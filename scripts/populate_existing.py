#!/usr/bin/env python3
"""既存プレゼンにスライドを投入"""
import sys, pickle, re
from pathlib import Path
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

PROJECT_ROOT = Path(__file__).parent.parent

def get_creds():
    tp = PROJECT_ROOT / 'slides_token.pickle'
    with open(tp, 'rb') as f:
        c = pickle.load(f)
    if c and c.expired and c.refresh_token:
        c.refresh(Request())
        with open(tp, 'wb') as f:
            pickle.dump(c, f)
    return c

def parse_slides(md):
    with open(md, 'r') as f:
        content = f.read()
    content = re.sub(r'^---\n.*?---\n', '', content, count=1, flags=re.DOTALL)
    return [s.strip() for s in content.split('\n---\n') if s.strip()]

def to_title_body(text):
    lines = text.split('\n')
    title = ''
    body = []
    for line in lines:
        if not title and line.startswith('#'):
            title = line.lstrip('#').strip()
        else:
            body.append(line)
    if not title:
        title = lines[0].strip() if lines else ''
        body = lines[1:]
    b = '\n'.join(body).strip()
    b = re.sub(r'\*\*(.+?)\*\*', r'\1', b)
    return title, b

def main():
    pres_id = sys.argv[1]
    md_path = sys.argv[2]
    
    slides = parse_slides(md_path)
    print(f"{len(slides)} 枚検出")
    
    creds = get_creds()
    svc = build('slides', 'v1', credentials=creds)
    
    # Delete all existing slides
    pres = svc.presentations().get(presentationId=pres_id).execute()
    existing = pres.get('slides', [])
    if len(existing) > 1:
        reqs = [{'deleteObject': {'objectId': s['objectId']}} for s in existing[1:]]
        svc.presentations().batchUpdate(presentationId=pres_id, body={'requests': reqs}).execute()
    
    # Update first slide
    pres = svc.presentations().get(presentationId=pres_id).execute()
    first = pres['slides'][0]
    t, b = to_title_body(slides[0])
    
    reqs = []
    for el in first.get('pageElements', []):
        sh = el.get('shape', {})
        ph = sh.get('placeholder', {})
        pt = ph.get('type', '')
        oid = el['objectId']
        tc = sh.get('text', {})
        has = any(te.get('textRun', {}).get('content', '').strip() for te in tc.get('textElements', []))
        
        if 'TITLE' in pt or 'CENTERED_TITLE' in pt:
            if has:
                reqs.append({'deleteText': {'objectId': oid, 'textRange': {'type': 'ALL'}}})
            reqs.append({'insertText': {'objectId': oid, 'insertionIndex': 0, 'text': t}})
        elif pt in ('SUBTITLE', 'BODY'):
            if has:
                reqs.append({'deleteText': {'objectId': oid, 'textRange': {'type': 'ALL'}}})
            if b:
                reqs.append({'insertText': {'objectId': oid, 'insertionIndex': 0, 'text': b}})
    
    if reqs:
        svc.presentations().batchUpdate(presentationId=pres_id, body={'requests': reqs}).execute()
    print(f"1: {t}")
    
    # Add rest
    for i, st in enumerate(slides[1:], 2):
        t, b = to_title_body(st)
        layout = 'TITLE_AND_BODY' if b else 'SECTION_HEADER'
        
        res = svc.presentations().batchUpdate(presentationId=pres_id, body={'requests': [
            {'createSlide': {'insertionIndex': i-1, 'slideLayoutReference': {'predefinedLayout': layout}}}
        ]}).execute()
        
        sid = res['replies'][0]['createSlide']['objectId']
        pres = svc.presentations().get(presentationId=pres_id).execute()
        ns = next((s for s in pres['slides'] if s['objectId'] == sid), None)
        
        if ns:
            r2 = []
            td = bd = False
            for el in ns.get('pageElements', []):
                sh = el.get('shape', {})
                ph = sh.get('placeholder', {})
                pt = ph.get('type', '')
                oid = el['objectId']
                tc = sh.get('text', {})
                has = any(te.get('textRun', {}).get('content', '').strip() for te in tc.get('textElements', []))
                
                if 'TITLE' in pt and not td:
                    if has:
                        r2.append({'deleteText': {'objectId': oid, 'textRange': {'type': 'ALL'}}})
                    r2.append({'insertText': {'objectId': oid, 'insertionIndex': 0, 'text': t}})
                    td = True
                elif not bd and pt in ('BODY', 'SUBTITLE', 'DESCRIPTION'):
                    if b:
                        if has:
                            r2.append({'deleteText': {'objectId': oid, 'textRange': {'type': 'ALL'}}})
                        r2.append({'insertText': {'objectId': oid, 'insertionIndex': 0, 'text': b}})
                    bd = True
            
            if r2:
                svc.presentations().batchUpdate(presentationId=pres_id, body={'requests': r2}).execute()
        print(f"{i}: {t}")
    
    print(f"\n完了！ {len(slides)} 枚")

if __name__ == '__main__':
    main()
