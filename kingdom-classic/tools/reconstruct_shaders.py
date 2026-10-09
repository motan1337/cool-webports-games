import ctypes
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DISASM = ROOT / 'analysis/shader-disassembly'
OUT = ROOT / 'analysis/shader-reconstruction'
OUT.mkdir(exist_ok=True)
UNIFORM = re.compile(r'^//   ((?:row_major )?(?:float(?:[1-4](?:x[1-4])?)?|sampler2D|samplerCUBE)) (\w+)(\[\d+\])?;$', re.M)
REGISTER = re.compile(r'^//   (\w+)\s+([cs]\d+)\s+(\d+)\s*$', re.M)
ALIASES = {'glstate_matrix_mvp': 'UNITY_MATRIX_MVP', '_Object2World': 'unity_ObjectToWorld',
           '_World2Object': 'unity_WorldToObject', 'glstate_lightmodel_ambient': 'UNITY_LIGHTMODEL_AMBIENT',
           '_LightMatrix0': 'unity_WorldToLight'}
BUILTINS = {'_ProjectionParams', '_ScreenParams', '_Time', '_WorldSpaceLightPos0', '_LightColor0',
            'unity_4LightAtten0', 'unity_4LightPosX0', 'unity_4LightPosY0', 'unity_4LightPosZ0',
            'unity_LightColor', 'unity_SHAb', 'unity_SHAg', 'unity_SHAr', 'unity_SHBb', 'unity_SHBg',
            'unity_SHBr', 'unity_SHC', 'unity_ColorSpaceLuminance', 'unity_MatrixVP'}

def vector(operand):
    negative = operand.startswith('-')
    operand = operand.lstrip('-')
    register, _, swizzle = operand.partition('.')
    if register.endswith('_abs'):
        register = 'abs(' + register[:-4] + ')'
    if swizzle:
        swizzle = (swizzle + swizzle[-1] * 4)[:4]
        register += '.' + swizzle
    return '-(' + register + ')' if negative else register

def semantic(name):
    if name == 'position': return 'position'
    if name.startswith('texcoord'): return 'tex' + (name[8:] or '0')
    if name.startswith('color'): return 'color' + (name[5:] or '0')
    if name == 'normal': return 'normal'
    raise RuntimeError('Unknown semantic ' + name)

def output_field(register):
    if register == 'oPos': return 'position'
    if register.startswith('oT'): return 'tex' + register[2:]
    if register.startswith('oD'): return 'color' + register[2:]
    raise RuntimeError('Output semantic is missing for ' + register)

STRUCTS = '''struct KingdomVertex {
float4 position : POSITION;
float4 normal : NORMAL;
float4 tex0 : TEXCOORD0;
float4 tex1 : TEXCOORD1;
float4 color0 : COLOR0;
};
struct KingdomVarying {
float4 position : SV_POSITION;
float4 tex0 : TEXCOORD0;
float4 tex1 : TEXCOORD1;
float4 tex2 : TEXCOORD2;
float4 tex3 : TEXCOORD3;
float4 tex4 : TEXCOORD4;
float4 tex5 : TEXCOORD5;
float4 tex6 : TEXCOORD6;
float4 tex7 : TEXCOORD7;
float4 color0 : COLOR0;
float4 color1 : COLOR1;
};
'''

