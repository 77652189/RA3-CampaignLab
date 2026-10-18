"""Disassemble the D3D9 shaders inside a compiled effect (.fx from the SDK's Max plugin, .fxo) with Windows'
d3dcompiler_47.dll, to read how a retail shader uses its textures (e.g. the SPM channels, team colour).

  python -I experimental/units/fx_disasm.py <effect file> [out.txt]

Shader blobs are found by their version token (vs_/ps_ 2.0-3.0) and end token 0x0000FFFF.
"""
import ctypes
import struct
import sys

VERSIONS = {0xFFFE0200: 'vs_2_0', 0xFFFE0300: 'vs_3_0', 0xFFFF0200: 'ps_2_0', 0xFFFF0300: 'ps_3_0',
            0xFFFF0201: 'ps_2_x', 0xFFFE0201: 'vs_2_x'}


def blobs(data):
    out = []
    i = 0
    while i + 4 <= len(data):
        tok = struct.unpack_from('<I', data, i)[0]
        if tok in VERSIONS:
            j = i + 4
            while j + 4 <= len(data) and struct.unpack_from('<I', data, j)[0] != 0x0000FFFF:
                j += 4
            if j + 4 <= len(data) and j - i > 64:
                out.append((i, VERSIONS[tok], data[i:j + 4]))
                i = j + 4
                continue
        i += 4
    return out


def disasm(blob):
    d3d = ctypes.WinDLL('d3dcompiler_47.dll')
    res = ctypes.c_void_p()
    hr = d3d.D3DDisassemble(blob, len(blob), 0, None, ctypes.byref(res))
    if hr != 0:
        return f'; D3DDisassemble failed 0x{hr & 0xffffffff:08x}\n'

    class ID3DBlobVtbl(ctypes.Structure):
        _fields_ = [('QueryInterface', ctypes.c_void_p), ('AddRef', ctypes.c_void_p), ('Release', ctypes.c_void_p),
                    ('GetBufferPointer', ctypes.WINFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p)),
                    ('GetBufferSize', ctypes.WINFUNCTYPE(ctypes.c_size_t, ctypes.c_void_p))]
    vtbl = ctypes.cast(ctypes.cast(res, ctypes.POINTER(ctypes.c_void_p))[0], ctypes.POINTER(ID3DBlobVtbl)).contents
    ptr, size = vtbl.GetBufferPointer(res), vtbl.GetBufferSize(res)
    return ctypes.string_at(ptr, size).decode('latin-1')


if __name__ == '__main__':
    data = open(sys.argv[1], 'rb').read()
    text = []
    for off, ver, blob in blobs(data):
        text.append(f'\n;;;;;;;; {ver} at 0x{off:x}, {len(blob)} bytes\n' + disasm(blob))
    out = ''.join(text)
    if len(sys.argv) > 2:
        open(sys.argv[2], 'w', encoding='utf-8').write(out)
        print(len(text), 'shaders ->', sys.argv[2])
    else:
        print(out)
