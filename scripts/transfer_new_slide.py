#!/usr/bin/env python3
"""
新しく挿入されたスライドの画像/背景を元スライドに転送し、新スライドを削除する。

使い方:
  python3 scripts/transfer_new_slide.py <presentation_id> <target_slide_index>

target_slide_index は 0-based。新スライドは target_slide_index + 1 にあると想定。
"""

import sys
import pickle
import time
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
        print("Usage: python3 scripts/transfer_new_slide.py <pres_id> <target_index>")
        sys.exit(1)

    pres_id = sys.argv[1]
    target_idx = int(sys.argv[2])

    creds = get_credentials()
    slides_service = build('slides', 'v1', credentials=creds)

    # プレゼンの現在状態を取得
    pres = slides_service.presentations().get(presentationId=pres_id).execute()
    slides = pres.get('slides', [])

    # 新スライドは target_idx + 1 にあるはず
    new_idx = target_idx + 1
    if new_idx >= len(slides):
        print(f"新スライドが見つかりません (target={target_idx}, total={len(slides)})")
        sys.exit(1)

    target_slide = slides[target_idx]
    new_slide = slides[new_idx]
    target_id = target_slide['objectId']
    new_id = new_slide['objectId']

    # 新スライドから画像URLを抽出
    image_url = None

    # 1. 背景画像をチェック
    bg = new_slide.get('pageProperties', {}).get('pageBackgroundFill', {})
    if 'stretchedPictureFill' in bg:
        image_url = bg['stretchedPictureFill'].get('contentUrl', '')

    # 2. page elements から image を探す
    if not image_url:
        for elem in new_slide.get('pageElements', []):
            if 'image' in elem:
                image_url = elem['image'].get('contentUrl', '')
                if image_url:
                    break

    # 3. page elements から最大のshapeBackgroundFill画像を探す
    if not image_url:
        for elem in new_slide.get('pageElements', []):
            if 'shape' in elem:
                props = elem['shape'].get('shapeProperties', {})
                fill = props.get('shapeBackgroundFill', {})
                if 'solidFill' not in fill:
                    # 画像背景の可能性
                    pass

    requests = []

    if image_url:
        # 元スライドの背景に新スライドの画像を設定
        requests.append({
            'updatePageProperties': {
                'objectId': target_id,
                'pageProperties': {
                    'pageBackgroundFill': {
                        'stretchedPictureFill': {
                            'contentUrl': image_url,
                        }
                    }
                },
                'fields': 'pageBackgroundFill'
            }
        })
        print(f"画像URL取得OK → 背景設定")
    else:
        # 画像URLが見つからない場合、新スライドのスクリーンショットをサムネイルとして使用
        # サムネイルAPIで新スライドの画像を取得
        try:
            thumb = slides_service.presentations().pages().getThumbnail(
                presentationId=pres_id,
                pageObjectId=new_id,
                thumbnailProperties_thumbnailSize='LARGE'
            ).execute()
            thumb_url = thumb.get('contentUrl', '')
            if thumb_url:
                requests.append({
                    'updatePageProperties': {
                        'objectId': target_id,
                        'pageProperties': {
                            'pageBackgroundFill': {
                                'stretchedPictureFill': {
                                    'contentUrl': thumb_url,
                                }
                            }
                        },
                        'fields': 'pageBackgroundFill'
                    }
                })
                print(f"サムネイルURL使用 → 背景設定")
            else:
                print(f"画像URLもサムネイルも取得できません")
        except Exception as e:
            print(f"サムネイル取得失敗: {e}")

    # 新スライドを削除
    requests.append({
        'deleteObject': {
            'objectId': new_id
        }
    })

    if requests:
        slides_service.presentations().batchUpdate(
            presentationId=pres_id, body={'requests': requests}
        ).execute()
        print(f"転送完了 (target={target_id}, deleted={new_id})")


if __name__ == '__main__':
    main()
