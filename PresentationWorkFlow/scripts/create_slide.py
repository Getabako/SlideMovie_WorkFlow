#!/usr/bin/env python3
"""
スライド作成スクリプト
入力ファイルからMarp形式のMarkdownスライドを生成します
"""

import sys
import os
import yaml
from pathlib import Path


def create_marp_slide(input_file, output_dir):
    """
    入力ファイルからMarpスライドを作成

    Args:
        input_file: 入力YAMLファイルのパス
        output_dir: 出力ディレクトリ

    Returns:
        生成されたスライドファイルのパス
    """
    # 入力ファイルを読み込む
    with open(input_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    topic = data.get('topic', 'presentation')
    slides = data.get('slides', [])

    # ファイル名を生成（トピック名からスペースやスラッシュを除去）
    safe_topic = topic.replace(' ', '_').replace('/', '_').replace('\\', '_')
    output_file = Path(output_dir) / f"{safe_topic}_slide.md"

    # Marpスライドの内容を生成
    content = []

    # Marp設定ヘッダー
    content.append("---")
    content.append("marp: true")
    content.append("theme: default")
    content.append("paginate: true")
    content.append("size: 16:9")
    content.append("---")
    content.append("")

    # 各スライドを生成
    for i, slide in enumerate(slides):
        if i > 0:
            content.append("---")
            content.append("")

        title = slide.get('title', '')
        slide_content = slide.get('content', '')

        # タイトル
        if title:
            content.append(f"# {title}")
            content.append("")

        # コンテンツ
        if slide_content:
            content.append(slide_content)
            content.append("")

    # ファイルに書き込む
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(content))

    print(f"スライドを作成しました: {output_file}")
    return str(output_file)


def main():
    if len(sys.argv) < 2:
        print("使用方法: python create_slide.py <input_yaml_file>")
        sys.exit(1)

    input_file = sys.argv[1]

    if not os.path.exists(input_file):
        print(f"エラー: 入力ファイルが見つかりません: {input_file}")
        sys.exit(1)

    # 出力ディレクトリ
    script_dir = Path(__file__).parent
    output_dir = script_dir.parent / "slides"
    output_dir.mkdir(exist_ok=True)

    # スライドを作成
    slide_file = create_marp_slide(input_file, output_dir)

    # 次のステップのために環境変数に保存
    if 'GITHUB_ENV' in os.environ:
        with open(os.environ['GITHUB_ENV'], 'a') as f:
            f.write(f"SLIDE_FILE={slide_file}\n")
            # トピック名も保存
            with open(input_file, 'r', encoding='utf-8') as input_f:
                data = yaml.safe_load(input_f)
                topic = data.get('topic', 'presentation')
                safe_topic = topic.replace(' ', '_').replace('/', '_').replace('\\', '_')
                f.write(f"TOPIC_NAME={safe_topic}\n")


if __name__ == "__main__":
    main()
