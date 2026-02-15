#!/usr/bin/env python3
"""
Google Driveアップロードスクリプト
指定フォルダ内にサブフォルダを作成し、ファイルをアップロードする
"""

import os
import sys
import pickle
import argparse
import re
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from dotenv import load_dotenv

load_dotenv()

SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive',
]

PROJECT_ROOT = Path(__file__).parent.parent


def get_credentials():
    """OAuth2認証情報を取得"""
    creds = None
    token_path = PROJECT_ROOT / 'drive_token.pickle'

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
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["http://localhost"]
                }
            }

            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    return creds


def extract_folder_id(url_or_id):
    """URLまたはIDからフォルダIDを抽出"""
    match = re.search(r'folders/([a-zA-Z0-9_-]+)', url_or_id)
    if match:
        return match.group(1)
    return url_or_id


def create_folder(service, name, parent_id):
    """Google Drive上にフォルダを作成"""
    # 既存フォルダチェック
    query = f"name='{name}' and '{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    existing = results.get('files', [])
    if existing:
        print(f"既存フォルダを使用: {name} ({existing[0]['id']})")
        return existing[0]['id']

    metadata = {
        'name': name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id]
    }
    folder = service.files().create(body=metadata, fields='id').execute()
    print(f"フォルダ作成: {name} ({folder['id']})")
    return folder['id']


def upload_file(service, file_path, parent_id):
    """ファイルをアップロード"""
    file_path = Path(file_path)
    mime_types = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
        '.md': 'text/markdown',
        '.yml': 'text/yaml',
        '.yaml': 'text/yaml',
        '.json': 'application/json',
        '.pdf': 'application/pdf',
        '.html': 'text/html',
        '.mp4': 'video/mp4',
        '.mp3': 'audio/mpeg',
        '.wav': 'audio/wav',
    }
    mime_type = mime_types.get(file_path.suffix.lower(), 'application/octet-stream')

    metadata = {
        'name': file_path.name,
        'parents': [parent_id]
    }
    media = MediaFileUpload(str(file_path), mimetype=mime_type, resumable=True)
    file = service.files().create(body=metadata, media_body=media, fields='id,name').execute()
    print(f"  アップロード: {file_path.name} ({file['id']})")
    return file['id']


def upload_directory(service, local_dir, parent_id, recursive=True):
    """ディレクトリ内のファイルをアップロード"""
    local_dir = Path(local_dir)
    count = 0
    for item in sorted(local_dir.iterdir()):
        if item.name.startswith('.'):
            continue
        if item.is_dir() and recursive:
            sub_folder_id = create_folder(service, item.name, parent_id)
            count += upload_directory(service, item, sub_folder_id, recursive)
        elif item.is_file():
            upload_file(service, item, parent_id)
            count += 1
    return count


def main():
    parser = argparse.ArgumentParser(description='Google Driveにファイルをアップロード')
    parser.add_argument('local_path', help='アップロードするローカルフォルダまたはファイル')
    parser.add_argument('--parent', required=True, help='Google DriveのフォルダURL or ID')
    parser.add_argument('--folder-name', help='作成するフォルダ名（省略時はローカルフォルダ名）')
    parser.add_argument('--no-subfolder', action='store_true', help='サブフォルダを作らず直接アップロード')
    parser.add_argument('--auth-only', action='store_true', help='認証のみ実行')
    args = parser.parse_args()

    creds = get_credentials()
    service = build('drive', 'v3', credentials=creds)

    if args.auth_only:
        print("認証成功")
        return

    parent_id = extract_folder_id(args.parent)
    local_path = Path(args.local_path)

    if not local_path.exists():
        print(f"エラー: {local_path} が見つかりません")
        sys.exit(1)

    if local_path.is_dir():
        folder_name = args.folder_name or local_path.name
        if not args.no_subfolder:
            target_id = create_folder(service, folder_name, parent_id)
        else:
            target_id = parent_id
        count = upload_directory(service, local_path, target_id)
        print(f"\n完了: {count}ファイルをアップロード")
        print(f"フォルダURL: https://drive.google.com/drive/folders/{target_id}")
    else:
        upload_file(service, local_path, parent_id)
        print("完了")


if __name__ == '__main__':
    main()
