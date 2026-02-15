#!/usr/bin/env python3
"""
既存Google Slidesの全スライドのテキスト内容をYAMLから更新する。
スライド数は変えず、各スライドの全要素を削除→新テキストを配置。
"""

import sys, yaml, pickle, time, uuid
from pathlib import Path
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

PROJECT_ROOT = Path(__file__).parent.parent
PRES_ID = '1_hNmyanUhPnvLhrb-qzAFjcB8ZYttIGHf9bWL5Ity6A'


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


def main():
    yaml_path = PROJECT_ROOT / 'inputs' / '鳥取大学式ペアレントトレーニング.yml'

    creds = get_credentials()
    slides_svc = build('slides', 'v1', credentials=creds)

    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    yaml_slides = data.get('slides', [])
    print(f"YAMLスライド数: {len(yaml_slides)}")

    # 既存プレゼン取得
    pres = slides_svc.presentations().get(presentationId=PRES_ID).execute()
    existing = pres.get('slides', [])
    print(f"既存スライド数: {len(existing)}")

    if len(yaml_slides) != len(existing):
        print(f"警告: スライド数が一致しません (YAML:{len(yaml_slides)} vs 既存:{len(existing)})")
        print("スライド数が少ない方に合わせます")

    count = min(len(yaml_slides), len(existing))

    for i in range(count):
        slide_id = existing[i]['objectId']
        title = yaml_slides[i]['title']
        content = yaml_slides[i].get('content', '').strip()
        clean = content.replace('## ', '').replace('**', '').replace('- ', '・').replace('|', ' ').replace('---', '')

        print(f"スライド {i+1}/{count}: {title}")

        reqs = []

        # 1. 既存の全要素を削除
        for elem in existing[i].get('pageElements', []):
            reqs.append({'deleteObject': {'objectId': elem['objectId']}})

        # 2. 背景を白にリセット
        reqs.append({
            'updatePageProperties': {
                'objectId': slide_id,
                'pageProperties': {
                    'pageBackgroundFill': {
                        'solidFill': {
                            'color': {
                                'rgbColor': {'red': 1.0, 'green': 1.0, 'blue': 1.0}
                            }
                        }
                    }
                },
                'fields': 'pageBackgroundFill'
            }
        })

        # 3. タイトルテキストボックス
        uid = uuid.uuid4().hex[:8]
        title_id = f't{uid}'
        content_id = f'c{uid}'

        reqs.append({
            'createShape': {
                'objectId': title_id,
                'shapeType': 'TEXT_BOX',
                'elementProperties': {
                    'pageObjectId': slide_id,
                    'size': {
                        'width': {'magnitude': 8000000, 'unit': 'EMU'},
                        'height': {'magnitude': 800000, 'unit': 'EMU'}
                    },
                    'transform': {
                        'scaleX': 1, 'scaleY': 1,
                        'translateX': 572000, 'translateY': 200000,
                        'unit': 'EMU'
                    }
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
                    'foregroundColor': {'opaqueColor': {'rgbColor': {'red': 0.1, 'green': 0.1, 'blue': 0.1}}}
                },
                'textRange': {'type': 'ALL'},
                'fields': 'fontSize,bold,foregroundColor'
            }
        })

        # 4. コンテンツテキストボックス
        if clean:
            reqs.append({
                'createShape': {
                    'objectId': content_id,
                    'shapeType': 'TEXT_BOX',
                    'elementProperties': {
                        'pageObjectId': slide_id,
                        'size': {
                            'width': {'magnitude': 8000000, 'unit': 'EMU'},
                            'height': {'magnitude': 3800000, 'unit': 'EMU'}
                        },
                        'transform': {
                            'scaleX': 1, 'scaleY': 1,
                            'translateX': 572000, 'translateY': 1200000,
                            'unit': 'EMU'
                        }
                    }
                }
            })
            reqs.append({'insertText': {'objectId': content_id, 'text': clean, 'insertionIndex': 0}})
            reqs.append({
                'updateTextStyle': {
                    'objectId': content_id,
                    'style': {
                        'fontSize': {'magnitude': 14, 'unit': 'PT'},
                        'foregroundColor': {'opaqueColor': {'rgbColor': {'red': 0.2, 'green': 0.2, 'blue': 0.2}}}
                    },
                    'textRange': {'type': 'ALL'},
                    'fields': 'fontSize,foregroundColor'
                }
            })

        batch_update_with_retry(slides_svc, PRES_ID, reqs)
        time.sleep(1.5)

    print(f"\n完了: {count}スライドを更新")
    print(f"URL: https://docs.google.com/presentation/d/{PRES_ID}/edit")


if __name__ == '__main__':
    main()
