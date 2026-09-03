#!/usr/bin/env python3
import argparse, json, re, hashlib
from pathlib import Path
from collections import Counter
TAG_RE=re.compile(r"\{[^}]*\}"); POS_RE=re.compile(r"\\pos\(([-\d.]+),([-\d.]+)\)"); FSCX_RE=re.compile(r"\\fscx(\d+(?:\.\d+)?)"); SPEAKER_RE=re.compile(r"^[（(]([^（）()]{1,30})[）)]")
def strip_tags(text): return TAG_RE.sub('',text).replace(r'\N','\n').strip()
def parse_dialogue(line):
    if not line.startswith(('Dialogue:','Comment:')): return None
    kind,rest=line.split(':',1); parts=rest.lstrip().split(',',9)
    if len(parts)!=10: return None
    layer,start,end,style,name,ml,mr,mv,effect,text=parts
    return {'kind':kind,'layer':layer,'start':start,'end':end,'style':style,'name':name,'margin_l':ml,'margin_r':mr,'margin_v':mv,'effect':effect,'text_raw':text.rstrip('\r\n'),'text':strip_tags(text.rstrip('\r\n'))}
def sha256(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
    return h.hexdigest()
def terminal_class(s):
    s=s.rstrip()
    if re.search(r'[？?][！!]$|[！!][？?]$',s): return '?!'
    if re.search(r'(?:……|\.\.\.|…)$',s): return 'ellipsis'
    if re.search(r'[？?]$',s): return 'question'
    if re.search(r'[！!]$',s): return 'exclamation'
    return 'none'
def analyze(path,target_style=None,expected_pos=None,require_q2=False,forbid_effects=()):
    events=[]
    for i,line in enumerate(path.read_text(encoding='utf-8-sig',errors='replace').splitlines(),1):
        ev=parse_dialogue(line)
        if ev: ev['line_no']=i; events.append(ev)
    dialogue=[e for e in events if e['kind']=='Dialogue']; styles=Counter(e['style'] for e in dialogue); effects=Counter(e['effect'] for e in dialogue if e['effect']); term=Counter(terminal_class(e['text']) for e in dialogue)
    pos=Counter(); fscx=[]; speaker=[]; notation=Counter(); notation_events=[]
    for e in dialogue:
        for m in POS_RE.finditer(e['text_raw']): pos[(m.group(1),m.group(2))]+=1
        for m in FSCX_RE.finditer(e['text_raw']): fscx.append((float(m.group(1)),e['line_no'],e['start'],e['style'],e['text']))
        sm=SPEAKER_RE.match(e['text'])
        if sm: speaker.append((e['line_no'],e['start'],sm.group(1),e['text']))
        marks=[]
        for label,pat in [('ascii_q',r'\?'),('ascii_bang',r'!'),('ascii_ellipsis',r'\.\.\.'),('jp_corner_open',r'[「｢]'),('jp_corner_close',r'[」｣]'),('double_angle_open',r'《'),('double_angle_close',r'》'),('double_lt',r'≪'),('arrow',r'→'),('music',r'♪')]:
            c=len(re.findall(pat,e['text']))
            if c: notation[label]+=c; marks.append((label,c))
        if marks: notation_events.append({'line_no':e['line_no'],'start':e['start'],'style':e['style'],'text':e['text'],'marks':marks})
    gate_events=[e for e in dialogue if not target_style or e['style']==target_style]
    exp=None
    if expected_pos:
        x,y=expected_pos.split(',',1); exp=(str(float(x)).rstrip('0').rstrip('.'),str(float(y)).rstrip('0').rstrip('.'))
    def has_expected(e):
        if not exp: return True
        vals=[(m.group(1).rstrip('0').rstrip('.') if '.' in m.group(1) else m.group(1),m.group(2).rstrip('0').rstrip('.') if '.' in m.group(2) else m.group(2)) for m in POS_RE.finditer(e['text_raw'])]
        return exp in vals
    profile_issues=[]
    for e in gate_events:
        if exp and not has_expected(e): profile_issues.append({'code':'EXPECTED_POS_MISSING','line_no':e['line_no'],'start':e['start'],'style':e['style'],'text':e['text']})
        if require_q2 and r'\q2' not in e['text_raw']: profile_issues.append({'code':'Q2_MISSING','line_no':e['line_no'],'start':e['start'],'style':e['style'],'text':e['text']})
        for fx in forbid_effects:
            if fx and fx in e['effect']: profile_issues.append({'code':'FORBIDDEN_EFFECT','value':fx,'line_no':e['line_no'],'start':e['start'],'style':e['style'],'text':e['text']})
    return {'file':path.name,'sha256':sha256(path),'dialogue_events':len(dialogue),'styles':dict(styles),'effects':dict(effects),'terminal_classes':dict(term),'explicit_linebreak_events':sum(r'\N' in e['text_raw'] for e in dialogue),'q2_events':sum(r'\q2' in e['text_raw'] for e in dialogue),'positions':{f'{x},{y}':c for (x,y),c in pos.items()},'fscx_count':len(fscx),'fscx_min':min((x[0] for x in fscx),default=None),'fscx_below_85':sum(x[0]<85 for x in fscx),'speaker_tag_events':len(speaker),'notation_counts':dict(notation),'notation_events':notation_events,'profile_gate':{'target_style':target_style,'expected_pos':expected_pos,'require_q2':require_q2,'forbid_effects':list(forbid_effects),'checked_events':len(gate_events),'issue_count':len(profile_issues),'issues':profile_issues,'hard_pass':len(profile_issues)==0}}
def main():
    ap=argparse.ArgumentParser(description='Deterministic ASS inventory/audit. It flags facts; it does not make semantic subtitle decisions.')
    ap.add_argument('ass',nargs='+'); ap.add_argument('--json',action='store_true'); ap.add_argument('--target-style'); ap.add_argument('--expected-pos',help='Expected explicit x,y for target events, e.g. 320,453'); ap.add_argument('--require-q2',action='store_true'); ap.add_argument('--forbid-effect',action='append',default=[])
    args=ap.parse_args(); out=[analyze(Path(p),args.target_style,args.expected_pos,args.require_q2,args.forbid_effect) for p in args.ass]
    if args.json: print(json.dumps(out if len(out)>1 else out[0],ensure_ascii=False,indent=2)); return
    for r in out:
        print(f"{r['file']}: dialogue={r['dialogue_events']} styles={r['styles']} q2={r['q2_events']} linebreak={r['explicit_linebreak_events']}")
        print(f"  notation={r['notation_counts']} fscx_min={r['fscx_min']} fscx<85={r['fscx_below_85']} profile_gate={r['profile_gate']['hard_pass']} issues={r['profile_gate']['issue_count']}")
if __name__=='__main__': main()
