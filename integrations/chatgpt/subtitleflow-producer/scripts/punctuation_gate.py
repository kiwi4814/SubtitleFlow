#!/usr/bin/env python3
import argparse, json, re
from pathlib import Path

TAG_RE = re.compile(r"\{[^}]*\}")

def parse(path):
    out=[]
    for i,line in enumerate(path.read_text(encoding='utf-8-sig',errors='replace').splitlines(),1):
        if not line.startswith('Dialogue:'): continue
        parts=line.split(':',1)[1].lstrip().split(',',9)
        if len(parts)!=10: continue
        start,end,style,effect,text=parts[1],parts[2],parts[3],parts[8],parts[9]
        visible=TAG_RE.sub('',text).replace(r'\N','\n')
        out.append((i,start,end,style,effect,visible))
    return out

def main():
    ap=argparse.ArgumentParser(description='Hard typography/notation acceptance gates; semantic mismatch requires model review and is not auto-fixed.')
    ap.add_argument('ass')
    ap.add_argument('--target-style',default='SF-ZH')
    ap.add_argument('--json',action='store_true')
    args=ap.parse_args()
    ev=parse(Path(args.ass))
    target=[x for x in ev if x[3]==args.target_style]
    issues=[]
    def add(code,row,detail):
        issues.append({'code':code,'line_no':row[0],'start':row[1],'style':row[3],'text':row[5],'detail':detail})
    for row in target:
        s=row[5]
        if '?' in s: add('ASCII_QUESTION',row,'Use full-width Chinese question mark after semantic judgment.')
        if '!' in s: add('ASCII_EXCLAMATION',row,'Use full-width Chinese exclamation mark after semantic judgment.')
        if '...' in s: add('ASCII_ELLIPSIS',row,'Do not mechanically convert; verify ellipsis semantics, then use …… if valid.')
    # Presentation leaks: flag for review, because some marks can be literal quotation.
    for row in ev:
        s=row[5]
        for mark,code in [('→','SOURCE_ARROW_LEAK'),('≪','SOURCE_OFFSCREEN_MARK_LEAK'),('《','DOUBLE_ANGLE_OPEN'),('》','DOUBLE_ANGLE_CLOSE')]:
            if mark in s: add(code,row,'Classify source notation before presentation; do not blindly delete literal content.')
    result={'file':Path(args.ass).name,'target_style':args.target_style,'issue_count':len(issues),'issues':issues,'hard_pass':len(issues)==0}
    if args.json: print(json.dumps(result,ensure_ascii=False,indent=2))
    else:
        print(f"issues={len(issues)} hard_pass={result['hard_pass']}")
        from collections import Counter
        print(Counter(i['code'] for i in issues))
if __name__=='__main__': main()
