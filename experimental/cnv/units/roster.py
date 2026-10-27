"""Our units a level plan may name like retail's (开局, 可造, 给, 进攻): {Chinese name: how to make it}, each made at
its module's defaults (docs/story/units.md: the numbers they were verified at). A plan's devices may publish more
(the festival's ice engineer and sculptures, the convoy truck): those stay the devices' own.

Published: NAMES (name -> what), make(name) -> the Units it needs, the named one first.
"""
from units import beacon, burrower, clone, combo, crane, jammer, shikigami, tesla

_MAKE = {
    '超时空信标兵': (lambda: [beacon.beacon()], '盟军：把一片里的我方单位拉到自己身边（A5）'),
    '钻地运兵车': (lambda: [burrower.burrower()], '苏联：钻进地下不能被瞄准、不能开火，载 5 人（S5）'),
    '协调器干扰车': (lambda: [jammer.jammer()], '苏联：打开后原地不动，250 内所有单位减速（S6）'),
    '磁暴坦克': (lambda: [tesla.tesla()], '苏联：电涌时放电（S7，原版删除单位）'),
    '式神护卫': (lambda: [shikigami.shikigami()], '帝国：200 内的敌人改打它（J5）'),
    '纸鹤侦察机': (lambda: [crane.crane()], '帝国：没有武器，驱雾 900，一直隐身（J3）'),
    '合体机甲': (lambda: [combo.parent(), combo.child()], '帝国：子机开进母机就是合体，合体后只拆建筑（J4）'),
    '心灵巫女': (lambda: [clone.maiden()], '帝国：收回被克隆体控制的单位（J8）'),
}
NAMES = {k: what for k, (_, what) in _MAKE.items()}


_made = {}


def make(name):
    if name not in _made:                       # one make per name: a plan names its units many times
        _made[name] = _MAKE[name][0]()
    return _made[name]
