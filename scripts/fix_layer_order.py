#!/usr/bin/env python3
"""
指定スライドの画像オブジェクトを最背面に移動するスクリプト

使い方:
  python scripts/fix_layer_order.py <presentation_id> <slide_numbers...>

例:
  python scripts/fix_layer_order.py 1_hNmyanUhPnvLhrb-qzAFjcB8ZYttIGHf9bWL5Ity6A 3 4 5 6 13 17
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
        print("Usage: python scripts/fix_layer_order.py <presentation_id> <slide_numbers...>")
        sys.exit(1)

    pres_id = sys.argv[1]
    slide_nums = [int(x) for x in sys.argv[2:]]

    creds = get_credentials()
    slides_service = build('slides', 'v1', credentials=creds)

    pres = slides_service.presentations().get(presentationId=pres_id).execute()
    slides = pres.get('slides', [])
    print(f"プレゼン: {pres.get('title', '無題')}")
    print(f"スライド数: {len(slides)}")
    print(f"修正対象: スライド {slide_nums}")

    requests = []

    for num in slide_nums:
        idx = num - 1
        if idx < 0 or idx >= len(slides):
            print(f"  スライド{num}: 範囲外")
            continue

        slide = slides[idx]
        slide_id = slide['objectId']
        elements = slide.get('pageElements', [])

        # 画像要素を探す（imageなど）
        image_elements = []
        for elem in elements:
            if 'image' in elem:
                image_elements.append(elem)
            elif 'shape' in elem and elem['shape'].get('shapeType') == 'RECTANGLE':
                # 画像が図形として挿入されている場合もチェック
                if 'shapeBackgroundFill' in elem['shape'].get('shapeProperties', {}):
                    image_elements.append(elem)

        if not image_elements:
            print(f"  スライド{num}: 画像要素なし")
            continue

        # 最初の画像要素を最背面に移動
        for img_elem in image_elements:
            obj_id = img_elem['objectId']
            requests.append({
                'updatePageElementTransform': {
                    'objectId': obj_id,
                    'applyMode': 'RELATIVE',
                    'transform': {
                        'scaleX': 1, 'scaleY': 1,
                        'translateX': 0, 'translateY': 0,
                        'unit': 'EMU'
                    }
                }
            })
            print(f"  スライド{num}: 画像 {obj_id} を最背面へ")

    if not requests:
        print("修正不要")
        return

    # batchUpdate で一括更新
    # Note: Slides APIには直接的な「最背面へ」命令がないため、
    # 画像を削除→テキスト要素の前に再挿入する方法を代わりに使う
    # 実際にはページ要素の順序変更はupdatePageElementsOrder API がないため、
    # 別のアプローチが必要

    # 代替案: 各スライドの背景画像として設定する
    bg_requests = []
    for num in slide_nums:
        idx = num - 1
        slide = slides[idx]
        slide_id = slide['objectId']
        elements = slide.get('pageElements', [])

        for elem in elements:
            if 'image' in elem:
                content_url = elem['image'].get('contentUrl', '')
                if content_url:
                    # 画像URLを背景に設定
                    bg_requests.append({
                        'updatePageProperties': {
                            'objectId': slide_id,
                            'pageProperties': {
                                'pageBackgroundFill': {
                                    'stretchedPictureFill': {
                                        'contentUrl': content_url,
                                    }
                                }
                            },
                            'fields': 'pageBackgroundFill'
                        }
                    })
                    # 前面の画像オブジェクトを削除
                    bg_requests.append({
                        'deleteObject': {
                            'objectId': elem['objectId']
                        }
                    })
                    print(f"  スライド{num}: 背景設定 + 前面画像削除")
                    break

    if bg_requests:
        slides_service.presentations().batchUpdate(
            presentationId=pres_id, body={'requests': bg_requests}
        ).execute()
        print(f"\n完了: {len(bg_requests) // 2}枚のスライドの画像を背景に設定しました")
    else:
        print("背景設定に使える画像URLが見つかりません")


if __name__ == '__main__':
    main()
