r"""红警3 测试启动器: a small window listing the built CNV mods (Documents\Red Alert 3\Mods\<mod>\<mod>_1.0.skudef),
grouped, with a line on what each one is; double-click or "启动" starts RA3 1.13 with it (the same command as the
Play_<mod>.bat files: RA3.exe -runver 1.13 -modConfig <skudef>). Refuses to start while RA3 / Uprising runs.

The groups come from the code, not a hand-kept list (the old list went stale: A4 and every check build fell into
其他, user 2026-10-24): experimental/cnv/build.py registers every build -- the campaign levels (LEVELS) as played,
their checks (scripted runs), the unit test maps -- and docs/story/levels.md has each level's title, pitch and
check descriptions (tests/test_level_cards.py keeps the cards and the code in step). Only mods outside the
registry (the early make_campnew*.py builds) still need a line in LEGACY.

  pythonw launcher.pyw            the window (the desktop shortcut runs this)
  python -I -X utf8 launcher.pyw --list    print what the window would list, then exit (a check without a window)
"""
import datetime
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, 'experimental', 'campaign'))
import labpaths  # noqa: E402

MODS = os.path.join(os.path.expanduser('~'), 'Documents', 'Red Alert 3', 'Mods')
RA3 = os.path.join(labpaths.GAME, 'RA3.exe')
CARDS = os.path.join(ROOT, 'docs', 'story', 'levels.md')

LEVEL, LEVEL_CHECK, UNIT, EARLY, OTHER = '战役关卡', '关卡检查（脚本代玩）', '单位测试图', '早期原型（旧编图脚本）', '其他'
GROUPS = [LEVEL, LEVEL_CHECK, UNIT, EARLY, OTHER]
OPEN = {LEVEL, EARLY}                   # groups shown unfolded

# mods the registry does not build (the early make_campnew*.py scripts): group, title
LEGACY = {
    'CampBridge1': (EARLY, 'CNV05 金门抢桥：先拿南桥头，再顶住北岸的反扑'),
    'CampNew33': (EARLY, 'CNV04 鸣神小关卡'),
    'CampNew30': (EARLY, 'CNV03 小关卡：冷冻 + 缩小 + 游隼'),
    'CampNew35': (EARLY, '时滞炮车（最后一次编的场景）'),
    'CampNew36': (EARLY, '阻塞气球车（最后一次编的场景）'),
    'CampNew37': (EARLY, '烟花兵（最后一次编的场景）'),
    'CampNew38': (EARLY, '自由号空天航母（最后一次编的场景）'),
    'CampNew34': (EARLY, '磁钩坦克'),
    'CampNew31': (EARLY, '鸣神机制'),
    'CampNew29': (EARLY, '收缩射线车 + 游隼'),
    'CNVChaos': (OTHER, '联机不同步测试图：遭遇战 CNV_Chaos，观战 + 4 个凶残 AI，会存录像'),
}


def cards():
    """{level key: (title, {check: what})} from docs/story/levels.md: "A4 冰雕里的兵：守" (the heading and the first
    sentence of its 一句话玩法) and its 检查 list -- for a level with a plan (docs/story/plans), its 一句话 and 检查."""
    with open(CARDS, encoding='utf-8') as f:
        text = f.read()
    heads = list(re.finditer(r'^## (.+?) · `(\w+)`$', text, re.M))
    out = {}
    for k, h in enumerate(heads):
        body = text[h.end():heads[k + 1].start() if k + 1 < len(heads) else len(text)]
        if f'(plans/{h.group(2)}.md)' in body:
            sys.path[:0] = [os.path.join(ROOT, 'experimental', 'cnv')]
            import plan
            d = plan.load(h.group(2))
            pitch = str(d.get('一句话', '')).split('。')[0]
            out[h.group(2)] = (h.group(1) + (f'：{pitch}' if pitch else ''), dict(d.get('检查') or {}))
            continue
        pitch = re.search(r'^一句话玩法：([^。\n]*)', body, re.M)
        checks = dict(re.findall(r'^  - `(\w+)`：(.*)$', body, re.M))
        out[h.group(2)] = (h.group(1) + (f'：{pitch.group(1)}' if pitch else ''), checks)
    return out


def catalog():
    """{mod: (group, title, order)} for every build the code registers; order: the cards' order for the levels."""
    sys.path[:0] = [os.path.join(ROOT, 'experimental', 'cnv')]
    import build
    known = cards()
    order = {key: k for k, key in enumerate(known)}
    out = {}
    for key, (make, checks) in build.MISSIONS.items():
        for check in [''] + list(checks):
            _, _, mod = build.resolve(key, check)
            if key in build.LEVELS:
                title, what = known.get(key, (key, {}))
                if check:
                    out[mod] = (LEVEL_CHECK, f'{title.split("：")[0]} · {check}：{what.get(check, "")}', order.get(key, 99))
                else:
                    out[mod] = (LEVEL, title, order.get(key, 99))
            else:
                m = make()
                names = list(dict.fromkeys(re.split('[：（(]', u.what)[0] for u in m.units if getattr(u, 'what', '')))
                title = '、'.join(names) or f'对照（{key}）'
                out[mod] = (UNIT, title + (f' · {check}' if check else ''), 99)
    return out


