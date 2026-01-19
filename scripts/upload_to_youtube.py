#!/usr/bin/env python3
"""
YouTube動画アップロードスクリプト

プレゼンテーション動画をYouTubeにアップロードし、
視聴数・いいね・チャンネル登録を促進するメタデータを自動設定します。
"""

import os
import sys
import json
import pickle
import argparse
from pathlib import Path
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv()

# YouTube API スコープ
SCOPES = ['https://www.googleapis.com/auth/youtube.upload',
          'https://www.googleapis.com/auth/youtube']

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent


def get_credentials():
    """OAuth2認証情報を取得"""
    creds = None
    token_path = PROJECT_ROOT / 'youtube_token.pickle'

    # 保存済みトークンがあれば読み込み
    if token_path.exists():
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)

    # 有効な認証情報がなければ認証フローを実行
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            client_id = os.getenv('YOUTUBE_CLIENT_ID')
            client_secret = os.getenv('YOUTUBE_CLIENT_SECRET')

            if not client_id or not client_secret:
                print("エラー: .envファイルにYOUTUBE_CLIENT_IDとYOUTUBE_CLIENT_SECRETを設定してください")
                sys.exit(1)

            # クライアント設定を動的に作成
            client_config = {
                "installed": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["http://localhost:8080/"]
                }
            }

            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            creds = flow.run_local_server(port=8080)

        # トークンを保存
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    return creds


def generate_optimized_metadata(presentation_name: str, script_path: Path = None) -> dict:
    """
    視聴数・いいね・チャンネル登録を促進するメタデータを生成
    """
    # プレゼン名から基本情報を抽出
    clean_name = presentation_name.replace('_', ' ').strip()

    # スクリプトファイルから内容を読み込み
    content_summary = ""
    if script_path and script_path.exists():
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                script_data = json.load(f)
                slides = script_data.get('slides', [])
                if slides:
                    # 最初の数スライドからサマリーを作成
                    for slide in slides[:3]:
                        if slide.get('script'):
                            content_summary += slide['script'][:200] + " "
        except Exception as e:
            print(f"スクリプト読み込み警告: {e}")

    # AI・IT教育関連のキーワードを判定
    ai_keywords = ['AI', '人工知能', 'ChatGPT', 'Gemini', '機械学習', 'ディープラーニング']
    it_keywords = ['プログラミング', 'IT', 'ホームページ', 'バナー', 'スプレッドシート', 'リサーチ']
    education_keywords = ['講座', '入門', '初心者', '勉強', '学習', '教育']

    is_ai_content = any(kw in clean_name for kw in ai_keywords)
    is_it_content = any(kw in clean_name for kw in it_keywords)
    is_education = any(kw in clean_name for kw in education_keywords)

    # タイトル生成（視聴を促す形式）
    title_prefix = ""
    if is_ai_content:
        title_prefix = "【AI入門】"
    elif is_it_content:
        title_prefix = "【IT講座】"
    else:
        title_prefix = "【無料講座】"

    title = f"{title_prefix}{clean_name}｜IF塾"

    # 説明文生成
    description = f"""🎓 {clean_name}

この動画では、{clean_name}について分かりやすく解説しています。

━━━━━━━━━━━━━━━━━━━━━━
📚 この動画で学べること
━━━━━━━━━━━━━━━━━━━━━━
"""

    if is_ai_content:
        description += """✅ AIの基礎知識と活用方法
✅ 実践的なAIツールの使い方
✅ 仕事や学習での具体的な活用例
"""
    elif is_it_content:
        description += """✅ ITスキルの基礎から応用まで
✅ 実践的なツールの使い方
✅ 効率的な作業のコツ
"""
    else:
        description += """✅ 基礎から応用まで丁寧に解説
✅ 実践的な活用方法
✅ すぐに使えるテクニック
"""

    description += f"""
━━━━━━━━━━━━━━━━━━━━━━
🏫 IF塾について
━━━━━━━━━━━━━━━━━━━━━━
IF塾は、AI・ITスキルを楽しく学べる教育チャンネルです。
初心者の方でも分かりやすい解説を心がけています。

👍 動画が役立ったら「いいね」をお願いします！
🔔 チャンネル登録で最新動画をチェック！
💬 質問・リクエストはコメント欄へどうぞ！

━━━━━━━━━━━━━━━━━━━━━━
🔗 関連リンク
━━━━━━━━━━━━━━━━━━━━━━
📺 チャンネル: https://www.youtube.com/@if-juku

#IF塾 #AI講座 #IT教育 #無料講座 #初心者向け
"""

    # タグ生成（検索されやすいキーワード）
    tags = ['IF塾', '講座', '教育', '初心者向け', '無料', '解説', 'わかりやすい']

    if is_ai_content:
        tags.extend(['AI', '人工知能', 'AI入門', 'AI活用', 'ChatGPT', 'Gemini',
                     'AI講座', 'AI初心者', 'AI使い方', '生成AI', 'AIツール'])
    if is_it_content:
        tags.extend(['IT', 'IT講座', 'IT入門', 'パソコン', 'PC', 'スキルアップ',
                     'デジタルスキル', 'ITスキル', '仕事効率化'])
    if is_education:
        tags.extend(['勉強法', '学習', '教育', 'オンライン学習', '独学'])

    # プレゼン名に含まれるキーワードも追加
    for word in clean_name.split():
        if len(word) >= 2 and word not in tags:
            tags.append(word)

    # タグは最大500文字まで
    tags = tags[:30]

    return {
        'title': title[:100],  # YouTubeの制限
        'description': description[:5000],  # YouTubeの制限
        'tags': tags,
        'category_id': '27',  # 27 = Education
        'privacy_status': 'public',  # public, private, unlisted
        'made_for_kids': False,
        'default_language': 'ja',
        'default_audio_language': 'ja'
    }


