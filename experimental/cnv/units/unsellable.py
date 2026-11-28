"""不能卖: a structure the player cannot sell (A2's dam sections, work/mappage/a2/notes.md r9). Retail's own way: KindOf
+NOT_SELLABLE on a structure that keeps BaseStructure's sell module (Brighton Beach's BB_EuropeCoastalGun). The copy is
the retail file under `CNV_NoSell_<template>`. Bench: checks/blackcanyon.py `sell` (CANNOT_BE_SOLD set by script did
not stop SELL_OBJECT; the kind does). copy(template, kind, tag) adds another kind the same way (Husk's bench:
`CNV_Husk_OilDerrick`, KindOf +HUSK).

Published: copy (a Unit).
"""
import os

import labpaths
from parts import Unit
from units.icewall import sub1

SAGE = os.path.join(labpaths.SDK3, 'SageXML')


def copy(template, kind='NOT_SELLABLE', tag='NoSell'):
    for faction in sorted(os.listdir(SAGE)):
        p = os.path.join(SAGE, faction, 'Structures', template + '.xml')
        if os.path.exists(p):
            break
    else:
        raise ValueError(f'{template}: no retail structure file (SageXML/*/Structures)')
    id_ = f'CNV_{tag}_{template}'
    x = open(p, encoding='utf-8-sig').read()
    x = sub1(x, f'id="{template}"', f'id="{id_}"')
    x = sub1(x, 'KindOf="', f'KindOf="+{kind} ')
    return Unit(id_, x)
