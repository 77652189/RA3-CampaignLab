"""Count the caption-strip lines (yellow text rows) in each game_*.png of a shell_shots.py run: python -I -X utf8 caption_rows.py <dir>.
A line outside a 过场 should stand alone (max 1); frame times are file mtimes (shell_shots.py --every 1)."""
import glob, os, sys
from PIL import Image
import numpy as np
d = sys.argv[1]
fs = sorted(glob.glob(os.path.join(d, 'game_*.png')))
t0 = os.path.getmtime(fs[0])
out = []
for i, f in enumerate(fs):
    im = np.array(Image.open(f).convert('RGB').crop((340, 520, 860, 610))).astype(int)
    yel = ((im[:, :, 0] > 200) & (im[:, :, 1] > 160) & (im[:, :, 2] < 110)).sum(axis=1)
    lines, prev = 0, -9
    for r, v in enumerate(yel):
        if v > 3:
            if r - prev > 5:
                lines += 1
            prev = r
    out.append((round(os.path.getmtime(f) - t0, 1), lines))
print(' '.join(f'{t}:{n}' for t, n in out))
print('max lines', max(n for _, n in out))
