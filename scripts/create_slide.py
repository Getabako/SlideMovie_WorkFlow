#!/usr/bin/env python3
"""
スライド作成スクリプト
入力ファイルからMarp形式のMarkdownスライドを生成します
docs/slide_generation_rules.mdに定義された規則に従います
"""

import sys
import os
import yaml
import re
from pathlib import Path


def should_apply_line_breaks(text, is_title=False):
    """
    改行を適用すべきか判断する

    Args:
        text: 処理対象のテキスト
        is_title: タイトルかどうか

    Returns:
        bool: 改行を適用すべきか
    """
    # タイトルは改行しない
    if is_title:
        return False

    # リスト項目やコードブロックは元の形式を保持
    if text.strip().startswith(('- ', '* ', '+ ', '```', '#', '|')):
        return False

    # 30文字以下の短いテキストは改行しない
    if len(text) <= 30:
        return False

    return True


def process_long_text(text, max_lines=15):
    """
    長いテキストを処理する（行数制限のみチェック）

    Args:
        text: 処理対象のテキスト
        max_lines: 最大行数

    Returns:
        処理後のテキストリスト（分割が必要な場合は複数）
    """
    lines = text.split('\n')

    # 行数が制限以内なら、そのまま返す
    if len(lines) <= max_lines - 2:  # タイトル分の余裕を持たせる
        return [text]

    # 行数オーバーの場合のみ分割
    result = []
    current_chunk = []
    current_line_count = 0

    for line in lines:
        if current_line_count + 1 > max_lines - 2:
            # 現在のチャンクを保存して新しいチャンクを開始
            result.append('\n'.join(current_chunk))
            current_chunk = [line]
            current_line_count = 1
        else:
            current_chunk.append(line)
            current_line_count += 1

    # 残りのチャンクを追加
    if current_chunk:
        result.append('\n'.join(current_chunk))

    return result if result else [text]


def create_marp_slide(input_file, output_dir):
    """
    入力ファイルからMarpスライドを作成
    docs/slide_generation_rules.mdの規則に従います

    改行ポリシー：
    - タイトルは改行しない
    - 本文の改行は最小限に
    - 行数制限（15行）を超える場合のみスライド分割

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
    slide_count = 0
    for i, slide in enumerate(slides):
        title = slide.get('title', '')
        slide_content = slide.get('content', '')

        # タイトルは改行しない
        # コンテンツは基本的にそのまま使用（行数チェックのみ）
        content_chunks = process_long_text(slide_content)

        for chunk_index, chunk in enumerate(content_chunks):
            if slide_count > 0:
                content.append("---")
                content.append("")

            # タイトル（改行なし）
            if title:
                if chunk_index > 0:
                    # 分割されたスライドの場合
                    content.append(f"# {title} (続き)")
                else:
                    content.append(f"# {title}")
                content.append("")

            # コンテンツ
            if chunk:
                content.append(chunk)
                content.append("")

            slide_count += 1

    # ファイルに書き込む
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(content))

    print(f"スライドを作成しました: {output_file}")
    print(f"改行ポリシー: タイトル改行なし、本文は必要最小限")
    return str(output_file)


def main():
    if len(sys.argv) < 2:
        print("使用方法: python create_slide.py <input_yaml_file>")
        print("規則ファイル: docs/slide_generation_rules.md")
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