#!/usr/bin/env python3
"""
スライド上の画像オブジェクトを背景に設定し、元のオブジェクトを削除する。

使い方:
  python3 scripts/set_image_as_background.py <presentation_id> <slide_index>

slide_index は 0-based。
"""

import sys
import pickle
from pathlib import Path
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

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


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 scripts/set_image_as_background.py <pres_id> <slide_index>")
        sys.exit(1)

    pres_id = sys.argv[1]
    slide_idx = int(sys.argv[2])

    creds = get_credentials()
    slides_service = build('slides', 'v1', credentials=creds)

    pres = slides_service.presentations().get(presentationId=pres_id).execute()
    slides = pres.get('slides', [])

    if slide_idx >= len(slides):
        print(f"スライドインデックス {slide_idx} が範囲外 (total={len(slides)})")
        sys.exit(1)

    slide = slides[slide_idx]
    slide_id = slide['objectId']

    # スライド上の画像要素を探す
    image_elements = []
    for elem in slide.get('pageElements', []):
        if 'image' in elem:
            content_url = elem['image'].get('contentUrl', '')
            obj_id = elem['objectId']
            # サイズ情報も取得
            size = elem.get('size', {})
            w = size.get('width', {}).get('magnitude', 0)
            h = size.get('height', {}).get('magnitude', 0)
            if content_url:
                image_elements.append({
                    'objectId': obj_id,
                    'contentUrl': content_url,
                    'area': w * h,
                })

    if not image_elements:
        print(f"スライド {slide_idx} に画像要素がありません")
        sys.exit(1)

    # 最大の画像を選択（最後に追加されたものが最大のことが多い）
    # objectId でソートして最新を取得、またはエリアが最大のものを選択
    target = max(image_elements, key=lambda x: x['area']) if len(image_elements) > 1 else image_elements[0]

    print(f"画像要素: {target['objectId']} (area={target['area']:.0f})")

    requests = [
        # 背景に設定
        {
            'updatePageProperties': {
                'objectId': slide_id,
                'pageProperties': {
                    'pageBackgroundFill': {
                        'stretchedPictureFill': {
                            'contentUrl': target['contentUrl'],
                        }
                    }
                },
                'fields': 'pageBackgroundFill'
            }
        },
        # 画像オブジェクトを削除
        {
            'deleteObject': {
                'objectId': target['objectId']
            }
        }
    ]

    slides_service.presentations().batchUpdate(
        presentationId=pres_id, body={'requests': requests}
    ).execute()
    print(f"完了: スライド {slide_idx} の背景を設定、画像オブジェクト削除")


if __name__ == '__main__':
    main()
