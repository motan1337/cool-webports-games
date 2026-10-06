import collections
import contextlib
import hashlib
import io
import json
import struct
from pathlib import Path

root = Path(__file__).resolve().parents[1]
archive = json.loads((root / 'analysis/extraction-inventory.json').read_text())
for image in archive['images']:
    path = root / 'extracted/images' / f'{image["handle"]:04d}.png'
    image.update(file=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
with contextlib.redirect_stdout(io.StringIO()):
    import extract_initial as fusion

def unpack(fmt, data, pos=0):
    return struct.unpack_from('<'+fmt, data, pos)

def chunks(data, pos=0):
    while pos+8 <= len(data):
        cid, flags, size = unpack('HHI', data, pos)
        assert pos+8+size <= len(data)
        raw = data[pos+8:pos+8+size]
        yield cid, fusion.decode(flags, raw), pos
        pos += 8+size
        if cid == 0x7f7f:
            return

def animations(data, base):
    count = unpack('H', data, base+2)[0]
    result = {}
    for index, offset in enumerate(unpack('H'*count, data, base+4)):
        if not offset:
            continue
        start = base+offset
        directions = {}
        for direction, relative in enumerate(unpack('h'*32, data, start)):
            if not relative:
                continue
            pos = start+relative
            minimum, maximum, repeat, repeat_frame, length = unpack('BBhhh', data, pos)
            handles = list(unpack('H'*length, data, pos+8))
            assert all(h in image_handles for h in handles)
            directions[direction] = dict(minimum=minimum, maximum=maximum, repeat=repeat,
                                          repeat_frame=repeat_frame, frames=handles)
        result[index] = directions
    return result

def movements(data, base):
    result = []
    count = unpack('I', data, base)[0]
    for index in range(count):
        name_offset, ident, offset, size = unpack('4I', data, base+4+16*index)
        start = base+offset
        assert start+size <= len(data)
        player, kind, enabled, options, direction = unpack('hhBB2xI', data, start)
        movement = dict(type=kind, enabled=bool(enabled), options=options, direction=direction)
        if kind == 5:
            count, minimum, maximum, loop, reposition, reverse = unpack('hhhBBB', data, start+12)
            movement.update(minimum=minimum, maximum=maximum, loop=bool(loop),
                            reposition=bool(reposition), reverse=bool(reverse), nodes=[])
            pos = start+22
            for _ in range(count):
                node_size = data[pos+1]
                assert node_size >= 16 and pos+node_size <= start+size
                fields = unpack('BBhhhhhh', data, pos+2)
                node = dict(zip(('speed','direction','dx','dy','cosine','sine','length','pause'), fields))
                movement['nodes'].append(node)
                pos += node_size
            # This executable uses only unpaused, forward, single-segment paths.
            assert count <= 1 and not reverse and all(n['pause'] == 0 for n in movement['nodes'])
        else:
            assert kind == 0, f'Unsupported movement type {kind}'
        result.append(movement)
    return result

def properties(data, obj):
    kind = obj['type']
    if kind == 1:
        size, obstacle, collision, width, height, image = unpack('IHHiiH', data)
        obj.update(width=width, height=height, image=image)
        return
    if kind == 0:
        obj['raw_properties'] = data.hex()
        return
    check = unpack('I', data, 6)[0] == 0
    offsets = unpack('6H', data, 4)
    obj['common_flags'] = unpack('I', data, 16)[0]
    obj['qualifiers'] = list(unpack('8h', data, 20))
    data_offset, values_offset, strings_offset, new_flags, preferences = unpack('5H', data, 36)
    obj['new_flags'] = new_flags
    obj['identifier'] = data[46:50].decode('ascii', 'replace')
    animation_offset = offsets[5] if check else offsets[0]
    value_offset = offsets[0] if check else offsets[5]
    movement_offset = offsets[3] if check else offsets[1]
    if movement_offset:
        obj['movements'] = movements(data, movement_offset)
    if animation_offset:
        obj['animations'] = animations(data, animation_offset)
    if values_offset:
        count = unpack('H', data, values_offset)[0]
        obj['alterable_values'] = list(unpack('i'*count, data, values_offset+2))
        obj['alterable_flags'] = unpack('I', data, values_offset+2+count*4)[0]
    if value_offset:
        size, initial, minimum, maximum = unpack('Hiii', data, value_offset)
        obj.update(initial=initial, minimum=minimum, maximum=maximum)
    if data_offset and obj['identifier'][:2] in ('CN', 'SC', 'LI'):
        size, width, height, player, display, digits, font = unpack('IiiHHHH', data, data_offset)
        obj.update(width=width, height=height, display=display, digits=digits, font=font)
        if display in (1, 4):
            count = unpack('H', data, data_offset+20)[0]
            obj['counter_frames'] = list(unpack('H'*count, data, data_offset+22))
    if data_offset and obj['identifier'][:2] in ('TE','QS'):
        size, width, height, count = unpack('Iiii', data, data_offset)
        obj.update(width=width,height=height,paragraphs=[])
        for relative in unpack('i'*count,data,data_offset+16):
            p = data_offset+relative
            font, flags = unpack('HH',data,p)
            text = data[p+8:].decode('utf-16le', 'replace').split('\0')[0]
            obj['paragraphs'].append(dict(font=font+1,flags=flags,color=list(data[p+4:p+7]),text=text))
    obj['raw_properties'] = data.hex()
    if kind == 32 and obj['identifier'] == 'tksp':
        extension = offsets[4]
        size, ignored, version, ident, private = unpack('5I',data,extension)
        p = extension+20
        sx,sy,width,height,effect,direction = unpack('hhhhBB',data,p)
        zoom,offset,waves = unpack('iii',data,p+12)
        obj['perspective'] = dict(width=width,height=height,effect=effect,direction=direction,
                                  zoom=zoom,offset=offset,waves=waves,perspective_direction=data[p+24],resample=bool(data[p+25]))

image_handles = {i['handle'] for i in archive['images']}
object_chunk = next(c for c in fusion.inventory['chunks'] if c['id'] == '2229')
start = object_chunk['offset']+8
objects_data = fusion.source[start:start+object_chunk['size']]
object_count = unpack('I', objects_data)[0]
objects = {}
position = 4
for _ in range(object_count):
    obj = {}
    for cid, data, offset in chunks(objects_data, position):
        if cid == 0x4444:
            handle, kind, flags, ignored, ink, ink_flags, coefficient = unpack('hhHHhHI', data)
            obj.update(handle=handle, type=kind, flags=flags, ink=ink, ink_flags=ink_flags,
                        coefficient=coefficient)
        elif cid == 0x4445:
            obj['name'] = data.decode('utf-16le').rstrip('\0')
        elif cid == 0x4446:
            properties(data, obj)
        elif cid == 0x7f7f:
            position = offset+8
    objects[obj['handle']] = obj
assert position == len(objects_data)

expression_codes = {15,22,23,27,28,45,46,52,53,54,59,62}
short_codes = {3,4,10,11,12,14,17,26,31,37,43,44,50,58,60,61}
int_codes = {5,25,29,34,48,49,56,67,70}
expression_histogram = collections.Counter()
parameter_histogram = collections.Counter()

def parameter(code, data, offset):
    result = dict(code=code, raw=data.hex(), offset=offset)
    parameter_histogram[code] += 1
    if code in short_codes:
        result['value'] = unpack('h', data)[0]
    elif code in int_codes or code in (2,42):
        result['value'] = unpack('i', data)[0]
    elif code in (6,7,35,36):
        result['handle'], result['flags'] = unpack('HH', data)
    elif code in (40,41,63,64):
        result['value'] = data.decode('utf-16le').split('\0')[0]
    elif code == 13:
        result['delay'], result['counter'] = unpack('ii', data)
    elif code == 32:
        result['button'], result['double'] = unpack('BB', data)
    elif code == 1:
        result['object_list'], result['object'], result['type'] = unpack('hHh', data)
    elif code in (9,16,21):
        fields = unpack('HHhhhhi hh h'.replace(' ', ''), data)
        result.update(zip(('parent','flags','x','y','slope','angle','direction','parent_type','object_list','layer'), fields))
        if code == 9:
            result['instance'], result['object'] = unpack('HH', data, 22)
    elif code == 38:
        result['flags'], result['group_id'] = unpack('Hh', data)
        result['name'] = data[4:162].decode('utf-16le').split('\0')[0]
        result['pointer'] = offset-36
    elif code == 39:
        result['relative'], result['group_id'] = unpack('ii', data)
        result['pointer'] = offset-4+result['relative']
    elif code in expression_codes:
        result['comparison'] = unpack('h', data)[0]
        result['tokens'] = []
        pos = 2
        while pos+4 <= len(data):
            kind, number = unpack('hh', data, pos)
            if kind == number == 0:
                assert pos+4 == len(data), (code, pos, len(data))
                break
            size = unpack('H', data, pos+4)[0]
            assert size >= 6 and pos+size <= len(data)
            payload = data[pos+6:pos+size]
            token = dict(type=kind, number=number, raw=payload.hex())
            if kind == -1 and number == 0:
                token['value'] = unpack('i', payload)[0]
            elif kind == -1 and number == 3:
                token['value'] = payload.decode('utf-16le').split('\0')[0]
            elif kind == -1 and number == 23:
                token['value'] = unpack('d', payload)[0]
            elif kind == -1 and number in (24,50):
                token['value'] = unpack('i', payload, 4)[0]
            elif kind > 1 or kind == -7:
                token['object'], token['object_list'] = unpack('Hh', payload)
                if number in (16,19):
                    token['value'] = unpack('h', payload, 4)[0]
            expression_histogram[(kind, number)] += 1
            result['tokens'].append(token)
            pos += size
    return result

event_histograms = dict(conditions=collections.Counter(), actions=collections.Counter())
frames = []
for original in archive['frames']:
    frame = {k: original[k] for k in ('index','name','width','height')}
    frame_header = Path(next(c['file'] for c in original['chunks'] if c['id'] == '3334')).read_bytes()
    frame['flags'] = unpack('I', frame_header, 12)[0]
    timer_chunk = next((c for c in original['chunks'] if c['id'] == '3347'), None)
    frame['movement_timer_base'] = unpack('I', Path(timer_chunk['file']).read_bytes())[0] if timer_chunk else 50
    frame['layers'] = []
    layer_chunk = next((c for c in original['chunks'] if c['id'] == '3341'), None)
    if layer_chunk:
        layer_data = Path(layer_chunk['file']).read_bytes()
        layer_count = unpack('I', layer_data)[0]
        layer_pos = 4
        for _ in range(layer_count):
            flags, x_coefficient, y_coefficient, backdrop_count, backdrop_index = unpack('Iffii', layer_data, layer_pos)
            layer_pos += 20
            name_start = layer_pos
            while layer_data[layer_pos:layer_pos+2] != b'\x00\x00':
                layer_pos += 2
            name = layer_data[name_start:layer_pos].decode('utf-16le')
            layer_pos += 2
            frame['layers'].append(dict(flags=flags, x_coefficient=x_coefficient,
                                        y_coefficient=y_coefficient, backdrop_count=backdrop_count,
                                        backdrop_index=backdrop_index, name=name))
        assert layer_pos == len(layer_data)
    frame['instances'] = []
    instance_chunk = next((c for c in original['chunks'] if c['id'] == '3338'), None)
    if instance_chunk:
        data = Path(instance_chunk['file']).read_bytes()
        count = unpack('I', data)[0]
        assert len(data) == 8+20*count
        frame['instance_trailer'] = data[-4:].hex()
        for i in range(count):
            handle, obj, x, y, parent, value, layer, parent_handle = unpack('HHiiHhHH', data, 4+20*i)
            frame['instances'].append(dict(handle=handle, object=obj, x=x, y=y, parent=parent,
                                            value=value, layer=layer, parent_handle=parent_handle))
    event_chunk = next(c for c in original['chunks'] if c['id'] == '333d')
    data = Path(event_chunk['file']).read_bytes()
    begin = data.index(b'ERev')
    end = begin+8+unpack('I', data, begin+4)[0]
    pos = begin+8
    frame['events'] = []
    while pos < end:
        size, condition_count, action_count, flags = unpack('hBBH', data, pos)
        size = abs(size)
        event = dict(offset=pos, flags=flags, conditions=[], actions=[])
        cursor = pos+16
        for label, count in (('conditions', condition_count), ('actions', action_count)):
            for _ in range(count):
                length, kind, number, obj, obj_list, ef, other, params, default = unpack('HhhHhBBBB', data, cursor)
                item = dict(offset=cursor, type=kind, number=number, object=obj, object_list=obj_list,
                            flags=ef, other_flags=other, parameters=[])
                parameter_pos = cursor+(16 if label == 'conditions' else 14)
                for _ in range(params):
                    parameter_size, code = unpack('Hh', data, parameter_pos)
                    assert parameter_size >= 4 and parameter_pos+parameter_size <= cursor+length
                    item['parameters'].append(parameter(code, data[parameter_pos+4:parameter_pos+parameter_size], parameter_pos+4))
                    parameter_pos += parameter_size
                assert parameter_pos == cursor+length, (frame['index'],cursor,parameter_pos,cursor+length)
                event[label].append(item)
                event_histograms[label][(kind, number)] += 1
                cursor += length
        assert cursor == pos+size, (frame['index'],pos,cursor,pos+size)
        frame['events'].append(event)
        pos += size
    assert pos == end
    frames.append(frame)

def app_chunk(cid):
    chunk = next(c for c in fusion.inventory['chunks'] if c['id'] == cid)
    p = chunk['offset']+8
    return fusion.decode(chunk['flags'],fusion.source[p:p+chunk['size']])

header = app_chunk('2223')
frame_handle_data = app_chunk('222b')
frame_handles = list(unpack('h'*(len(frame_handle_data)//2),frame_handle_data))
fonts = {}
font_data = app_chunk('6667')
count = unpack('I',font_data)[0]
pos = 4
for _ in range(count):
    handle,expected,size = unpack('III',font_data,pos)
    font = fusion.inflate(font_data[pos+12:pos+12+size])
    assert len(font)==expected
    height,width,escape,orientation,weight = unpack('iiiii',font,12)
    fonts[handle]=dict(height=height,width=width,weight=weight,italic=font[32],name=font[40:104].decode('utf-16le').split('\0')[0])
    pos+=12+size
assert pos==len(font_data)

game = dict(objects=objects, frames=frames, frame_handles=frame_handles, fonts=fonts,
            frame_rate=unpack('I',header,104)[0], width=unpack('h',header,12)[0],height=unpack('h',header,14)[0],
            images=[{k:i[k] for k in ('handle','width','height','hotspot','action_point')} for i in archive['images']],
            sounds=[dict(handle=s['handle'], name=s['name'], path='extracted/audio/'+Path(s['file']).name) for s in archive['sounds']])
(root / 'analysis/game-data.json').write_text(json.dumps(game, indent=2), encoding='utf-8')
(root / 'game-data.js').write_text('window.FNAF_DATA='+json.dumps(game,separators=(',',':')).replace('<','\\u003c')+';\n', encoding='utf-8')
stats = {key:[dict(type=k[0],number=k[1],count=v) for k,v in counts.most_common()]
         for key,counts in event_histograms.items()}
stats['expressions'] = [dict(type=k[0],number=k[1],count=v) for k,v in expression_histogram.most_common()]
stats['parameters'] = dict(parameter_histogram)
(root / 'analysis/opcode-inventory.json').write_text(json.dumps(stats, indent=2), encoding='utf-8')
print('Decoded', len(objects), 'objects and', sum(len(f['events']) for f in frames), 'event groups')
print('Opcode counts:', {k:len(v) for k,v in stats.items()})
print('Rate:',game['frame_rate'],'Frame handles:',frame_handles,'Fonts:',fonts)
# Preserve the completed PNG inventory after the import's reproducible extraction pass.
(root / 'analysis/extraction-inventory.json').write_text(json.dumps(archive, indent=2), encoding='utf-8')
