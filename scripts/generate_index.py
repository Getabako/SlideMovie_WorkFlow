#!/usr/bin/env python3
"""
GitHub Pages用のインデックスファイル生成スクリプト
プレゼンテーション一覧をJSONとして出力します
"""

import os
import json
from pathlib import Path


def generate_presentations_index():
    """
    presentations/ ディレクトリをスキャンして、
    プレゼンテーション一覧のJSONを生成
    """
    presentations_dir = Path("presentations")
    presentations = []

    if not presentations_dir.exists():
        print("presentations/ ディレクトリが見つかりません")
        return presentations

    # 各プレゼンテーションディレクトリをスキャン
    for pres_dir in sorted(presentations_dir.iterdir()):
        if not pres_dir.is_dir():
            continue

        topic_name = pres_dir.name

        # HTMLファイルを探す
        html_files = list(pres_dir.glob("*.html"))
        if not html_files:
            print(f"警告: {topic_name} にHTMLファイルが見つかりません")
            continue

        html_file = html_files[0]

        # PDFファイルを探す
        pdf_files = list(pres_dir.glob("*.pdf"))
        pdf_file = pdf_files[0] if pdf_files else None

        # 動画ファイルを探す（videos/ ディレクトリ）
        video_path = Path(f"videos/{topic_name}/video.mp4")
        video_file = video_path if video_path.exists() else None

        presentation = {
            "title": topic_name,
            "html": str(html_file).replace("\\", "/"),
            "pdf": str(pdf_file).replace("\\", "/") if pdf_file else None,
            "video": str(video_file).replace("\\", "/") if video_file else None
        }

        presentations.append(presentation)
        print(f"✓ プレゼンテーションを追加: {topic_name}")

    return presentations


def main():
    print("プレゼンテーション一覧を生成中...")
    presentations = generate_presentations_index()

    # JSONファイルに書き出し
    output_file = Path("presentations.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(presentations, f, ensure_ascii=False, indent=2)

    print(f"\n✓ {len(presentations)}件のプレゼンテーションを {output_file} に出力しました")

    # 内容を表示
    if presentations:
        print("\nプレゼンテーション一覧:")
        for pres in presentations:
            print(f"  - {pres['title']}")
            print(f"    HTML: {pres['html']}")
            if pres['pdf']:
                print(f"    PDF: {pres['pdf']}")
            if pres['video']:
                print(f"    Video: {pres['video']}")


if __name__ == "__main__":
    main()
