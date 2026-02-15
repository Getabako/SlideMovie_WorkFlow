#!/usr/bin/env python3
"""
api_prompts.jsonから全スライド画像を一括生成し、
Google Slidesの背景に設定、テキスト要素を削除する。

Usage:
  python scripts/batch_generate_slides.py <presentation_id> <api_prompts.json>
"""

import sys
import os
import json
import pickle
import time
import tempfile
from pathlib import Path
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / '.env')


def get_google_credentials():
    token_path = PROJECT_ROOT / 'drive_token.pickle'
    with open(token_path, 'rb') as f:
        creds = pickle.load(f)
    if creds.expired:
        creds.refresh(Request())
        with open(token_path, 'wb') as f:
            pickle.dump(creds, f)
    return creds


def generate_image(prompt, max_retries=3):
    """Gemini APIで画像を生成"""
    api_key = os.environ.get('GOOGLE_AI_API_KEY')
    if not api_key:
        raise Exception("GOOGLE_AI_API_KEY not set")

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemini-3-pro-image-preview',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=['TEXT', 'IMAGE'],
                ),
            )
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.mime_type.startswith('image/'):
                    return part.inline_data.data, part.inline_data.mime_type
            print(f"    ⚠ 画像が生成されませんでした (attempt {attempt+1})")
        except Exception as e:
            print(f"    ⚠ エラー (attempt {attempt+1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(5)
    return None, None


def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/batch_generate_slides.py <presentation_id> <api_prompts.json>")
        sys.exit(1)

    presentation_id = sys.argv[1]
    prompts_path = Path(sys.argv[2])

    with open(prompts_path, 'r', encoding='utf-8') as f:
        prompts = json.load(f)

    creds = get_google_credentials()
    slides_service = build('slides', 'v1', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)

    # Get slides
    pres = slides_service.presentations().get(presentationId=presentation_id).execute()
    slides = pres.get('slides', [])
    print(f"プレゼン: {pres.get('title')}")
    print(f"スライド数: {len(slides)}, プロンプト数: {len(prompts)}")

    # Create temp folder in Drive
    folder_meta = {
        'name': f'_bg_{presentation_id[:8]}',
        'mimeType': 'application/vnd.google-apps.folder'
    }
    folder = drive_service.files().create(body=folder_meta, fields='id').execute()
    folder_id = folder['id']

    success = 0
    errors = 0

    for slide_num_str, prompt in prompts.items():
        slide_idx = int(slide_num_str) - 1
        if slide_idx >= len(slides):
            print(f"  スライド{slide_num_str}: インデックス超過、スキップ")
            continue

        slide = slides[slide_idx]
        slide_id = slide['objectId']

        print(f"\n[{slide_num_str}/{len(prompts)}] スライド{slide_num_str}")
        print(f"  画像生成中...")

        image_data, mime_type = generate_image(prompt)
        if not image_data:
            print(f"  ❌ 画像生成失敗")
            errors += 1
            continue

        # Save to temp file and upload to Drive
        ext = 'png' if 'png' in mime_type else 'jpg'
        with tempfile.NamedTemporaryFile(suffix=f'.{ext}', delete=False) as tmp:
            tmp.write(image_data)
            tmp_path = tmp.name

        file_meta = {'name': f'slide_{slide_num_str}.{ext}', 'parents': [folder_id]}
        media = MediaFileUpload(tmp_path, mimetype=mime_type)
        uploaded = drive_service.files().create(
            body=file_meta, media_body=media, fields='id'
        ).execute()
        file_id = uploaded['id']
        os.unlink(tmp_path)

        # Make public
        drive_service.permissions().create(
            fileId=file_id,
            body={'type': 'anyone', 'role': 'reader'}
        ).execute()

        image_url = f"https://drive.google.com/uc?id={file_id}&export=download"

        # Set background
        try:
            slides_service.presentations().batchUpdate(
                presentationId=presentation_id,
                body={'requests': [{
                    'updatePageProperties': {
                        'objectId': slide_id,
                        'pageProperties': {
                            'pageBackgroundFill': {
                                'stretchedPictureFill': {'contentUrl': image_url}
                            }
                        },
                        'fields': 'pageBackgroundFill'
                    }
                }]}
            ).execute()
            print(f"  ✅ 背景設定完了")
        except Exception as e:
            print(f"  ❌ 背景設定エラー: {e}")
            errors += 1
            continue

        # Delete text elements on this slide
        text_element_ids = []
        for elem in slide.get('pageElements', []):
            if 'shape' in elem and 'text' in elem.get('shape', {}):
                text_element_ids.append(elem['objectId'])

        if text_element_ids:
            delete_requests = [{'deleteObject': {'objectId': eid}} for eid in text_element_ids]
            try:
                slides_service.presentations().batchUpdate(
                    presentationId=presentation_id,
                    body={'requests': delete_requests}
                ).execute()
                print(f"  🗑️ テキスト要素{len(text_element_ids)}個削除")
            except Exception as e:
                print(f"  ⚠ テキスト削除エラー: {e}")

        success += 1
        time.sleep(2)  # Rate limit

    print(f"\n{'='*40}")
    print(f"完了: 成功{success} / エラー{errors} / 合計{len(prompts)}")
    print(f"URL: https://docs.google.com/presentation/d/{presentation_id}/edit")


if __name__ == '__main__':
    main()
