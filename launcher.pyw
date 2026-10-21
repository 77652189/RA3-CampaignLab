r"""红警3 测试启动器: a small window listing the built CNV mods (Documents\Red Alert 3\Mods\<mod>\<mod>_1.0.skudef),
grouped, with a line on what each one is; double-click or "启动" starts RA3 1.13 with it (the same command as the
Play_<mod>.bat files: RA3.exe -runver 1.13 -modConfig <skudef>). Refuses to start while RA3 / Uprising runs.

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

# group, title -- the missions first, then the unit test maps; anything else is listed under 其他
KNOWN = {
    'CampA7': ('关卡', 'A7 鹰派：自由号当首领。先炸东北的电站，它就不能跃迁了'),
    'CampA8': ('关卡', 'A8 海上发布会：自由号归你，打掉东边三座供电平台；自由号被击落就输'),
    'CampBridge1': ('关卡', 'CNV05 金门抢桥：先拿南桥头，再顶住北岸的反扑'),
    'CampNew33': ('关卡', 'CNV04 鸣神小关卡'),
    'CampNew30': ('关卡', 'CNV03 小关卡：冷冻 + 缩小 + 游隼'),
    'CampNew35': ('单位测试图', '时滞炮车（最后一次编的场景）'),
    'CampNew36': ('单位测试图', '阻塞气球车（最后一次编的场景）'),
    'CampNew37': ('单位测试图', '烟花兵（最后一次编的场景）'),
    'CampNew38': ('单位测试图', '自由号空天航母（最后一次编的场景）'),
    'CampNew34': ('单位测试图', '磁钩坦克'),
    'CampNew31': ('单位测试图', '鸣神机制'),
    'CampNew29': ('单位测试图', '收缩射线车 + 游隼'),
}
GROUPS = ['关卡', '单位测试图', '其他']


def mods():
    """[(group, mod, title, built time)] for every mod folder with its skudef, missions first, newest first."""
    out = []
    if not os.path.isdir(MODS):
        return out
    for name in os.listdir(MODS):
        sku = os.path.join(MODS, name, f'{name}_1.0.skudef')
        if not os.path.exists(sku):
            continue
        group, title = KNOWN.get(name, ('其他', ''))
        out.append((group, name, title, os.path.getmtime(sku)))
    out.sort(key=lambda r: (GROUPS.index(r[0]), -r[3]))
    return out


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
                parents[group] = tree.insert('', 'end', text=group, open=group != '其他')
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
