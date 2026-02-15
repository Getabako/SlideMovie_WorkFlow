#!/usr/bin/env python3
"""
Google Slidesの各スライドに背景画像を設定するスクリプト
画像をDriveにアップロードし、Slides APIで背景に設定
"""

import os
import sys
import pickle
import glob
from pathlib import Path

from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent


def get_credentials():
    token_path = PROJECT_ROOT / 'drive_token.pickle'
    with open(token_path, 'rb') as f:
        creds = pickle.load(f)
    if creds.expired:
        creds.refresh(Request())
        with open(token_path, 'wb') as f:
            pickle.dump(creds, f)
    return creds


def main():
    if len(sys.argv) < 3:
        print("使い方: python set_backgrounds.py <presentation_id> <images_dir>")
        sys.exit(1)

    presentation_id = sys.argv[1]
    images_dir = Path(sys.argv[2])

    creds = get_credentials()
    slides_service = build('slides', 'v1', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)

    # Get presentation slides
    pres = slides_service.presentations().get(presentationId=presentation_id).execute()
    slides = pres.get('slides', [])
    print(f"プレゼンテーション: {pres.get('title')}")
    print(f"スライド数: {len(slides)}")

    # Get image files sorted
    image_files = sorted(glob.glob(str(images_dir / '*.png')))
    print(f"画像ファイル数: {len(image_files)}")

    if len(image_files) < len(slides):
        print(f"⚠️ 画像数({len(image_files)})がスライド数({len(slides)})より少ない")

    # Create a temp folder in Drive for images
    folder_meta = {
        'name': f'_bg_images_{presentation_id[:8]}',
        'mimeType': 'application/vnd.google-apps.folder'
    }
    folder = drive_service.files().create(body=folder_meta, fields='id').execute()
    folder_id = folder['id']
    print(f"一時フォルダ作成: {folder_id}")

    # Process each slide
    for i, slide in enumerate(slides):
        if i >= len(image_files):
            print(f"  スライド{i+1}: 画像なし、スキップ")
            continue

        slide_id = slide['objectId']
        image_path = image_files[i]
        print(f"  スライド{i+1}: {Path(image_path).name} をアップロード中...")

        # Upload image to Drive
        file_meta = {
            'name': Path(image_path).name,
            'parents': [folder_id]
        }
        media = MediaFileUpload(image_path, mimetype='image/png')
        uploaded = drive_service.files().create(
            body=file_meta, media_body=media, fields='id,webContentLink'
        ).execute()
        file_id = uploaded['id']

        # Make the file publicly accessible
        drive_service.permissions().create(
            fileId=file_id,
            body={'type': 'anyone', 'role': 'reader'}
        ).execute()

        # Get the direct URL
        image_url = f"https://drive.google.com/uc?id={file_id}&export=download"

        # Set as slide background
        requests = [{
            'updatePageProperties': {
                'objectId': slide_id,
                'pageProperties': {
                    'pageBackgroundFill': {
                        'stretchedPictureFill': {
                            'contentUrl': image_url
                        }
                    }
                },
                'fields': 'pageBackgroundFill'
            }
        }]

        try:
            slides_service.presentations().batchUpdate(
                presentationId=presentation_id,
                body={'requests': requests}
            ).execute()
            print(f"    ✅ 背景設定完了")
        except Exception as e:
            print(f"    ❌ エラー: {e}")

    print(f"\n🎉 完了！")
    print(f"URL: https://docs.google.com/presentation/d/{presentation_id}/edit")

    # Clean up temp folder
    # drive_service.files().delete(fileId=folder_id).execute()


if __name__ == '__main__':
    main()
