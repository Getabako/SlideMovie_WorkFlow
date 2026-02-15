#!/usr/bin/env python3
"""
スライド上のテキスト要素（シェイプ・テーブル）を削除する。
「スライド」モードで生成された背景にはテキストが含まれているため、
元のテキストボックスは不要。

Usage:
  python3 scripts/delete_text_elements.py <presentation_id> <slide_numbers>
  slide_numbers: カンマ区切りの1-basedスライド番号 (例: "1,2,3,10")
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
        print("Usage: python3 scripts/delete_text_elements.py <pres_id> <slide_numbers>")
        sys.exit(1)

    pres_id = sys.argv[1]
    slide_nums = [int(x.strip()) for x in sys.argv[2].split(',')]

    creds = get_credentials()
    service = build('slides', 'v1', credentials=creds)

    pres = service.presentations().get(presentationId=pres_id).execute()
    slides = pres.get('slides', [])

    delete_requests = []
    total_deleted = 0

    for slide_num in slide_nums:
        idx = slide_num - 1
        if idx < 0 or idx >= len(slides):
            print(f"  スライド{slide_num}: 範囲外（スキップ）")
            continue

        slide = slides[idx]
        deleted_count = 0

        for elem in slide.get('pageElements', []):
            # 画像要素はスキップ
            if 'image' in elem:
                continue

            should_delete = False

            # シェイプ要素（テキストボックス含む）
            if 'shape' in elem:
                shape = elem['shape']
                text_content = shape.get('text', {})
                for text_elem in text_content.get('textElements', []):
                    if 'textRun' in text_elem:
                        text = text_elem['textRun'].get('content', '').strip()
                        if text:
                            should_delete = True
                            break

            # テーブル要素
            elif 'table' in elem:
                should_delete = True

            # グループ要素
            elif 'elementGroup' in elem:
                should_delete = True

            if should_delete:
                delete_requests.append({
                    'deleteObject': {'objectId': elem['objectId']}
                })
                deleted_count += 1

        print(f"  スライド{slide_num}: テキスト要素 {deleted_count}件を削除予定")
        total_deleted += deleted_count

    if delete_requests:
        # バッチ更新（一括削除）
        service.presentations().batchUpdate(
            presentationId=pres_id,
            body={'requests': delete_requests}
        ).execute()
        print(f"完了: {total_deleted}個のテキスト要素を削除しました")
    else:
        print("削除対象のテキスト要素がありません")


if __name__ == '__main__':
    main()
