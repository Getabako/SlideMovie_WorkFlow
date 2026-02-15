#!/usr/bin/env python3
"""
プレゼンテーションを完全クリーンアップ:
- 余分なスライド（25枚目以降）を削除
- 全スライドの背景画像を削除（白背景に戻す）
- 全スライドの画像オブジェクトを削除
"""

import sys
import pickle
from pathlib import Path
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

PROJECT_ROOT = Path(__file__).parent.parent
PRES_ID = '1_hNmyanUhPnvLhrb-qzAFjcB8ZYttIGHf9bWL5Ity6A'
TARGET_SLIDES = 24


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
    creds = get_credentials()
    slides_service = build('slides', 'v1', credentials=creds)

    # プレゼン取得
    pres = slides_service.presentations().get(presentationId=PRES_ID).execute()
    slides = pres.get('slides', [])
    print(f"現在のスライド数: {len(slides)}")

    requests = []

    # 余分なスライドを削除（25枚目以降、後ろから削除）
    if len(slides) > TARGET_SLIDES:
        for i in range(len(slides) - 1, TARGET_SLIDES - 1, -1):
            slide_id = slides[i]['objectId']
            requests.append({'deleteObject': {'objectId': slide_id}})
            print(f"  削除: スライド{i+1} ({slide_id})")

    # 各スライドの背景を白に戻し、画像オブジェクトを削除
    for i, slide in enumerate(slides[:TARGET_SLIDES]):
        slide_id = slide['objectId']

        # 背景画像があれば白ソリッドに変更
        bg = slide.get('pageProperties', {}).get('pageBackgroundFill', {})
        if 'stretchedPictureFill' in bg:
            requests.append({
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
            print(f"  スライド{i+1}: 背景画像→白に変更")

        # 画像オブジェクトを削除
        for elem in slide.get('pageElements', []):
            if 'image' in elem:
                elem_id = elem['objectId']
                requests.append({'deleteObject': {'objectId': elem_id}})
                print(f"  スライド{i+1}: 画像オブジェクト削除 ({elem_id})")

    if requests:
        print(f"\n{len(requests)}件のリクエストを実行中...")
        slides_service.presentations().batchUpdate(
            presentationId=PRES_ID, body={'requests': requests}
        ).execute()
        print("クリーンアップ完了!")
    else:
        print("変更不要（既にクリーン）")

    # 確認
    pres = slides_service.presentations().get(presentationId=PRES_ID).execute()
    slides = pres.get('slides', [])
    print(f"\n=== クリーンアップ後の状態 ===")
    print(f"スライド数: {len(slides)}")
    for i, slide in enumerate(slides):
        bg = slide.get('pageProperties', {}).get('pageBackgroundFill', {})
        elems = slide.get('pageElements', [])
        img_count = sum(1 for e in elems if 'image' in e)
        bg_type = 'picture' if 'stretchedPictureFill' in bg else 'solid' if 'solidFill' in bg else 'none'
        print(f"  スライド{i+1}: bg={bg_type}, elements={len(elems)}, images={img_count}")


if __name__ == '__main__':
    main()
