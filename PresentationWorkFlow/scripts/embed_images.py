#!/usr/bin/env python3
"""
画像埋め込みスクリプト
スライドファイルに生成された画像を埋め込みます
画像は右端揃え、縦幅フルで配置されます
"""

import sys
import os
import re
from pathlib import Path


def parse_slides(slide_file):
    """
    Marpスライドファイルを解析してヘッダーとページに分割

    Args:
        slide_file: スライドファイルのパス

    Returns:
        (header, slides) のタプル
    """
    with open(slide_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # ヘッダー部分を抽出
    parts = content.split('---\n')

    # 最初の2つはヘッダー
    header = '---\n' + parts[1] + '---\n'

    # 残りはスライド
    slides = []
    for i in range(2, len(parts)):
        if parts[i].strip():
            slides.append(parts[i].strip())

    return header, slides


def embed_images_in_slides(slide_file, image_dir, topic_name, output_file, use_server_url=False):
    """
    スライドに画像を埋め込む

    Args:
        slide_file: 元のスライドファイルのパス
        image_dir: 画像ディレクトリ
        topic_name: トピック名
        output_file: 出力ファイルのパス
        use_server_url: サーバーURLを使用するかどうか
    """
    # スライドを解析
    header, slides = parse_slides(slide_file)

    # 画像を埋め込んだスライドを作成
    content = []

    # ヘッダーを追加（グローバルスタイルを含む）
    content.append(header.rstrip())
    content.append("")

    # グローバルスタイル定義を追加（日本語フォント設定のみ）
    content.append("<style>")
    content.append("@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&display=swap');")
    content.append("")
    content.append("section {")
    content.append("  font-family: 'Noto Sans JP', 'Hiragino Sans', 'Hiragino Kaku Gothic ProN', 'Meiryo', sans-serif;")
    content.append("}")
    content.append("h1, h2, h3, h4, h5, h6 {")
    content.append("  font-family: 'Noto Sans JP', 'Hiragino Sans', 'Hiragino Kaku Gothic ProN', 'Meiryo', sans-serif;")
    content.append("}")
    content.append("</style>")
    content.append("")

    # 各スライドに画像を埋め込む
    image_path = Path(image_dir)

    for i, slide in enumerate(slides, start=1):
        # ページ区切り
        if i > 1:
            content.append("---")
            content.append("")

        # 画像URLを決定
        if use_server_url:
            # サーバーURLを使用（000.png ~ 999.png形式）
            image_url = f"https://images.if-juku.net/{topic_name}/{i-1:03d}.png"
            # サーバー上の画像は常に存在するものとして扱う
            image_exists = True
        else:
            # ローカルファイルの相対パスを使用
            image_filename = f"{topic_name}_page{i:02d}.png"
            image_file = image_path / image_filename
            image_exists = image_file.exists()

            if image_exists:
                # スライドファイルからの相対パスを計算
                # slides/ から images/ へは ../images/... となる
                slide_dir = Path(slide_file).parent
                try:
                    relative_path = image_file.relative_to(slide_dir.parent)
                    image_url = str(Path('..') / relative_path).replace('\\', '/')
                except ValueError:
                    # 相対パスが計算できない場合は絶対パスを使用
                    image_url = str(image_file.absolute()).replace('\\', '/')

        # 画像を配置
        if image_exists:
            # Marpのbg directiveを使用して画像を右側に配置
            # bg right:40% を使用して右側40%を画像に割り当て
            content.append(f"![bg right:40%]({image_url})")
            content.append("")
            content.append(slide)
        else:
            # 画像がない場合は元のスライドをそのまま追加
            content.append(slide)

        content.append("")

    # ファイルに書き込む
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(content))

    print(f"画像を埋め込んだスライドを作成しました: {output_file}")


def main():
    if len(sys.argv) < 4:
        print("使用方法: python embed_images.py <slide_file> <image_dir> <topic_name> [--use-server-url]")
        sys.exit(1)

    slide_file = sys.argv[1]
    image_dir = sys.argv[2]
    topic_name = sys.argv[3]

    # サーバーURLを使用するかどうかを判定
    use_server_url = '--use-server-url' in sys.argv

    if not os.path.exists(slide_file):
        print(f"エラー: スライドファイルが見つかりません: {slide_file}")
        sys.exit(1)

    if not use_server_url and not os.path.exists(image_dir):
        print(f"エラー: 画像ディレクトリが見つかりません: {image_dir}")
        sys.exit(1)

    # 出力ファイル名を生成
    slide_path = Path(slide_file)
    output_file = slide_path.parent / f"{topic_name}_slide_with_images.md"

    # 画像を埋め込む
    embed_images_in_slides(slide_file, image_dir, topic_name, output_file, use_server_url)

    if use_server_url:
        print(f"サーバーURL（https://images.if-juku.net/{topic_name}/）を使用して画像を埋め込みました")

    # 次のステップのために環境変数に保存
    if 'GITHUB_ENV' in os.environ:
        with open(os.environ['GITHUB_ENV'], 'a') as f:
            f.write(f"FINAL_SLIDE_FILE={output_file}\n")


if __name__ == "__main__":
    main()