def upload_video(video_path: str, metadata: dict) -> str:
    """
    動画をYouTubeにアップロード

    Returns:
        アップロードした動画のURL
    """
    creds = get_credentials()
    youtube = build('youtube', 'v3', credentials=creds)

    body = {
        'snippet': {
            'title': metadata['title'],
            'description': metadata['description'],
            'tags': metadata['tags'],
            'categoryId': metadata['category_id'],
            'defaultLanguage': metadata.get('default_language', 'ja'),
            'defaultAudioLanguage': metadata.get('default_audio_language', 'ja')
        },
        'status': {
            'privacyStatus': metadata['privacy_status'],
            'madeForKids': metadata['made_for_kids'],
            'selfDeclaredMadeForKids': metadata['made_for_kids']
        }
    }

    # 動画ファイルをアップロード
    media = MediaFileUpload(
        video_path,
        mimetype='video/mp4',
        resumable=True,
        chunksize=1024*1024  # 1MB chunks
    )

    print(f"📤 アップロード開始: {metadata['title']}")
    print(f"   ファイル: {video_path}")

    request = youtube.videos().insert(
        part='snippet,status',
        body=body,
        media_body=media
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"   進捗: {int(status.progress() * 100)}%")

    video_id = response['id']
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    print(f"✅ アップロード完了!")
    print(f"   動画URL: {video_url}")

    return video_url


def upload_presentation_video(presentation_name: str, privacy: str = 'public') -> str:
    """
    プレゼンテーション動画をYouTubeにアップロード

    Args:
        presentation_name: プレゼンテーション名（フォルダ名）
        privacy: 公開設定 (public/private/unlisted)

    Returns:
        アップロードした動画のURL
    """
    presentations_dir = PROJECT_ROOT / 'presentations'
    presentation_path = presentations_dir / presentation_name

    if not presentation_path.exists():
        print(f"エラー: プレゼンテーションが見つかりません: {presentation_path}")
        sys.exit(1)

    # 動画ファイルを探す
    video_path = presentation_path / 'video_output' / 'output.mp4'
    if not video_path.exists():
        print(f"エラー: 動画ファイルが見つかりません: {video_path}")
        sys.exit(1)

    # スクリプトファイル
    script_path = presentation_path / 'video_output' / 'script.json'

    # メタデータ生成
    metadata = generate_optimized_metadata(presentation_name, script_path)
    metadata['privacy_status'] = privacy

    print("\n📋 アップロード設定:")
    print(f"   タイトル: {metadata['title']}")
    print(f"   公開設定: {metadata['privacy_status']}")
    print(f"   タグ: {', '.join(metadata['tags'][:10])}...")
    print()

    try:
        video_url = upload_video(str(video_path), metadata)

        # アップロード結果を保存
        result = {
            'uploaded_at': datetime.now().isoformat(),
            'video_url': video_url,
            'title': metadata['title'],
            'privacy': metadata['privacy_status']
        }

        result_path = presentation_path / 'video_output' / 'youtube_upload.json'
        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"\n📁 アップロード情報を保存: {result_path}")

        return video_url

    except HttpError as e:
        print(f"❌ YouTubeアップロードエラー: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='プレゼンテーション動画をYouTubeにアップロード'
    )
    parser.add_argument(
        'presentation_name',
        help='プレゼンテーション名（フォルダ名）'
    )
    parser.add_argument(
        '--privacy',
        choices=['public', 'private', 'unlisted'],
        default='public',
        help='公開設定 (デフォルト: public)'
    )
    parser.add_argument(
        '--auth-only',
        action='store_true',
        help='認証のみ実行（動画アップロードなし）'
    )

    args = parser.parse_args()

    if args.auth_only:
        print("🔐 YouTube認証を実行...")
        get_credentials()
        print("✅ 認証完了!")
        return

    video_url = upload_presentation_video(args.presentation_name, args.privacy)
    print(f"\n🎉 完了! 動画URL: {video_url}")


if __name__ == '__main__':
    main()
