#!/usr/bin/env python3
"""
Gemini APIでスライド画像を生成し、Google Slidesの背景に設定する。
テキスト要素も削除する。

Usage:
  python3 scripts/gemini_slide_generator.py <presentation_id> <slide_index_0based> "<prompt>"
"""

import sys
import os
import pickle
import tempfile
from pathlib import Path
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / '.env')


def get_google_credentials():
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


def generate_image(prompt):
    """Gemini APIで画像を生成する。画像データとMIMEタイプを返す。"""
    api_key = os.environ.get('GOOGLE_AI_API_KEY')
    if not api_key:
        raise Exception("GOOGLE_AI_API_KEY が .env に設定されていません")

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model='gemini-3-pro-image-preview',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=['IMAGE'],
        )
    )

    for part in response.candidates[0].content.parts:
        if part.inline_data:
            mime = part.inline_data.mime_type or 'image/jpeg'
            return part.inline_data.data, mime

    raise Exception("画像が生成されませんでした")


def upload_to_drive(creds, image_data, filename, mime_type='image/jpeg'):
    """Google Driveに画像をアップロードして公開URLを返す"""
    drive_service = build('drive', 'v3', credentials=creds)

    ext = '.jpg' if 'jpeg' in mime_type else '.png'
    tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
    tmp.write(image_data)
    tmp.close()

    try:
        file_metadata = {'name': filename, 'mimeType': mime_type}
        media = MediaFileUpload(tmp.name, mimetype=mime_type)
        file_result = drive_service.files().create(
            body=file_metadata, media_body=media, fields='id'
        ).execute()

        file_id = file_result['id']

        # 公開設定
        drive_service.permissions().create(
            fileId=file_id,
            body={'role': 'reader', 'type': 'anyone'}
        ).execute()

        content_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        return file_id, content_url
    finally:
        os.unlink(tmp.name)


def set_background_and_cleanup(creds, pres_id, slide_index, image_url):
    """スライドの背景に画像を設定し、テキスト要素を削除する"""
    slides_service = build('slides', 'v1', credentials=creds)
    pres = slides_service.presentations().get(presentationId=pres_id).execute()
    slides = pres.get('slides', [])

    if slide_index >= len(slides):
        raise Exception(f"スライドインデックス {slide_index} が範囲外 (total={len(slides)})")

    slide = slides[slide_index]
    slide_id = slide['objectId']

    requests = []

    # 背景に設定
    requests.append({
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
    })

    # テキスト要素を削除
    for elem in slide.get('pageElements', []):
        if 'image' in elem:
            continue
        if 'shape' in elem or 'table' in elem or 'elementGroup' in elem:
            requests.append({
                'deleteObject': {'objectId': elem['objectId']}
            })

    slides_service.presentations().batchUpdate(
        presentationId=pres_id, body={'requests': requests}
    ).execute()


def main():
    if len(sys.argv) < 4:
        print("Usage: python3 scripts/gemini_slide_generator.py <pres_id> <slide_index> \"<prompt>\"")
        sys.exit(1)

    pres_id = sys.argv[1]
    slide_index = int(sys.argv[2])
    prompt = sys.argv[3]

    slide_num = slide_index + 1
    print(f"スライド{slide_num}: Gemini API画像生成中...")

    # 1. 画像生成
    image_data, mime_type = generate_image(prompt)
    ext = '.jpg' if 'jpeg' in mime_type else '.png'
    print(f"  画像生成完了 ({len(image_data)} bytes, {mime_type})")

    # 2. ローカル保存
    local_dir = PROJECT_ROOT / 'screenshots'
    local_dir.mkdir(exist_ok=True)
    local_path = local_dir / f'slide_{slide_num}_api{ext}'
    local_path.write_bytes(image_data)
    print(f"  ローカル保存: {local_path.name}")

    # 3. Drive アップロード
    creds = get_google_credentials()
    file_id, image_url = upload_to_drive(creds, image_data, f'slide_{slide_num}{ext}', mime_type)
    print(f"  Driveアップロード完了: {file_id}")

    # 4. 背景設定 + テキスト削除
    set_background_and_cleanup(creds, pres_id, slide_index, image_url)
    print(f"  背景設定・テキスト削除完了")

    print(f"スライド{slide_num}: 完了")


if __name__ == '__main__':
    main()
