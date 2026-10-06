import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
game = json.loads((root / 'analysis/game-data.json').read_text())
objects = game['objects']
def name(handle):
    return objects.get(str(handle), {}).get('name', str(handle)) + f'#{handle}'

condition_labels = {
    (-3,-1):'start',(-1,-1):'always',(-1,-3):'compare',(-1,-6):'once',(-1,-7):'on change',
    (-4,-8):'every',(-4,-7):'timer equals',(-4,-1):'timer greater',
    (-6,-1):'key pressed',(-6,-2):'key held',(-6,-4):'pointer over',(-6,-5):'click',(-6,-7):'click on',
    (7,-81):'counter compare', (2,-42):'alterable compare', (2,-27):'alterable compare',
    (2,-4):'overlapping', (2,-3):'animation playing', (2,-2):'animation finished',
    (2,-1):'animation frame', (2,-17):'x compare', (2,-29):'visible', (2,-7):'stopped',
}
action_labels = {
    (-3,0):'next frame',(-3,2):'jump',(-3,4):'end app',(-3,8):'scroll x',(-5,0):'create',
    (-2,1):'stop all sound',(-2,11):'play channel',(-2,12):'loop channel',(-2,17):'channel volume',
    (7,80):'set counter',(7,81):'add counter',(7,82):'subtract counter',
    (7,26):'hide',(7,27):'show',
    (2,1):'position',(2,2):'set x',(2,17):'animation',(2,24):'destroy',(2,26):'hide',(2,27):'show',
    (2,31):'set alt',(2,32):'add alt',(2,33):'subtract alt',(2,65):'alpha',
    (33,80):'INI group',(33,86):'INI file',(33,87):'INI set value item',
}

def expression(tokens):
    result = ''
    for t in tokens:
        kind, number = t['type'], t['number']
        if kind == -1:
            result += {0:str(t.get('value')),3:repr(t.get('value')),1:'random(', -1:'(', -2:')'}.get(number, f'E{number}')
        elif kind == 0:
            result += {2:' + ',4:' - ',6:' * ',8:' / '}.get(number, f'O{number}')
        else:
            result += {80:'counter',16:'alt'+str(t.get('value')),11:'x',82:'INI item',85:'day',86:'month'}.get(number,str(number))+'('+name(t['object'])+')'
    return result

def parameter(p):
    if 'tokens' in p:
        return ['=','!=','<=','<','>=','>'][p['comparison']]+' '+expression(p['tokens'])
    if p['code'] == 1:
        return name(p['object'])
    if p['code'] in (9,16,21):
        return f'({p["x"]},{p["y"]}) parent {p["parent"]}'+(f' create {name(p["object"])}' if p['code']==9 else '')
    if 'handle' in p:
        return 'sample '+str(p['handle'])
    return repr(p.get('value', p.get('button', p['raw'])))

lines = []
for frame in game['frames']:
    lines.append(f'FRAME {frame["index"]}: {frame["name"]}')
    for i,event in enumerate(frame['events']):
        lines.append(f'  EVENT {i} @ {event["offset"]} flags {event["flags"]}')
        for label in ('conditions','actions'):
            table = condition_labels if label == 'conditions' else action_labels
            for item in event[label]:
                ident = (item['type'],item['number'])
                title = table.get(ident,str(ident))
                if item['type'] > 0:
                    title += ' '+name(item['object'])
                negated = 'NOT ' if item['other_flags'] & 1 else ''
                lines.append('    '+('IF ' if label=='conditions' else 'DO ')+negated+title+' / '+', '.join(parameter(p) for p in item['parameters']))
(root / 'analysis/events-readable.txt').write_text('\n'.join(lines), encoding='utf-8')
print('Wrote',root / 'analysis/events-readable.txt')
