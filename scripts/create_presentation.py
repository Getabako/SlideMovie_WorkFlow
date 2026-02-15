#!/usr/bin/env python3
"""
YAMLからGoogle Slidesプレゼンテーションを新規作成し、テキストを入力する
"""

import os
import sys
import yaml
import pickle
import re
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

SCOPES = [
    'https://www.googleapis.com/auth/presentations',
    'https://www.googleapis.com/auth/drive',
]

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
        else:
            client_id = os.getenv('YOUTUBE_CLIENT_ID')
            client_secret = os.getenv('YOUTUBE_CLIENT_SECRET')
            if not client_id or not client_secret:
                print("エラー: .envにYOUTUBE_CLIENT_IDとYOUTUBE_CLIENT_SECRETを設定してください")
                sys.exit(1)
            client_config = {
                "installed": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"]
                }
            }
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, 'wb') as f:
            pickle.dump(creds, f)
    return creds


def strip_markdown(text):
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    return text.strip()


def main():
    if len(sys.argv) < 2:
        print("使い方: python create_presentation.py <yaml_file> [--folder-id FOLDER_ID]")
        sys.exit(1)

    yaml_path = sys.argv[1]
    folder_id = None
    if '--folder-id' in sys.argv:
        idx = sys.argv.index('--folder-id')
        folder_id = sys.argv[idx + 1]

    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    topic = data.get('topic', 'Untitled')
    slides_data = data.get('slides', [])
    print(f"📄 「{topic}」- {len(slides_data)}枚のスライドを作成します")

    creds = get_credentials()
    slides_service = build('slides', 'v1', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)

    # Create presentation
    presentation = slides_service.presentations().create(
        body={'title': topic}
    ).execute()
    presentation_id = presentation['presentationId']
    print(f"✅ プレゼンテーション作成: {presentation_id}")

    # Move to folder if specified
    if folder_id:
        try:
            file = drive_service.files().get(fileId=presentation_id, fields='parents').execute()
            old_parents = ','.join(file.get('parents', []))
            drive_service.files().update(
                fileId=presentation_id,
                addParents=folder_id,
                removeParents=old_parents,
                fields='id, parents'
            ).execute()
            print(f"📁 フォルダに移動しました: {folder_id}")
        except Exception as e:
            print(f"⚠️ フォルダ移動に失敗: {e}")

    # Get default slide to delete later
    pres = slides_service.presentations().get(presentationId=presentation_id).execute()
    default_slide_id = pres['slides'][0]['objectId']
    # Get page dimensions
    page_size = pres.get('pageSize', {})
    page_w = page_size.get('width', {}).get('magnitude', 9144000)
    page_h = page_size.get('height', {}).get('magnitude', 5143500)

    EMU = 914400  # 1 inch

    # Create blank slides
    requests = []
    for i in range(len(slides_data)):
        slide_id = f'slide_{i:03d}'
        requests.append({
            'createSlide': {
                'objectId': slide_id,
                'insertionIndex': i + 1,
                'slideLayoutReference': {'predefinedLayout': 'BLANK'},
            }
        })
    requests.append({'deleteObject': {'objectId': default_slide_id}})

    print("🔨 スライドを作成中...")
    slides_service.presentations().batchUpdate(
        presentationId=presentation_id,
        body={'requests': requests}
    ).execute()

    # Create text boxes and insert text
    text_requests = []
    for i, slide in enumerate(slides_data):
        slide_id = f'slide_{i:03d}'
        title_box_id = f'title_{i:03d}'
        body_box_id = f'body_{i:03d}'
        title = slide.get('title', '')
        content = strip_markdown(slide.get('content', ''))

        # Title text box - top area
        title_h = int(EMU * 1.2)
        text_requests.append({
            'createShape': {
                'objectId': title_box_id,
                'shapeType': 'TEXT_BOX',
                'elementProperties': {
                    'pageObjectId': slide_id,
                    'size': {
                        'width': {'magnitude': page_w - EMU, 'unit': 'EMU'},
                        'height': {'magnitude': title_h, 'unit': 'EMU'},
                    },
                    'transform': {
                        'scaleX': 1, 'scaleY': 1,
                        'translateX': int(EMU * 0.5),
                        'translateY': int(EMU * 0.3),
                        'unit': 'EMU'
                    }
                }
            }
        })

        # Body text box - below title
        body_top = int(EMU * 1.6)
        body_h = page_h - body_top - int(EMU * 0.3)
        text_requests.append({
            'createShape': {
                'objectId': body_box_id,
                'shapeType': 'TEXT_BOX',
                'elementProperties': {
                    'pageObjectId': slide_id,
                    'size': {
                        'width': {'magnitude': page_w - EMU, 'unit': 'EMU'},
                        'height': {'magnitude': body_h, 'unit': 'EMU'},
                    },
                    'transform': {
                        'scaleX': 1, 'scaleY': 1,
                        'translateX': int(EMU * 0.5),
                        'translateY': body_top,
                        'unit': 'EMU'
                    }
                }
            }
        })

        if title:
            text_requests.append({
                'insertText': {'objectId': title_box_id, 'text': title, 'insertionIndex': 0}
            })
            text_requests.append({
                'updateTextStyle': {
                    'objectId': title_box_id,
                    'style': {
                        'bold': True,
                        'fontSize': {'magnitude': 28 if i == 0 else 22, 'unit': 'PT'},
                        'foregroundColor': {'opaqueColor': {'rgbColor': {'red': 1, 'green': 1, 'blue': 1}}}
                    },
                    'textRange': {'type': 'ALL'},
                    'fields': 'bold,fontSize,foregroundColor'
                }
            })

        if content:
            text_requests.append({
                'insertText': {'objectId': body_box_id, 'text': content, 'insertionIndex': 0}
            })
            text_requests.append({
                'updateTextStyle': {
                    'objectId': body_box_id,
                    'style': {
                        'fontSize': {'magnitude': 12, 'unit': 'PT'},
                        'foregroundColor': {'opaqueColor': {'rgbColor': {'red': 1, 'green': 1, 'blue': 1}}}
                    },
                    'textRange': {'type': 'ALL'},
                    'fields': 'fontSize,foregroundColor'
                }
            })

    print("✏️ テキストを入力中...")
    chunk_size = 30
    for j in range(0, len(text_requests), chunk_size):
        chunk = text_requests[j:j+chunk_size]
        slides_service.presentations().batchUpdate(
            presentationId=presentation_id,
            body={'requests': chunk}
        ).execute()
        print(f"  ... {min(j+chunk_size, len(text_requests))}/{len(text_requests)} リクエスト完了")

    print(f"\n🎉 完了！")
    print(f"URL: https://docs.google.com/presentation/d/{presentation_id}/edit")
    print(f"ID: {presentation_id}")


if __name__ == '__main__':
    main()
