#!/usr/bin/env python3
"""
Google Slides APIで画像を各スライドの背景に設定するスクリプト

使い方:
  python scripts/set_slide_backgrounds.py <presentation_id> <images_dir> [--from N] [--to N]

例:
  python scripts/set_slide_backgrounds.py 1_hNmyanUhPnvLhrb-qzAFjcB8ZYttIGHf9bWL5Ity6A presentations/鳥取大学式ペアレントトレーニング/images/
"""

import os
import sys
import pickle
import time
import argparse
from pathlib import Path

from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from dotenv import load_dotenv

load_dotenv()
PROJECT_ROOT = Path(__file__).parent.parent


def get_credentials():
    """OAuth2認証情報を取得"""
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


def upload_image_to_drive(drive_service, file_path):
    """画像をGoogle Driveにアップロードし、公開リンクを返す"""
    metadata = {
        'name': file_path.name,
    }
    media = MediaFileUpload(str(file_path), mimetype='image/png', resumable=True)
    file = drive_service.files().create(
        body=metadata, media_body=media, fields='id'
    ).execute()
    file_id = file['id']

    # 公開アクセス設定（anyone with link can view）
    drive_service.permissions().create(
        fileId=file_id,
        body={'type': 'anyone', 'role': 'reader'}
    ).execute()

    return file_id


def set_background(slides_service, pres_id, slide_id, image_url, slide=None):
    """スライドの背景画像を設定し、テキスト要素を削除する"""
    requests = []

    # 既存のテキスト要素・シェイプを削除（画像が完成版なので不要）
    if slide:
        for elem in slide.get('pageElements', []):
            # 画像要素はスキップ（背景以外の画像があれば残す場合もあるが、基本削除）
            if 'shape' in elem or 'table' in elem or 'elementGroup' in elem:
                requests.append({
                    'deleteObject': {'objectId': elem['objectId']}
                })

    # 背景に設定
    requests.append({
        'updatePageProperties': {
            'objectId': slide_id,
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

    slides_service.presentations().batchUpdate(
        presentationId=pres_id, body={'requests': requests}
    ).execute()


def main():
    parser = argparse.ArgumentParser(description='スライド背景画像を設定')
    parser.add_argument('presentation_id', help='Google SlidesのプレゼンテーションID')
    parser.add_argument('images_dir', help='画像ディレクトリ')
    parser.add_argument('--from', dest='from_slide', type=int, default=1, help='開始スライド番号')
    parser.add_argument('--to', dest='to_slide', type=int, default=-1, help='終了スライド番号')

    args = parser.parse_args()

    creds = get_credentials()
    drive_service = build('drive', 'v3', credentials=creds)
    slides_service = build('slides', 'v1', credentials=creds)

    # プレゼンテーションのスライド一覧を取得
    pres = slides_service.presentations().get(presentationId=args.presentation_id).execute()
    slides = pres.get('slides', [])
    print(f"プレゼン: {pres.get('title', '無題')}")
    print(f"スライド数: {len(slides)}")

    # 画像ファイルを取得（ソート済み）
    images_dir = Path(args.images_dir)
    image_files = sorted(images_dir.glob('*.png'))
    print(f"画像数: {len(image_files)}")

    from_idx = args.from_slide - 1
    to_idx = args.to_slide if args.to_slide > 0 else len(slides)

    print(f"処理範囲: スライド{from_idx + 1}〜{to_idx}")
    print()

    success = 0
    errors = 0

    for i in range(from_idx, min(to_idx, len(slides))):
        slide = slides[i]
        slide_id = slide['objectId']

        # 対応する画像ファイル
        img_num = i + 1  # 1-indexed
        img_name = f'{img_num:03d}.png'
        img_path = images_dir / img_name

        if not img_path.exists():
            print(f"[{img_num}/{to_idx}] スライド{img_num}: 画像なし ({img_name})")
            continue

        try:
            print(f"[{img_num}/{to_idx}] スライド{img_num}: アップロード中...", end='', flush=True)

            # 画像をDriveにアップロード
            file_id = upload_image_to_drive(drive_service, img_path)
            image_url = f'https://drive.google.com/uc?id={file_id}&export=download'

            print(f" 背景設定中...", end='', flush=True)

            # 背景に設定 + テキスト要素削除
            set_background(slides_service, args.presentation_id, slide_id, image_url, slide=slide)

            print(f" ✓ 完了")
            success += 1

            # レート制限回避
            time.sleep(1)

        except Exception as e:
            print(f" ✗ エラー: {e}")
            errors += 1
            time.sleep(2)

    print(f"\n=== 結果 ===")
    print(f"成功: {success} / エラー: {errors} / 合計: {success + errors}")
    print(f"URL: https://docs.google.com/presentation/d/{args.presentation_id}/edit")


if __name__ == '__main__':
    main()
