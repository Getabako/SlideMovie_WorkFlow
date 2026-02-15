#!/usr/bin/env python3
"""
Googleスライド管理スクリプト
Discordからスライドの参照・編集を行うためのツール
"""

import os
import sys
import json
import pickle
import argparse
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

SCOPES = [
    'https://www.googleapis.com/auth/presentations',
    'https://www.googleapis.com/auth/drive.readonly',
]

PROJECT_ROOT = Path(__file__).parent.parent


def get_credentials():
    """OAuth2認証情報を取得"""
    creds = None
    token_path = PROJECT_ROOT / 'slides_token.pickle'

    if token_path.exists():
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)

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
                    "redirect_uris": ["http://localhost", "urn:ietf:wg:oauth:2.0:oob"],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            }

            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    return creds


def extract_presentation_id(url_or_id):
    """URLまたはIDからプレゼンテーションIDを抽出"""
    if '/' in url_or_id:
        parts = url_or_id.split('/')
        for i, part in enumerate(parts):
            if part == 'd' and i + 1 < len(parts):
                return parts[i + 1]
    return url_or_id


def list_slides(presentation_id):
    """スライド一覧を表示"""
    creds = get_credentials()
    service = build('slides', 'v1', credentials=creds)
    
    presentation = service.presentations().get(presentationId=presentation_id).execute()
    slides = presentation.get('slides', [])
    
    print(f"プレゼン: {presentation.get('title', '無題')}")
    print(f"スライド数: {len(slides)}")
    print("---")
    
    for i, slide in enumerate(slides, 1):
        texts = []
        for element in slide.get('pageElements', []):
            shape = element.get('shape', {})
            text_content = shape.get('text', {})
            for text_element in text_content.get('textElements', []):
                text_run = text_element.get('textRun', {})
                content = text_run.get('content', '').strip()
                if content:
                    texts.append(content)
        
        title = texts[0] if texts else '(テキストなし)'
        body = ' / '.join(texts[1:3]) if len(texts) > 1 else ''
        
        print(f"{i}. {title}")
        if body:
            print(f"   {body[:80]}")
    
    return slides


def get_slide_detail(presentation_id, slide_number):
    """特定スライドの詳細を表示"""
    creds = get_credentials()
    service = build('slides', 'v1', credentials=creds)
    
    presentation = service.presentations().get(presentationId=presentation_id).execute()
    slides = presentation.get('slides', [])
    
    if slide_number < 1 or slide_number > len(slides):
        print(f"エラー: スライド番号は1〜{len(slides)}の範囲で指定してください")
        return
    
    slide = slides[slide_number - 1]
    print(f"スライド {slide_number}/{len(slides)}")
    print(f"ID: {slide['objectId']}")
    print("---")
    
    for element in slide.get('pageElements', []):
        obj_id = element.get('objectId', '')
        shape = element.get('shape', {})
        text_content = shape.get('text', {})
        
        full_text = ''
        for text_element in text_content.get('textElements', []):
            text_run = text_element.get('textRun', {})
            content = text_run.get('content', '')
            if content:
                full_text += content
        
        if full_text.strip():
            placeholder = shape.get('placeholder', {})
            ptype = placeholder.get('type', 'BODY')
            print(f"[{ptype}] objectId={obj_id}")
            print(f"  {full_text.strip()}")
            print()


def replace_text(presentation_id, old_text, new_text, slide_number=None):
    """テキストを置換"""
    creds = get_credentials()
    service = build('slides', 'v1', credentials=creds)
    
    requests = []
    
    if slide_number:
        presentation = service.presentations().get(presentationId=presentation_id).execute()
        slides = presentation.get('slides', [])
        if slide_number < 1 or slide_number > len(slides):
            print(f"エラー: スライド番号は1〜{len(slides)}の範囲で指定してください")
            return
        page_object_id = slides[slide_number - 1]['objectId']
        
        requests.append({
            'replaceAllText': {
                'containsText': {'text': old_text, 'matchCase': True},
                'replaceText': new_text,
                'pageObjectIds': [page_object_id],
            }
        })
    else:
        requests.append({
            'replaceAllText': {
                'containsText': {'text': old_text, 'matchCase': True},
                'replaceText': new_text,
            }
        })
    
    result = service.presentations().batchUpdate(
        presentationId=presentation_id, body={'requests': requests}
    ).execute()
    
    replies = result.get('replies', [])
    count = replies[0].get('replaceAllText', {}).get('occurrencesChanged', 0) if replies else 0
    print(f"置換完了: {count}箇所を変更しました")


def insert_text(presentation_id, object_id, text, insertion_index=0):
    """テキストを挿入"""
    creds = get_credentials()
    service = build('slides', 'v1', credentials=creds)
    
    requests = [{
        'insertText': {
            'objectId': object_id,
            'insertionIndex': insertion_index,
            'text': text,
        }
    }]
    
    service.presentations().batchUpdate(
        presentationId=presentation_id, body={'requests': requests}
    ).execute()
    print(f"挿入完了: '{text[:30]}...'")


def delete_text(presentation_id, object_id, start_index, end_index):
    """テキストを削除"""
    creds = get_credentials()
    service = build('slides', 'v1', credentials=creds)
    
    requests = [{
        'deleteText': {
            'objectId': object_id,
            'textRange': {
                'type': 'FIXED_RANGE',
                'startIndex': start_index,
                'endIndex': end_index,
            }
        }
    }]
    
    service.presentations().batchUpdate(
        presentationId=presentation_id, body={'requests': requests}
    ).execute()
    print(f"削除完了")


def main():
    parser = argparse.ArgumentParser(description='Googleスライド管理')
    subparsers = parser.add_subparsers(dest='command')
    
    # list
    list_parser = subparsers.add_parser('list', help='スライド一覧表示')
    list_parser.add_argument('url', help='GoogleスライドのURLまたはID')
    
    # detail
    detail_parser = subparsers.add_parser('detail', help='スライド詳細表示')
    detail_parser.add_argument('url', help='GoogleスライドのURLまたはID')
    detail_parser.add_argument('slide_number', type=int, help='スライド番号')
    
    # replace
    replace_parser = subparsers.add_parser('replace', help='テキスト置換')
    replace_parser.add_argument('url', help='GoogleスライドのURLまたはID')
    replace_parser.add_argument('old_text', help='置換元テキスト')
    replace_parser.add_argument('new_text', help='置換先テキスト')
    replace_parser.add_argument('--slide', type=int, help='対象スライド番号')
    
    args = parser.parse_args()
    
    if args.command == 'list':
        pid = extract_presentation_id(args.url)
        list_slides(pid)
    elif args.command == 'detail':
        pid = extract_presentation_id(args.url)
        get_slide_detail(pid, args.slide_number)
    elif args.command == 'replace':
        pid = extract_presentation_id(args.url)
        replace_text(pid, args.old_text, args.new_text, args.slide)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
