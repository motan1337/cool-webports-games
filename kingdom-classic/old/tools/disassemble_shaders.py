import ctypes
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/python'))
import UnityPy
from UnityPy.export.ShaderConverter import ShaderProgram
from UnityPy.helpers import CompressionHelper
from UnityPy.streams import EndianBinaryReader

compiler = ctypes.WinDLL('d3dcompiler_47.dll')
disassemble = compiler.D3DDisassemble
disassemble.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint, ctypes.c_char_p,
                       ctypes.POINTER(ctypes.c_void_p)]
disassemble.restype = ctypes.c_long

def disassembly(code):
    if b'DXBC' in code[:32]:
        code = code[code.index(b'DXBC'):]
    blob = ctypes.c_void_p()
    data = ctypes.create_string_buffer(code)
    result = disassemble(data, len(code), 0, None, ctypes.byref(blob))
    if result < 0:
        return None, result
    table = ctypes.cast(blob, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    pointer = ctypes.WINFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p)(table[3])(blob)
    size = ctypes.WINFUNCTYPE(ctypes.c_size_t, ctypes.c_void_p)(table[4])(blob)
    text = ctypes.string_at(pointer, size).decode('utf-8', errors='replace').rstrip('\0')
    ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(table[2])(blob)
    return text, 0

out = ROOT / 'analysis/shader-disassembly'
out.mkdir(exist_ok=True)
env = UnityPy.load(str(ROOT / 'Kingdom_Data'))
manifest = []
for obj in env.objects:
    if obj.type.name != 'Shader':
        continue
    shader = obj.read()
    if not shader.m_SubProgramBlob:
        continue
    data = CompressionHelper.decompress_lz4(bytes(shader.m_SubProgramBlob), shader.decompressedSize)
    program = ShaderProgram(EndianBinaryReader(data, endian='<'), obj.version)
    name = re.sub(r'[^\w.-]', '_', shader.m_Name) + '_' + str(obj.path_id)
    directory = out / name
    directory.mkdir(exist_ok=True)
    results = []
    for i, sub in enumerate(program.m_SubPrograms):
        code = sub.m_ProgramCode
        text, status = disassembly(code)
        (directory / ('%03d.bin' % i)).write_bytes(code)
        if text:
            (directory / ('%03d.asm.txt' % i)).write_text(text, encoding='utf-8')
        results.append({'index': i, 'type': str(sub.m_ProgramType), 'keywords': sub.m_Keywords,
                        'bytes': len(code), 'hresult': status, 'disassembled': text is not None})
    (directory / 'programs.json').write_text(json.dumps(results, indent=2))
    manifest.append({'shader': shader.m_Name, 'source': obj.assets_file.name, 'path_id': obj.path_id,
                     'programs': len(results), 'disassembled': sum(x['disassembled'] for x in results)})
(out / 'manifest.json').write_text(json.dumps(manifest, indent=2))
print('Disassembled', sum(x['disassembled'] for x in manifest), 'of', sum(x['programs'] for x in manifest), 'programs')
