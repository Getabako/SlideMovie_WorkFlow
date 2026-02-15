#!/usr/bin/env python3
"""
Google Slides APIで新規プレゼンテーションにスライドを一括作成
YAMLからスライド内容を読み取り、テキストを配置する
1スライド=1 batchUpdateでレート制限を回避
"""

import os, sys, yaml, pickle, time
from pathlib import Path
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

load_dotenv()
PROJECT_ROOT = Path(__file__).parent.parent


def get_credentials():
    creds = None
    token_path = PROJECT_ROOT / 'drive_token.pickle'
    if token_path.exists():
        with open(token_path, 'rb') as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(token_path, 'wb') as f:
                pickle.dump(creds, f)
    return creds


def batch_update_with_retry(service, pres_id, requests, max_retries=3):
    for attempt in range(max_retries):
        try:
            return service.presentations().batchUpdate(
                presentationId=pres_id, body={'requests': requests}
            ).execute()
        except HttpError as e:
            if e.resp.status == 429:
                wait = 30 * (attempt + 1)
                print(f"  レート制限。{wait}秒待機...")
                time.sleep(wait)
            else:
                raise
    raise Exception("リトライ上限")


def create_slides(pres_id, yaml_path):
    creds = get_credentials()
    slides_svc = build('slides', 'v1', credentials=creds)
    drive_svc = build('drive', 'v3', credentials=creds)

    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    slides = data.get('slides', [])
    start = int(os.environ.get('START_FROM', '0'))

    # リネーム
    if start == 0:
        drive_svc.files().update(fileId=pres_id, body={'name': data.get('topic', '無題')}).execute()
        print(f"タイトル設定: {data.get('topic')}")

    # 既存スライド取得
    pres = slides_svc.presentations().get(presentationId=pres_id).execute()
    existing_slides = pres.get('slides', [])
    first_slide_id = existing_slides[0]['objectId'] if existing_slides else None

    for i, slide in enumerate(slides):
        if i < start:
            continue

        title = slide['title']
        content = slide.get('content', '').strip()
        clean = content.replace('## ', '').replace('**', '').replace('- ', '・').replace('|', ' ').replace('---', '')
        
        print(f"スライド {i+1}/{len(slides)}: {title}")

        reqs = []
        import uuid
        uid = uuid.uuid4().hex[:8]
        slide_id = f's{uid}'
        title_id = f't{uid}'
        content_id = f'c{uid}'

        if i == 0 and first_slide_id:
            slide_id = first_slide_id
            # 既存要素削除
            for el in existing_slides[0].get('pageElements', []):
                reqs.append({'deleteObject': {'objectId': el['objectId']}})
        else:
            reqs.append({
                'createSlide': {
                    'objectId': slide_id,
                    'insertionIndex': i,
                    'slideLayoutReference': {'predefinedLayout': 'BLANK'}
                }
            })

        # タイトルボックス
        reqs.append({
            'createShape': {
                'objectId': title_id,
                'shapeType': 'TEXT_BOX',
                'elementProperties': {
                    'pageObjectId': slide_id,
                    'size': {'width': {'magnitude': 8000000, 'unit': 'EMU'}, 'height': {'magnitude': 800000, 'unit': 'EMU'}},
                    'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': 572000, 'translateY': 200000, 'unit': 'EMU'}
                }
            }
        })
        reqs.append({'insertText': {'objectId': title_id, 'text': title, 'insertionIndex': 0}})
        reqs.append({
            'updateTextStyle': {
                'objectId': title_id,
                'style': {
                    'fontSize': {'magnitude': 28, 'unit': 'PT'},
                    'bold': True,
                    'foregroundColor': {'opaqueColor': {'rgbColor': {'red': 1, 'green': 1, 'blue': 1}}}
                },
                'textRange': {'type': 'ALL'},
                'fields': 'fontSize,bold,foregroundColor'
            }
        })

        # コンテンツボックス
        if clean:
            reqs.append({
                'createShape': {
                    'objectId': content_id,
                    'shapeType': 'TEXT_BOX',
                    'elementProperties': {
                        'pageObjectId': slide_id,
                        'size': {'width': {'magnitude': 8000000, 'unit': 'EMU'}, 'height': {'magnitude': 3800000, 'unit': 'EMU'}},
                        'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': 572000, 'translateY': 1200000, 'unit': 'EMU'}
                    }
                }
            })
            reqs.append({'insertText': {'objectId': content_id, 'text': clean, 'insertionIndex': 0}})
            reqs.append({
                'updateTextStyle': {
                    'objectId': content_id,
                    'style': {
                        'fontSize': {'magnitude': 14, 'unit': 'PT'},
                        'foregroundColor': {'opaqueColor': {'rgbColor': {'red': 1, 'green': 1, 'blue': 1}}}
                    },
                    'textRange': {'type': 'ALL'},
                    'fields': 'fontSize,foregroundColor'
                }
            })

        batch_update_with_retry(slides_svc, pres_id, reqs)
        time.sleep(2)

    # 指定フォルダに移動
    target_folder = '1np1rotFHHuRskqDArwlle2_63ILA0n5a'
    try:
        drive_svc.files().update(fileId=pres_id, addParents=target_folder, fields='id,parents').execute()
        print(f"フォルダに移動: {target_folder}")
    except Exception as e:
        print(f"フォルダ移動失敗（手動で移動してください）: {e}")

    print(f"\n完了: {len(slides)}スライド")
    print(f"URL: https://docs.google.com/presentation/d/{pres_id}/edit")


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("使い方: python create_google_slides.py <presentation_id> <yaml_path>")
        sys.exit(1)
    create_slides(sys.argv[1], sys.argv[2])
