#!/usr/bin/env python3
"""
画像アップロードスクリプト
生成された画像をimages.if-juku.netにアップロードします
"""

import sys
import os
import requests
from pathlib import Path


def upload_images(image_dir, topic_name, password):
    """
    画像をサーバーにアップロード

    Args:
        image_dir: 画像ディレクトリ
        topic_name: トピック名（フォルダ名として使用）
        password: アップロード用パスワード

    Returns:
        アップロード成功した画像のURL一覧
    """
    upload_url = "https://images.if-juku.net/upload.php"
    image_path = Path(image_dir)

    if not image_path.exists():
        print(f"エラー: 画像ディレクトリが見つかりません: {image_dir}")
        return []

    # 画像ファイルを取得してソート
    image_files = sorted(image_path.glob(f"{topic_name}_page*.png"))

    if not image_files:
        print(f"エラー: 画像ファイルが見つかりません: {image_dir}/{topic_name}_page*.png")
        return []

    print(f"\n{len(image_files)}枚の画像をアップロードします...")

    uploaded_urls = []

    for i, image_file in enumerate(image_files):
        # ファイル名を000.png ~ 999.pngの形式に変換
        new_filename = f"{i:03d}.png"
        relative_path = f"{topic_name}/{new_filename}"

        print(f"\n画像 {i+1}/{len(image_files)} をアップロード中...")
        print(f"  元のファイル: {image_file.name}")
        print(f"  保存先: {relative_path}")

        try:
            # ファイルを読み込む
            with open(image_file, 'rb') as f:
                files = {
                    'file': (new_filename, f, 'image/png')
                }
                data = {
                    'password': password,
                    'path': relative_path
                }

                # アップロード
                response = requests.post(upload_url, files=files, data=data, timeout=30)

                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        url = result.get('url', '')
                        print(f"  ✓ アップロード成功: {url}")
                        uploaded_urls.append(url)
                    else:
                        error_msg = result.get('error', '不明なエラー')
                        print(f"  ✗ アップロード失敗: {error_msg}")
                else:
                    print(f"  ✗ アップロード失敗: HTTPステータス {response.status_code}")

        except Exception as e:
            print(f"  ✗ エラー: {e}")

    print(f"\n\nアップロード完了: {len(uploaded_urls)}/{len(image_files)} 件成功")
    return uploaded_urls


def main():
    if len(sys.argv) < 4:
        print("使用方法: python upload_images.py <image_dir> <topic_name> <password>")
        sys.exit(1)

    image_dir = sys.argv[1]
    topic_name = sys.argv[2]
    password = sys.argv[3]

    # 画像をアップロード
    uploaded_urls = upload_images(image_dir, topic_name, password)

    if not uploaded_urls:
        print("\nエラー: 画像のアップロードに失敗しました")
        sys.exit(1)

    # 次のステップのために環境変数に保存
    if 'GITHUB_ENV' in os.environ:
        with open(os.environ['GITHUB_ENV'], 'a') as f:
            f.write(f"UPLOADED_IMAGES={','.join(uploaded_urls)}\n")
            # ベースURLも保存
            f.write(f"IMAGE_BASE_URL=https://images.if-juku.net/{topic_name}\n")

    print("\n✓ すべての画像のアップロードが完了しました")


if __name__ == "__main__":
    main()
