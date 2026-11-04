"""Any video file -> a .vp6 the game plays (EA's MVhd container, vp60 video, no audio: retail's own clips have none, the sound
is a dialogue line played next to them -- docs/story/handoff.md 1g).

  python -I -X utf8 experimental/video/to_vp6.py in.mp4 out.vp6 [--size radar|full]

radar: 288x288 for MOVIE_PLAY_RADAR (the picture is scaled to fit, black bars); full: 1280x720 for MOVIE_PLAY_FULLSCREEN.
23.976 fps like retail. Frames are decoded with OpenCV (any container it opens), written as y4m and encoded with NihAV's
nihav-encoder (built from source under work/downloads/nihav, see the handoff; ffmpeg cannot encode VP6).
"""
import argparse
import os
import subprocess
import sys
import tempfile

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENCODER = os.path.join(ROOT, 'work', 'downloads', 'nihav', 'src', 'nihav-HEAD-63ac44b', 'nihav-encoder', 'target', 'release',
                       'nihav-encoder.exe')
SIZES = {'radar': (288, 288), 'full': (1280, 720), 'head': (512, 288)}     # head: the overview's talking head (retail AMB*.vp6)
FPS = 23.976


def frames(path, size):
    """The video's frames at FPS, each scaled into `size` with black bars (BGR)."""
    w, h = size
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        sys.exit(f'to_vp6: cannot open {path}')
    src_fps = cap.get(cv2.CAP_PROP_FPS) or FPS
    read, canvas, k = 0, None, 0              # input frames read so far, the picture of the last one, output frame number
    while True:
        want = int(k / FPS * src_fps + 0.5)    # the input frame nearest in time to output frame k
        while read <= want:
            ok, img = cap.read()
            if not ok:
                return
            read += 1
            sh, sw = img.shape[:2]
            s = min(w / sw, h / sh)
            small = cv2.resize(img, (max(1, round(sw * s)), max(1, round(sh * s))), interpolation=cv2.INTER_AREA)
            canvas = np.zeros((h, w, 3), np.uint8)
            y0, x0 = (h - small.shape[0]) // 2, (w - small.shape[1]) // 2
            canvas[y0:y0 + small.shape[0], x0:x0 + small.shape[1]] = small
        yield canvas
        k += 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input')
    ap.add_argument('output')
    ap.add_argument('--size', choices=sorted(SIZES), default='radar')
    ap.add_argument('--quant', type=int, default=40, help='VP6 quantiser (retail-like quality ~ 30-60, lower = better)')
    a = ap.parse_args()
    if not os.path.exists(ENCODER):
        sys.exit(f'to_vp6: {ENCODER} not built (handoff 1g: cargo build --release in nihav-encoder)')
    w, h = SIZES[a.size]
    with tempfile.TemporaryDirectory() as tmp:
        y4m = os.path.join(tmp, 'in.y4m')
        count = 0
        with open(y4m, 'wb') as f:
            f.write(f'YUV4MPEG2 W{w} H{h} F24000:1001 Ip A1:1 C420jpeg\n'.encode())
            for img in frames(a.input, (w, h)):
                f.write(b'FRAME\n' + cv2.cvtColor(img, cv2.COLOR_BGR2YUV_I420).tobytes())
                count += 1
        r = subprocess.run([ENCODER, '--input', y4m, '--output', a.output, '--output-format', 'ea', '--ostream0',
                            f'timebase=1000/23976,encoder=vp6,version=vp61,quant={a.quant}'], capture_output=True, text=True)
        if r.returncode:
            sys.exit(f'to_vp6: encoder failed: {r.stderr[-300:]}')
    print(f'{a.output}: {count} frames {w}x{h}, {os.path.getsize(a.output)} bytes')


if __name__ == '__main__':
    main()
