#!/usr/bin/env python3
"""
YAMLからGoogle Slidesにテキストを一括入力するスクリプト
既存の空プレゼンテーションにスライドを追加し、テキストを配置する
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
]

PROJECT_ROOT = Path(__file__).parent.parent
EMU = 914400  # 1 inch = 914400 EMU


def get_credentials():
    creds = None
    token_path = PROJECT_ROOT / 'slides_token.pickle'
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
    """Remove markdown formatting for plain text insertion"""
    # Remove ## headers -> keep text
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # Remove bold **text**
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    # Remove emoji shortcodes but keep emoji
    # Remove bullet dashes at start
    # Keep as-is for readability
    return text.strip()


def create_slide_requests(slides_data):
    """Generate API requests to create slides with text"""
    requests = []
    slide_ids = []

    for i, slide in enumerate(slides_data):
        slide_id = f'slide_{i:03d}'
        title_id = f'title_{i:03d}'
        body_id = f'body_{i:03d}'
        slide_ids.append(slide_id)

        # Choose layout based on slide position
        if i == 0:
            # Title slide
            layout = 'TITLE'
        else:
            layout = 'TITLE_AND_BODY'

        # Create slide
        requests.append({
            'createSlide': {
                'objectId': slide_id,
                'insertionIndex': i,
                'slideLayoutReference': {
                    'predefinedLayout': layout
                },
                'placeholderIdMappings': [
                    {
                        'layoutPlaceholder': {'type': 'TITLE'},
                        'objectId': title_id
                    },
                    {
                        'layoutPlaceholder': {'type': 'SUBTITLE' if i == 0 else 'BODY'},
                        'objectId': body_id
                    }
                ]
            }
        })

    return requests, slide_ids


def create_text_requests(slides_data):
    """Generate text insertion requests"""
    requests = []

    for i, slide in enumerate(slides_data):
        title_id = f'title_{i:03d}'
        body_id = f'body_{i:03d}'

        title = slide.get('title', '')
        content = strip_markdown(slide.get('content', ''))

        # Insert title
        if title:
            requests.append({
                'insertText': {
                    'objectId': title_id,
                    'text': title,
                    'insertionIndex': 0
                }
            })
            # Style title
            requests.append({
                'updateTextStyle': {
                    'objectId': title_id,
                    'style': {
                        'bold': True,
                        'fontSize': {'magnitude': 28 if i == 0 else 24, 'unit': 'PT'},
                        'foregroundColor': {
                            'opaqueColor': {
                                'rgbColor': {'red': 1, 'green': 1, 'blue': 1}
                            }
                        }
                    },
                    'textRange': {'type': 'ALL'},
                    'fields': 'bold,fontSize,foregroundColor'
                }
            })

        # Insert body content
        if content:
            requests.append({
                'insertText': {
                    'objectId': body_id,
                    'text': content,
                    'insertionIndex': 0
                }
            })
            # Style body - white text for dark backgrounds
            requests.append({
                'updateTextStyle': {
                    'objectId': body_id,
                    'style': {
                        'fontSize': {'magnitude': 14, 'unit': 'PT'},
                        'foregroundColor': {
                            'opaqueColor': {
                                'rgbColor': {'red': 1, 'green': 1, 'blue': 1}
                            }
                        }
                    },
                    'textRange': {'type': 'ALL'},
                    'fields': 'fontSize,foregroundColor'
                }
            })

    return requests


def main():
    if len(sys.argv) < 3:
        print("使い方: python populate_slides.py <presentation_id> <yaml_file>")
        sys.exit(1)

    presentation_id = sys.argv[1]
    yaml_path = sys.argv[2]

    # Load YAML
    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    slides_data = data.get('slides', [])
    print(f"📄 {len(slides_data)}枚のスライドを作成します")

    # Auth
    creds = get_credentials()
    service = build('slides', 'v1', credentials=creds)

    # First, delete the default blank slide if it exists
    presentation = service.presentations().get(presentationId=presentation_id).execute()
    existing_slides = presentation.get('slides', [])

    # Create all slides first
    slide_requests, slide_ids = create_slide_requests(slides_data)
    if slide_requests:
        print(f"🔨 スライドを作成中...")
        service.presentations().batchUpdate(
            presentationId=presentation_id,
            body={'requests': slide_requests}
        ).execute()
        print(f"✅ {len(slide_requests)}枚のスライドを作成しました")

    # Delete old blank slides
    if existing_slides:
        delete_requests = [
            {'deleteObject': {'objectId': s['objectId']}}
            for s in existing_slides
        ]
        service.presentations().batchUpdate(
            presentationId=presentation_id,
            body={'requests': delete_requests}
        ).execute()
        print(f"🗑️ 既存の空白スライド{len(existing_slides)}枚を削除しました")

    # Insert text
    text_requests = create_text_requests(slides_data)
    if text_requests:
        print(f"✏️ テキストを入力中...")
        # Batch in chunks of 50 to avoid API limits
        chunk_size = 50
        for j in range(0, len(text_requests), chunk_size):
            chunk = text_requests[j:j+chunk_size]
            service.presentations().batchUpdate(
                presentationId=presentation_id,
                body={'requests': chunk}
            ).execute()
        print(f"✅ テキスト入力完了")

    print(f"\n🎉 完了！ プレゼンテーションURL:")
    print(f"https://docs.google.com/presentation/d/{presentation_id}/edit")


if __name__ == '__main__':
    main()