def mods():
    """[(group, mod, title, built time)] for every mod folder with its skudef: levels in the cards' order, the rest
    newest first."""
    out = []
    if not os.path.isdir(MODS):
        return out
    try:
        known = catalog()
    except Exception as e:                  # the code mid-edit: still list the mods, flat
        known = {}
        print('catalog failed:', e, file=sys.stderr)
    for name in os.listdir(MODS):
        sku = os.path.join(MODS, name, f'{name}_1.0.skudef')
        if not os.path.exists(sku):
            continue
        group, title, rank = known.get(name) or (*LEGACY.get(name, (OTHER, '')), 99)
        out.append((group, name, title, os.path.getmtime(sku), rank))
    out.sort(key=lambda r: (GROUPS.index(r[0]), r[4], -r[3]))
    return [r[:4] for r in out]


def game_running():
    out = subprocess.run(['tasklist'], capture_output=True, text=True, errors='replace',
                         creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)).stdout.lower()
    return bool(re.search(r'\bra3(_1\.\d+\.game|\.exe|ep1)', out))


def launch(name, windowed=False):
    sku = os.path.join(MODS, name, f'{name}_1.0.skudef')
    args = [RA3, '-runver', '1.13', '-modConfig', sku] + (['-win'] if windowed else [])
    subprocess.Popen(args, cwd=labpaths.GAME)


def main():
    import tkinter as tk
    from tkinter import messagebox, ttk

    root = tk.Tk()
    root.title('红警3 测试启动器')
    root.geometry('760x480')
    root.minsize(560, 360)
    font = ('Microsoft YaHei UI', 10)
    style = ttk.Style(root)
    style.configure('Treeview', font=font, rowheight=26)
    style.configure('Treeview.Heading', font=(font[0], 10, 'bold'))
    style.configure('TButton', font=font, padding=6)

    frame = ttk.Frame(root, padding=10)
    frame.pack(fill='both', expand=True)
    tree = ttk.Treeview(frame, columns=('title', 'built'), selectmode='browse')
    tree.heading('#0', text='mod')
    tree.heading('title', text='内容')
    tree.heading('built', text='编译时间')
    tree.column('#0', width=150, stretch=False)
    tree.column('title', width=440)
    tree.column('built', width=130, stretch=False)
    scroll = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    tree.grid(row=0, column=0, sticky='nsew')
    scroll.grid(row=0, column=1, sticky='ns')
    frame.rowconfigure(0, weight=1)
    frame.columnconfigure(0, weight=1)

    status = tk.StringVar()
    windowed = tk.BooleanVar(value=False)

    def refresh():
        tree.delete(*tree.get_children())
        parents = {}
        for group, name, title, built in mods():
            if group not in parents:
                parents[group] = tree.insert('', 'end', text=group, open=group in OPEN)
            tree.insert(parents[group], 'end', iid=name, text=name,
                        values=(title, datetime.datetime.fromtimestamp(built).strftime('%m-%d %H:%M')))
        first = next((i for p in tree.get_children() for i in tree.get_children(p)), None)
        if first:
            tree.selection_set(first)
            tree.see(first)
        status.set('游戏正在运行，先关掉再启动' if game_running() else f'共 {len(mods())} 个 mod，双击或点"启动"')

    def start(_event=None):
        sel = tree.selection()
        if not sel or sel[0] in GROUPS:
            return
        if game_running():
            messagebox.showwarning('红警3 测试启动器', '红警3 或起义时刻已经在运行（也可能是测试台在跑）。\n先关掉再启动。')
            return
        launch(sel[0], windowed.get())
        status.set(f'已启动 {sel[0]}，游戏加载要几十秒')

    tree.bind('<Double-1>', start)
    tree.bind('<Return>', start)
    bar = ttk.Frame(root, padding=(10, 0, 10, 10))
    bar.pack(fill='x')
    ttk.Button(bar, text='启动', command=start).pack(side='left')
    ttk.Checkbutton(bar, text='窗口模式', variable=windowed).pack(side='left', padx=10)
    ttk.Button(bar, text='刷新', command=refresh).pack(side='left')
    ttk.Button(bar, text='打开 Mods 文件夹', command=lambda: os.startfile(MODS)).pack(side='left', padx=10)
    ttk.Label(bar, textvariable=status, font=font).pack(side='right')
    refresh()
    root.mainloop()


if __name__ == '__main__':
    if '--list' in sys.argv:
        for group, name, title, built in mods():
            print(group, name, title, datetime.datetime.fromtimestamp(built).strftime('%m-%d %H:%M'), sep=' | ')
        print('RA3:', RA3, os.path.exists(RA3), '| running:', game_running())
    else:
        main()
