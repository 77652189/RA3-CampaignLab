"""The CampShell launcher, its icon and the desktop shortcut (ADR 0014: the shell is started by its own way, the retail game and
its shortcuts are never touched).

  python -I -X utf8 experimental/cnv/launcher.py            -> Mods\\CampShell\\Play_CampShell.vbs + CampShell.ico
  python -I -X utf8 experimental/cnv/launcher.py --desktop  ... and the shortcut on the desktop (its own file, created or replaced)
  python -I -X utf8 experimental/cnv/launcher.py --icon-only <png>   the icon's master picture, to look at

The launcher is a .vbs run by wscript (no console window): RA3.exe -runver 1.13 -modConfig <the mod's skudef>, extra arguments
passed on (-win for a windowed test). The icon follows retail's and Uprising's: a red star with the cream points between, a disc
in the middle; ours has the ice-blue disc and a snowflake (the A4 festival), and no lettering.
"""
import math
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'experimental', 'campaign'))
import labpaths                                         # noqa: E402

MOD = 'CampShell'
SHORTCUT = '红警3 · 战役实验室'
OUT = os.path.join(os.path.expanduser('~'), 'Documents', 'Red Alert 3', 'Mods', MOD)
ICON_SIZES = [256, 128, 64, 48, 32, 24, 16]

VBS = '''\' CampShell launcher: RA3 with the CampShell mod, no console window (experimental/cnv/launcher.py)
Dim sh, fso, here, game, args, i
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
here = fso.GetParentFolderName(WScript.ScriptFullName)
game = "{game}"
If Not fso.FileExists(game & "\\RA3.exe") Then
    MsgBox "找不到红謭3：" & game, 16, "{shortcut}"
    WScript.Quit 1
End If
If Not fso.FileExists(here & "\\{mod}_1.0.skudef") Then
    MsgBox "找不到 mod 配置：" & here & "\\{mod}_1.0.skudef", 16, "{shortcut}"
    WScript.Quit 1
End If
args = ""
For i = 0 To WScript.Arguments.Count - 1
    args = args & " " & WScript.Arguments(i)
Next
sh.CurrentDirectory = game
sh.Run """" & game & "\\RA3.exe"" -runver 1.13 -modConfig """ & here & "\\{mod}_1.0.skudef""" & args, 1, False
'''


# ---- the icon ------------------------------------------------------------------------------------------------------

def _star(cx, cy, tip, inner, first, n=5):
    return [(cx + (tip if i % 2 == 0 else inner) * math.cos(first + i * math.pi / n),
             cy + (tip if i % 2 == 0 else inner) * math.sin(first + i * math.pi / n)) for i in range(2 * n)]


def draw_icon(size=1024):
    """The icon's master picture (RGBA, `size` square): drawn at twice the size and scaled down for smooth edges."""
    from PIL import Image, ImageDraw, ImageFilter
    S = 2048
    k = S / 1024
    cx, cy = 512 * k, 545 * k
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    up = -math.pi / 2

    def xy(r, a):
        return (cx + r * k * math.cos(a), cy + r * k * math.sin(a))

    # the cream points between the red ones (shorter), lit from the upper left
    for i in range(5):
        a = up + math.pi / 5 + i * 2 * math.pi / 5
        tip, l, r = xy(380, a), xy(190, a - math.pi / 5), xy(190, a + math.pi / 5)
        d.polygon([tip, l, (cx, cy)], fill=(214, 190, 128, 255), outline=(40, 25, 10, 255))
        d.polygon([tip, r, (cx, cy)], fill=(244, 228, 176, 255), outline=(40, 25, 10, 255))
    # the red star: five long points, each half in its own shade
    for i in range(5):
        a = up + i * 2 * math.pi / 5
        tip, l, r = xy(505, a), xy(215, a - math.pi / 5), xy(215, a + math.pi / 5)
        d.polygon([tip, l, (cx, cy)], fill=(150, 18, 20, 255), outline=(30, 8, 8, 255))
        d.polygon([tip, r, (cx, cy)], fill=(214, 40, 34, 255), outline=(30, 8, 8, 255))
    for i in range(5):                                  # a thin cream ridge along each red point
        a = up + i * 2 * math.pi / 5
        d.line([xy(495, a), xy(250, a)], fill=(255, 196, 150, 255), width=int(5 * k))
    # the disc: a cream ring, the ice-blue face, a gloss on its upper half
    R = 300
    d.ellipse([cx - R * k, cy - R * k, cx + R * k, cy + R * k], fill=(246, 232, 190, 255), outline=(40, 25, 10, 255), width=int(5 * k))
    r = 268
    face = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    fd = ImageDraw.Draw(face)
    for step in range(int(r * k), 0, -2):               # a radial gradient, lighter toward the upper centre
        t = step / (r * k)
        fd.ellipse([cx - step, cy - step * 0.98 + (1 - t) * 40 * k, cx + step, cy + step * 1.02 + (1 - t) * 40 * k],
                   fill=(int(40 + 70 * (1 - t)), int(95 + 100 * (1 - t)), int(170 + 70 * (1 - t)), 255))
    mask = Image.new('L', (S, S), 0)
    ImageDraw.Draw(mask).ellipse([cx - r * k, cy - r * k, cx + r * k, cy + r * k], fill=255)
    img.paste(face, (0, 0), mask)
    gloss = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(gloss).ellipse([cx - 235 * k, cy - 262 * k, cx + 235 * k, cy - 20 * k], fill=(255, 255, 255, 70))
    gloss.putalpha(Image.composite(gloss.getchannel('A'), Image.new('L', (S, S), 0), mask))
    img.alpha_composite(gloss)
    d = ImageDraw.Draw(img)
    # the snowflake: six arms, each with two pairs of side branches
    white = (255, 255, 255, 255)
    for i in range(6):
        a = up + i * math.pi / 3
        d.line([(cx, cy), xy(190, a)], fill=white, width=int(26 * k))
        for dist, ln in ((95, 78), (150, 48)):
            for side in (-1, 1):
                base = xy(dist, a)
                end = (base[0] + ln * k * math.cos(a + side * math.pi / 3), base[1] + ln * k * math.sin(a + side * math.pi / 3))
                d.line([base, end], fill=white, width=int(18 * k))
        tipx = xy(190, a)
        d.ellipse([tipx[0] - 13 * k, tipx[1] - 13 * k, tipx[0] + 13 * k, tipx[1] + 13 * k], fill=white)
    d.ellipse([cx - 22 * k, cy - 22 * k, cx + 22 * k, cy + 22 * k], fill=white)
    shadow = img.filter(ImageFilter.GaussianBlur(10))   # a soft drop shadow so the star stands off any desktop
    back = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    back.paste((0, 0, 0, 110), (int(6 * k), int(12 * k)), shadow.getchannel('A'))
    back.alpha_composite(img)
    return back.resize((size, size), Image.LANCZOS)


