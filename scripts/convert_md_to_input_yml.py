#!/usr/bin/env python3
"""
Markdownファイルから input.yml を生成するスクリプト
Marp形式のスライドを解析してYAML形式に変換する
"""

import yaml
import sys
import os
import re


def parse_marp_slides(md_content: str) -> list:
    """
    Marp形式のMarkdownを解析してスライドリストを返す

    Args:
        md_content: Markdownファイルの内容

    Returns:
        スライドのリスト [{title: str, content: str}, ...]
    """
    # スライドを --- で分割
    slides_raw = md_content.split('\n---\n')

    slides = []

    for slide_raw in slides_raw:
        slide_raw = slide_raw.strip()
        if not slide_raw:
            continue

        # 最初のスライド（YAMLフロントマター）はスキップ
        if slide_raw.startswith('---') and 'marp:' in slide_raw:
            continue

        # 画像参照を削除
        slide_text = re.sub(r'!\[bg [^\]]+\]\([^\)]+\)\n?', '', slide_raw)

        # タイトルを抽出（# または ## で始まる行）
        title_match = re.search(r'^#{1,2}\s+(.+)$', slide_text, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else ""

        # 本文を抽出（タイトル以外の部分）
        if title_match:
            # タイトル行を削除
            content = slide_text[:title_match.start()] + slide_text[title_match.end():]
        else:
            content = slide_text

        # 空行を削除して整形
        content = content.strip()

        # タイトルまたは本文がある場合のみスライドとして追加
        if title or content:
            slides.append({
                'title': title,
                'content': content
            })

    return slides


def extract_topic_from_filename(filepath: str) -> str:
    """
    ファイルパスからトピック名を抽出

    Args:
        filepath: Markdownファイルのパス

    Returns:
        トピック名
    """
    basename = os.path.basename(filepath)
    # 拡張子を除去
    topic = os.path.splitext(basename)[0]
    # _slide_with_images などのサフィックスを除去
    topic = re.sub(r'_slide(_with_images)?$', '', topic)
    return topic


def convert_md_to_yml(md_path: str, output_path: str = None):
    """
    MarkdownファイルをYAML形式に変換

    Args:
        md_path: 入力Markdownファイルのパス
        output_path: 出力YAMLファイルのパス（省略時は input.yml）
    """
    if not os.path.exists(md_path):
        print(f"エラー: {md_path} が見つかりません")
        sys.exit(1)

    # Markdownファイルを読み込む
    with open(md_path, 'r', encoding='utf-8') as f:
        md_content = f.read()

    # スライドを解析
    slides = parse_marp_slides(md_content)

    if not slides:
        print("エラー: スライドを解析できませんでした")
        sys.exit(1)

    # トピック名を抽出
    topic = extract_topic_from_filename(md_path)

    # YAML形式のデータを作成
    yaml_data = {
        'topic': topic,
        'slides': slides
    }

    # 出力先を決定
    if output_path is None:
        # 入力ファイルと同じディレクトリに input.yml を作成
        output_path = os.path.join(os.path.dirname(md_path), 'input.yml')

    # YAMLファイルに書き込む
    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(yaml_data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    print(f"✓ {len(slides)}枚のスライドを変換しました")
    print(f"✓ 出力先: {output_path}")
    print(f"✓ トピック名: {topic}")


def main():
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python convert_md_to_input_yml.py <markdown_path> [output_path]")
        print("\n例:")
        print("  python convert_md_to_input_yml.py presentations/③バナー作り/③バナー作り.md")
        print("  python convert_md_to_input_yml.py slides/test_slide.md output/test.yml")
        sys.exit(1)

    md_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    convert_md_to_yml(md_path, output_path)


if __name__ == "__main__":
    main()
