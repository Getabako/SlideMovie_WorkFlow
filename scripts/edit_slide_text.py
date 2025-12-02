#!/usr/bin/env python3
"""
特定のスライドのテキストを編集するスクリプト
"""

import yaml
import sys
import os
from pathlib import Path

def edit_slide_text(yaml_path: str, slide_number: int, new_title: str = None, new_content: str = None):
    """
    指定したスライドのテキストを編集する

    Args:
        yaml_path: YAMLファイルのパス
        slide_number: 編集するスライド番号（1から始まる）
        new_title: 新しいタイトル（Noneの場合は変更しない）
        new_content: 新しい本文（Noneの場合は変更しない）
    """

    # YAMLファイルを読み込む
    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    # スライド番号の検証
    if slide_number < 1 or slide_number > len(data['slides']):
        raise ValueError(f"スライド番号は1から{len(data['slides'])}の範囲で指定してください")

    # スライドのインデックス（0から始まる）
    slide_index = slide_number - 1

    # テキストを編集
    if new_title is not None:
        data['slides'][slide_index]['title'] = new_title
        print(f"✓ スライド{slide_number}のタイトルを更新しました")

    if new_content is not None:
        data['slides'][slide_index]['content'] = new_content
        print(f"✓ スライド{slide_number}の本文を更新しました")

    # YAMLファイルに書き込む
    with open(yaml_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    print(f"\n✓ {yaml_path} を更新しました")

    # 変更内容を表示
    print(f"\n【更新後のスライド{slide_number}】")
    print(f"タイトル: {data['slides'][slide_index]['title']}")
    print(f"本文:\n{data['slides'][slide_index]['content']}")

def main():
    if len(sys.argv) < 3:
        print("使用方法:")
        print("  python edit_slide_text.py <presentation_name> <slide_number> [options]")
        print("\nオプション:")
        print("  --title \"新しいタイトル\"")
        print("  --content \"新しい本文\"")
        print("\n例:")
        print("  python edit_slide_text.py '最新のAI業界の動向2025' 13 --title '実習1：テンプレートから作成（15分）'")
        print("  python edit_slide_text.py '最新のAI業界の動向2025' 13 --content '課題\\n\\nInstagram投稿用のバナーを作る\\n\\n手順\\n\\n1. 「デザインを作成」をクリック\\n2. 「Instagram 投稿」を選択'")
        sys.exit(1)

    presentation_name = sys.argv[1]
    slide_number = int(sys.argv[2])

    # YAMLファイルのパスを構築
    yaml_path = f"presentations/{presentation_name}/input.yml"

    if not os.path.exists(yaml_path):
        print(f"エラー: {yaml_path} が見つかりません")
        sys.exit(1)

    # オプションを解析
    new_title = None
    new_content = None

    i = 3
    while i < len(sys.argv):
        if sys.argv[i] == '--title' and i + 1 < len(sys.argv):
            new_title = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '--content' and i + 1 < len(sys.argv):
            new_content = sys.argv[i + 1]
            i += 2
        else:
            i += 1

    if new_title is None and new_content is None:
        print("エラー: --title または --content を指定してください")
        sys.exit(1)

    # スライドテキストを編集
    edit_slide_text(yaml_path, slide_number, new_title, new_content)

if __name__ == "__main__":
    main()