def translate(text, function, modern=False):
    uniforms = {name: (kind, array or '') for kind, name, array in UNIFORM.findall(text)}
    registers = REGISTER.findall(text)
    lines = [line.strip() for line in text.splitlines() if line.startswith('    ') and line.strip()]
    is_vertex = lines[0].startswith('vs_')
    inputs, outputs, sampler_types = {}, {}, {}
    constants, operations = [], []
    all_registers = set()
    for line in lines[1:]:
        op, _, args = line.partition(' ')
        op = op.replace('_pp', '')
        arguments = [arg.strip() for arg in args.split(',')]
        if op.startswith('dcl'):
            register = arguments[0].split('.')[0]
            name = op[4:] if op.startswith('dcl_') else ('color' if register.startswith('v') and not is_vertex else 'texcoord') + register[1:]
            if register.startswith('s'):
                sampler_types[register] = name
            elif register.startswith(('v', 't')):
                inputs[register] = semantic(name)
            elif register.startswith('o'):
                outputs[register] = semantic(name)
            continue
        if op == 'def':
            constants.append('float4 %s = float4(%s);' % (arguments[0], ', '.join(arguments[1:])))
            continue
        operations.append((op, arguments))
        all_registers.update(re.findall(r'\b(?:r\d+|o\d+|oPos|oT\d+|oD\d+|oC\d+)\b', args))
    samplers = {}
    for name, register, count in registers:
        kind, array = uniforms[name]
        if register.startswith('s'):
            samplers[register] = (name, kind)
            continue
        count = int(count)
        first = int(register[1:])
        symbol = ALIASES.get(name, name) if modern else name
        for i in range(count):
            if 'x' in kind:
                value = symbol + ('[%d]' % (i // 4) if array else '') + '[%d]' % (i % 4)
            elif array:
                value = symbol + '[%d]' % i
            elif kind == 'float': value = 'float4(' + symbol + ', 0, 0, 0)'
            elif kind == 'float2': value = 'float4(' + symbol + ', 0, 0)'
            elif kind == 'float3': value = 'float4(' + symbol + ', 0)'
            else: value = symbol
            constants.append('float4 c%d = %s;' % (first + i, value))
    return_type, input_type = ('KingdomVarying', 'KingdomVertex') if is_vertex else ('float4', 'KingdomVarying')
    code = [return_type + ' ' + function + '(' + input_type + ' input)' + ('' if is_vertex else ' : SV_Target') + ' {']
    if is_vertex: code.append('KingdomVarying output = (KingdomVarying)0;')
    code += ['float4 %s = input.%s;' % pair for pair in inputs.items()]
    code += constants
    code += ['float4 %s = 0;' % name for name in sorted(all_registers)]
    for raw_op, arguments in operations:
        saturate = '_sat' in raw_op
        op = raw_op.replace('_sat', '')
        dest = arguments[0]
        if op == 'texkill':
            code.append('clip(%s.xyz);' % dest.split('.')[0])
            continue
        src = [vector(arg) for arg in arguments[1:]]
        a = '(' + src[0] + ')' if src else ''
        b = '(' + src[1] + ')' if len(src) > 1 else ''
        c = '(' + src[2] + ')' if len(src) > 2 else ''
        if op == 'mov': value = a
        elif op == 'add': value = a + ' + ' + b
        elif op == 'mul': value = a + ' * ' + b
        elif op == 'mad': value = a + ' * ' + b + ' + ' + c
        elif op in ['dp3', 'dp4']: value = 'dot(%s.%s, %s.%s).xxxx' % (a, 'xyz' if op == 'dp3' else 'xyzw', b, 'xyz' if op == 'dp3' else 'xyzw')
        elif op == 'dp2add': value = '(dot(%s.xy, %s.xy) + %s.x).xxxx' % (a, b, c)
        elif op == 'rcp': value = '1.0 / ' + a
        elif op == 'rsq': value = 'rsqrt(abs(%s.x)).xxxx' % a
        elif op == 'nrm': value = 'float4(normalize(%s.xyz), 0)' % a
        elif op in ['max', 'min']: value = op + '(' + a + ', ' + b + ')'
        elif op in ['abs', 'frc', 'exp', 'log']: value = {'abs': 'abs', 'frc': 'frac', 'exp': 'exp2', 'log': 'log2'}[op] + '(' + a + ')'
        elif op == 'sge': value = 'step(' + b + ', ' + a + ')'
        elif op == 'cmp': value = 'lerp(' + c + ', ' + b + ', step(0, ' + a + '))'
        elif op == 'lrp': value = 'lerp(' + c + ', ' + b + ', ' + a + ')'
        elif op == 'sincos': value = 'float4(cos(%s.x), sin(%s.x), 0, 0)' % (a, a)
        elif op in ['texld', 'texldp']:
            sampler, kind = samplers[arguments[2].split('.')[0]]
            if kind == 'samplerCUBE': value = 'texCUBE(%s, %s.xyz)' % (sampler, a)
            elif op == 'texldp': value = 'tex2Dproj(%s, %s)' % (sampler, a)
            else: value = 'tex2D(%s, %s.xy)' % (sampler, a)
        else: raise RuntimeError('Unsupported instruction ' + op)
        if saturate: value = 'saturate(' + value + ')'
        mask = dest.partition('.')[2]
        if mask: value = '(' + value + ').' + mask
        code.append(dest + ' = ' + value + ';')
    if is_vertex:
        for register in all_registers:
            if register.startswith('o'):
                code.append('output.%s = %s;' % (outputs.get(register) or output_field(register), register))
        if modern and '_ScreenParams' in uniforms:
            code.append('#if !defined(SHADER_API_D3D9)\noutput.position.xy += output.position.w * float2(1.0 / _ScreenParams.x, -1.0 / _ScreenParams.y);\n#endif')
        code.append('return output;')
    else:
        code.append('return oC0;')
    code.append('}')
    return '\n'.join(code), uniforms, 'vs_3_0' if is_vertex else 'ps_3_0'

def brace_end(text, opening):
    depth = 1
    index = opening + 1
    while depth:
        depth += (text[index] == '{') - (text[index] == '}')
        index += 1
    return index

compiler = ctypes.WinDLL('d3dcompiler_47.dll')
compile_shader = compiler.D3DCompile
compile_shader.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_char_p, ctypes.c_void_p,
                          ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint,
                          ctypes.c_uint, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_void_p)]
