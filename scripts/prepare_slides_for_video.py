#!/usr/bin/env python3
"""
プレゼンテーションのスライド画像を動画用に準備するスクリプト
"""

import sys
import os
import json
from pathlib import Path
import shutil

def prepare_slides(presentation_dir, output_dir):
    """
    プレゼンテーションディレクトリからスライド画像を準備

    Args:
        presentation_dir: プレゼンテーションディレクトリ
        output_dir: 出力ディレクトリ
    """
    presentation_path = Path(presentation_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # スライド画像を検索（複数のパターンを試す）
    print(f"スライド画像を検索中: {presentation_path}")
    print(f"ディレクトリの内容:")
    for item in presentation_path.iterdir():
        print(f"  - {item.name}")

    # パターン1: slide.*.png (Marpの標準出力: slide.001.png, slide.002.png, ...)
    slide_images = sorted(presentation_path.glob("slide.*.png"))

    # パターン2: slide-*.png (旧パターン)
    if not slide_images:
        print("slide.*.png が見つかりません。slide-*.png を検索します...")
        slide_images = sorted(presentation_path.glob("slide-*.png"))

    # パターン3: *.png (全てのPNG画像)
    if not slide_images:
        print("slide-*.png も見つかりません。全てのPNG画像を検索します...")
        slide_images = sorted(presentation_path.glob("*.png"))

    if not slide_images:
        # デバッグ情報を表示
        all_files = list(presentation_path.iterdir())
        print(f"\nディレクトリ内のファイル一覧 ({len(all_files)} 個):")
        for f in all_files:
            print(f"  - {f.name}")
        raise FileNotFoundError(f"スライド画像が見つかりません: {presentation_dir}")

    print(f"スライド画像数: {len(slide_images)}")

    # スライド情報を収集
    slides_info = []
    for i, slide_img in enumerate(slide_images, 1):
        # 出力ディレクトリにコピー
        output_file = output_path / f"slide_{i:02d}.png"
        shutil.copy(slide_img, output_file)
        print(f"コピー: {slide_img} -> {output_file}")

        slides_info.append({
            'index': i,
            'filename': f"slide_{i:02d}.png",
            'original': str(slide_img)
        })

    # メタデータを保存
    metadata = {
        'total_slides': len(slide_images),
        'slides': slides_info
    }

    metadata_file = output_path / 'slides_metadata.json'
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"\nメタデータ保存: {metadata_file}")
    return str(metadata_file)

def main():
    if len(sys.argv) < 2:
        print("使用方法: python prepare_slides_for_video.py <presentation_directory>")
        sys.exit(1)

    presentation_dir = sys.argv[1]

    if not os.path.exists(presentation_dir):
        print(f"エラー: プレゼンテーションディレクトリが見つかりません: {presentation_dir}")
        sys.exit(1)

    # 出力ディレクトリ
    root_dir = Path(__file__).parent.parent
    output_dir = root_dir / "slide_images"

    # スライドを準備
    metadata_file = prepare_slides(presentation_dir, output_dir)

    print(f"\n完了: スライド画像の準備が完了しました")

    # GitHub Actions用に環境変数に保存
    if 'GITHUB_ENV' in os.environ:
        with open(os.environ['GITHUB_ENV'], 'a') as f:
            f.write(f"SLIDES_METADATA={metadata_file}\n")
            f.write(f"SLIDES_DIR={output_dir}\n")

if __name__ == "__main__":
    main()