def write_icon(path):
    master = draw_icon(512)
    master.save(path, format='ICO', sizes=[(s, s) for s in ICON_SIZES])
    return path


# ---- the launcher and the shortcut -------------------------------------------------------------------------------

def write_launcher(out=OUT):
    os.makedirs(out, exist_ok=True)
    vbs = os.path.join(out, f'Play_{MOD}.vbs')
    text = VBS.format(game=labpaths.GAME, shortcut=SHORTCUT, mod=MOD)
    with open(vbs, 'w', encoding='utf-16', newline='') as f:        # UTF-16 with a BOM: wscript reads it, the Chinese in the messages too
        f.write(text.replace('\r\n', '\n').replace('\n', '\r\n'))
    return vbs


def desktop_shortcut(vbs, ico):
    """Create (or replace) the shortcut file on the desktop, named SHORTCUT: wscript runs the launcher, the icon is ours.
    Only this file is written: retail's shortcuts are not read or changed."""
    script = os.path.join(os.environ.get('TEMP', '.'), 'campshell_lnk.ps1')
    with open(script, 'w', encoding='utf-8-sig') as f:
        f.write('$desk = [Environment]::GetFolderPath("Desktop")\n'
                f'$lnk = Join-Path $desk "{SHORTCUT}.lnk"\n'
                '$sh = New-Object -ComObject WScript.Shell\n'
                '$s = $sh.CreateShortcut($lnk)\n'
                '$s.TargetPath = Join-Path $env:SystemRoot "System32\\wscript.exe"\n'
                f'$s.Arguments = \'//nologo "{vbs}"\'\n'
                f'$s.WorkingDirectory = "{os.path.dirname(vbs)}"\n'
                f'$s.IconLocation = "{ico},0"\n'
                '$s.Description = "红警3 战役实验室：CampShell mod 的专用启动方式，不影响原版"\n'
                '$s.Save()\n'
                'Write-Output $lnk\n')
    r = subprocess.run(['pwsh', '-NoProfile', '-File', script], capture_output=True)       # (console code page output: bytes)
    if r.returncode:
        raise SystemExit('launcher: shortcut not created: ' + (r.stderr or r.stdout).decode('gbk', 'replace').strip()[-300:])
    return r.stdout.decode('gbk', 'replace').strip()


def main():
    if len(sys.argv) > 2 and sys.argv[1] == '--icon-only':
        draw_icon(512).save(sys.argv[2])
        print(sys.argv[2])
        return
    ico = write_icon(os.path.join(OUT, f'{MOD}.ico')) if os.path.isdir(OUT) else None
    if ico is None:
        os.makedirs(OUT, exist_ok=True)
        ico = write_icon(os.path.join(OUT, f'{MOD}.ico'))
    vbs = write_launcher()
    print('launcher', vbs, '\nicon    ', ico)
    if '--desktop' in sys.argv:
        print('shortcut', desktop_shortcut(vbs, ico))


if __name__ == '__main__':
    main()