compile_shader.restype = ctypes.c_long

def blob_text(blob):
    if not blob.value: return ''
    table = ctypes.cast(blob, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    pointer = ctypes.WINFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p)(table[3])(blob)
    size = ctypes.WINFUNCTYPE(ctypes.c_size_t, ctypes.c_void_p)(table[4])(blob)
    text = ctypes.string_at(pointer, size).decode('utf-8', errors='replace').rstrip('\0')
    ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(table[2])(blob)
    return text

report = []
for shader_file in sorted((ROOT / 'unity-web/Assets/Shader').glob('*.shader')):
    safe = re.sub(r'[^\w.-]', '_', shader_file.stem)
    directories = [p for p in DISASM.iterdir() if p.is_dir() and p.name.rsplit('_', 1)[0] == safe]
    if len(directories) != 1: raise RuntimeError('Shader identity is ambiguous: ' + safe)
    directory = directories[0]
    metadata = {x['index']: x for x in json.loads((directory / 'programs.json').read_text())}
    original = (ROOT / 'analysis/original-shaders' / (directory.name + '.shader.txt')).read_text()
    validation = []
    translated = {}
    shader_out = OUT / directory.name
    shader_out.mkdir(exist_ok=True)
    for index, data in metadata.items():
        if data['type'] not in ['9', '10', '11', '12']:
            continue
        asm = (directory / ('%03d.asm.txt' % index)).read_text()
        code, uniforms, target = translate(asm, 'main')
        declarations = '\n'.join(kind + ' ' + name + array + ';' for name, (kind, array) in uniforms.items())
        source = declarations + '\n' + STRUCTS + code
        (shader_out / ('%03d.hlsl' % index)).write_text(source)
        data_buffer = ctypes.create_string_buffer(source.encode())
        blob, error = ctypes.c_void_p(), ctypes.c_void_p()
        status = compile_shader(data_buffer, len(source.encode()), b'kingdom', None, None, b'main', target.encode(), 0, 0,
                                ctypes.byref(blob), ctypes.byref(error))
        diagnostic = blob_text(error)
        if blob.value:
            table = ctypes.cast(blob, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
            ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(table[2])(blob)
        validation.append({'index': index, 'keywords': data['keywords'], 'hresult': status, 'diagnostic': diagnostic})
        translated[index] = translate(asm, 'vert' if target.startswith('vs') else 'frag', modern=True)
    updated = original
    passes = []
    for match in list(re.finditer(r'\bPass\s*\{', original)):
        opening = original.index('{', match.start())
        end = brace_end(original, opening)
        block = original[match.start():end]
        if 'Program "vp"' not in block: continue
        programs = []
        for stage in ['vp', 'fp']:
            start = block.index('Program "' + stage + '"')
            body_start = block.index('{', start)
            body_end = brace_end(block, body_start)
            indices = [int(i) for i in re.findall(r'GpuProgramIndex (\d+)', block[body_start:body_end]) if int(i) in translated]
            if not indices: raise RuntimeError('Missing DX9 stage ' + shader_file.name + ' ' + stage)
            programs.append((start, body_end, indices))
        keys = set(k for _, _, indices in programs for i in indices for k in metadata[i]['keywords'])
        pragmas = ['#pragma vertex vert', '#pragma fragment frag', '#pragma target 3.0']
        lights = sorted(keys & {'DIRECTIONAL', 'POINT', 'SPOT', 'POINT_COOKIE', 'DIRECTIONAL_COOKIE'})
        shadows = sorted(keys & {'SHADOWS_OFF', 'SHADOWS_SCREEN'})
        for group in [lights, shadows]:
            if group: pragmas.append('#pragma multi_compile ' + ' '.join(group))
        for key in sorted(keys - set(lights + shadows)):
            pragmas.append('#pragma multi_compile ' + ('' if key.endswith('_OFF') else '__ ') + key)
        uniforms = {}
        for _, _, indices in programs:
            for i in indices: uniforms.update(translated[i][1])
        declarations = []
        for name, (kind, array) in sorted(uniforms.items()):
            if name in BUILTINS or (name in ALIASES and name != '_LightMatrix0'): continue
            if name == '_LightTexture0' and 'POINT_COOKIE' in keys:
                declarations.append('#if defined(POINT_COOKIE)\nsamplerCUBE _LightTexture0;\n#else\nsampler2D _LightTexture0;\n#endif')
            else:
                declarations.append(kind.replace('row_major ', '') + ' ' + ALIASES.get(name, name) + array + ';')
        bodies = []
        for _, _, indices in programs:
            stage_keys = set(k for i in indices for k in metadata[i]['keywords'])
            indices = sorted(indices, key=lambda i: -len(metadata[i]['keywords']))
            exclusive_keys = set(lights + shadows)
            for number, index in enumerate(indices):
                own = set(metadata[index]['keywords'])
                tests = [('' if key in own else '!') + 'defined(' + key + ')' for key in sorted(stage_keys) if key in own or key in exclusive_keys]
                bodies.append(('#if ' if number == 0 else '#elif ') + (' && '.join(tests) if tests else '1'))
                bodies.append(translated[index][0])
            bodies.append('#else\n' + translated[indices[0]][0] + '\n#endif')
        cg = 'CGPROGRAM\n' + '\n'.join(pragmas) + '\n#include "UnityCG.cginc"\n#include "UnityLightingCommon.cginc"\n'
        cg += '\n'.join(declarations) + '\n' + STRUCTS + '\n' + '\n'.join(bodies) + '\nENDCG\n'
        first, last = min(p[0] for p in programs), max(p[1] for p in programs)
        new_block = re.sub(r'\s*GpuProgramID \d+', '', block[:first]) + cg + block[last:]
        passes.append((match.start(), end, new_block))
    for start, end, block in reversed(passes):
        updated = updated[:start] + block + updated[end:]
    (OUT / shader_file.name).write_text(updated)
    failures = [x for x in validation if x['hresult'] < 0]
    report.append({'shader': shader_file.name, 'programs': len(validation), 'passes': len(passes), 'failures': failures})
(OUT / 'validation.json').write_text(json.dumps(report, indent=2))
print('Translated', sum(x['programs'] for x in report), 'custom shader programs; HLSL compile failures', sum(len(x['failures']) for x in report))
for item in report:
    for failure in item['failures'][:2]: print(item['shader'], failure['index'], failure['diagnostic'][:700])
raise SystemExit(1 if any(x['failures'] for x in report) else 0)
