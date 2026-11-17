"""E147: ordinary engineer capture of neutral Swiss banks, module on/off.

Retail XML predicts a 750 initial bonus and 5 every 15 game frames (1s).
Both wallets start at zero; engineers enter normally at mission second 10.
Frame-relative wallet samples distinguish the bonus from recurring income.
Evidence bits: on/off captured with engineer consumed=1/2; pre-entry zero=4;
on bonus=8; off initial zero=16; on +15/+30/+45/+60 frames=32/64/128/256;
off +60 frames zero=512. Prediction: 1023 and final wallets 770/0.
Travel time and first deposit phase are hypotheses, not fitted clock offsets.
MEASURED 2026-11-15 PASS: f188=750/0, f206=755/0, f223=760/0,
f242=765/0, f257=770/0; evidence reaches 1023 and stays there. Those are
HUD observation frames; the evidence bits verify the exact relative samples.
Only ordinary neutral capture is covered; recapture, caps, garrison and repair
remain gaps. See work/re/e147_bankcapture.md.
"""
import re
from pathlib import Path

import labpaths
from maps import probe_range
from parts import Mission, Script, Test, Unit


def mission():
    m = Mission(name='CampBankE', map=probe_range, units=[])
    source = (Path(labpaths.SDK3) / 'SageXML/Civilian/Geneva_GE/Buildings/GE_SwissBank.xml').read_text(encoding='utf-8-sig')
    for tag, side, dx in [('on', 'p1', 0), ('off', 's2', 500)]:
        ident = 'CNVE147Bank' + tag
        xml = source.replace('id="GE_SwissBank"', 'id="' + ident + '"', 1)
        if tag == 'off':
            xml, n = re.subn(r'<AutoDepositUpdate\b.*?</AutoDepositUpdate>', '', xml, flags=re.S)
            assert n == 1
        m.units.append(Unit(ident, xml))
        m.put(ident, 'base gun', dx, 0, side='neutral', role='bank ' + tag, name='Bank ' + tag)
        m.put('AlliedEngineer', 'base gun', dx, -180, side=side, role='man ' + tag, name='Engineer ' + tag)
    return m


def check(m):
    t = Test()
    frame, evidence = 'E147Frame', 'E147Evidence'
    t.counters = [(frame, '帧数'), ('E147Moneyon', '收入'),
                  ('E147Moneyoff', '对照'), (evidence, '证据')]
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1')),
             ('SET_MILLISECOND_TIMER', 'E147Enter', 10.0)]
    for tag, side in [('on', 'p1'), ('off', 's2')]:
        start += [('PLAYER_SET_MONEY', m.player(side), 0),
                  ('UNIT_CHANGE_OBJECT_STATUS', m.role('man ' + tag).name, 'NO_ATTACK', 1)]
    t.scripts = [Script('Test - E147 start', [], start),
                 Script('Test - E147 frame', [], [('INCREMENT_COUNTER', 1, frame)], once=False)]
    t.scripts.append(Script('Test - E147 enter', [('TIMER_EXPIRED', 'E147Enter')], [
        ('NAMED_GARRISON_SPECIFIC_BUILDING', m.role('man ' + tag).name, m.role('bank ' + tag).name)
        for tag in ('on', 'off')]))
    for tag, side, bit in [('on', 'p1', 1), ('off', 's2', 2)]:
        money, age = 'E147Money' + tag, 'E147Age' + tag
        captured = [('NAMED_OWNED_BY_PLAYER', m.player(side), m.role('bank ' + tag).name),
                    ('NAMED_DESTROYED', m.role('man ' + tag).name)]
        t.scripts += [
            Script('Test - E147 wallet ' + tag, [],
                   [('SET_PLAYER_MONEY_TO_COUNTER', m.player(side), money)], once=False),
            Script('Test - E147 age ' + tag, captured,
                   [('INCREMENT_COUNTER', 1, age)], once=False),
            Script('Test - E147 captured ' + tag, captured, [('INCREMENT_COUNTER', bit, evidence)])]
        samples = [(1, 750, 8), (16, 755, 32), (31, 760, 64),
                   (46, 765, 128), (61, 770, 256)] if tag == 'on' else [(1, 0, 16), (61, 0, 512)]
        for at, amount, flag in samples:
            t.scripts.append(Script(f'Test - E147 sample {tag} {at}',
                [('COUNTER', age, 2, at), ('COUNTER', money, 2, amount)],
                [('INCREMENT_COUNTER', flag, evidence)]))
        t.scripts.append(Script('Test - E147 remove ' + tag, [('COUNTER', age, 2, 62)],
            [('NAMED_DELETE', m.role('bank ' + tag).name)]))
    t.scripts.append(Script('Test - E147 neutral zero',
        [('COUNTER', frame, 2, 100), ('COUNTER', 'E147Moneyon', 2, 0),
         ('COUNTER', 'E147Moneyoff', 2, 0)], [('INCREMENT_COUNTER', 4, evidence)]))
    t.expect = [('收入', 22, '==', 770, 28), ('对照', 2, '==', 0, 28),
                ('证据', 22, '==', 1023, 28)]
    t.bench = [('bench_watch', dict(seconds=28, every=1, sheet=False, lines=4))]
    return t


MISSION = {'engine_bankcapture': mission}
CHECKS = {'engine_bankcapture': {'a': check}}
