"""Shared lock-gate unit used by the roster, look tools and pathing bench."""
from units import icewall as iw


def gate_unit(id='CNV_LockGate'):
    return iw.wall(id=id, length=240, thick=60, lifetime=None, health=5000, look_as='gate',
                   what='船闸闸门：横在水道上的建筑，不化、不打碎（关卡脚本删掉它就是开闸）')
