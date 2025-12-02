#!/usr/bin/env python3
"""
スライドに画像を挿入するスクリプト

生成された画像を各スライドに適切な形式で配置します。
"""

import os
import re
import sys
import argparse
from pathlib import Path
from typing import List, Dict


class SlideImageInserter:
    """スライド画像挿入クラス"""

    def __init__(
        self,
        md_file: str,
        images_dir: str,
        alignment: str = 'right',
        width: str = '45%',
        aspect_ratio: str = '3:4'
    ):
        """
        初期化

        Args:
            md_file: マークダウンファイルのパス
            images_dir: 画像ディレクトリのパス
            alignment: 画像の配置 ('right' or 'left')
            width: 画像の幅（%指定）
            aspect_ratio: アスペクト比
        """
        self.md_file = Path(md_file)
        self.images_dir = Path(images_dir)
        self.alignment = alignment
        self.width = width
        self.aspect_ratio = aspect_ratio

    def get_image_files(self) -> List[Path]:
        """
        画像ファイルを名前順に取得

        Returns:
            画像ファイルのリスト
        """
        # .pngファイルを取得して名前順にソート
        image_files = sorted(self.images_dir.glob('*.png'))

        print(f"Found {len(image_files)} images in {self.images_dir}")
        for img in image_files[:5]:  # 最初の5枚を表示
            print(f"  - {img.name}")
        if len(image_files) > 5:
            print(f"  ... and {len(image_files) - 5} more")

        return image_files

    def parse_slides(self, content: str) -> List[Dict]:
        """
        スライドを解析

        Args:
            content: マークダウンコンテンツ

        Returns:
            スライド情報のリスト
        """
        # スライドを分割
        slides = content.split('\n---\n')

        slide_data = []
        for i, slide_content in enumerate(slides):
            # すでに画像が含まれているかチェック
            has_image = bool(re.search(r'!\[bg [^\]]*\]', slide_content))

            # ヘッダースライド（marp設定）をスキップ
            is_header = (i == 0 and 'marp: true' in slide_content)

            slide_data.append({
                'index': i,
                'content': slide_content,
                'has_image': has_image,
                'is_header': is_header
            })

        return slide_data

    def insert_image_to_slide(self, slide_content: str, image_path: Path) -> str:
        """
        スライドに画像を挿入

        Args:
            slide_content: スライドの内容
            image_path: 画像ファイルのパス

        Returns:
            画像が挿入されたスライド内容
        """
        # 画像の相対パスを計算
        relative_path = f"images/{image_path.name}"

        # 画像タグを作成
        # 3:4の縦長画像の場合、上下幅をスライドに合わせる
        if self.aspect_ratio == '3:4':
            # 縦長画像は自動的に上下フルハイトになる
            image_tag = f"![bg {self.alignment}:{self.width}]({relative_path})"
        else:
            # 横長画像の場合
            image_tag = f"![bg {self.alignment}:{self.width}]({relative_path})"

        # スライドの先頭に画像を挿入
        # 既存の改行を維持しながら挿入
        lines = slide_content.split('\n')

        # <style>タグの終了位置を探す（存在する場合はその後に挿入）
        insert_index = 0
        in_style = False
        style_end_found = False

        for i, line in enumerate(lines):
            if '<style>' in line:
                in_style = True
            if '</style>' in line:
                in_style = False
                style_end_found = True
                insert_index = i + 1
                break

        # <style>タグがない場合は、最初の空でない行を見つける
        if not style_end_found:
            for i, line in enumerate(lines):
                if line.strip():
                    insert_index = i
                    break

        # 画像タグを挿入
        lines.insert(insert_index, image_tag)

        return '\n'.join(lines)

    def process(self):
        """
        スライドに画像を挿入して保存
        """
        # 画像ファイルを取得
        image_files = self.get_image_files()

        if not image_files:
            print("Error: No images found in the images directory")
            sys.exit(1)

        # マークダウンを読み込み
        with open(self.md_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # スライドを解析
        slides = self.parse_slides(content)

        # 画像を挿入
        image_index = 0
        modified_slides = []

        for slide in slides:
            # ヘッダースライドはそのまま
            if slide['is_header']:
                modified_slides.append(slide['content'])
                continue

            # すでに画像がある場合はスキップ
            if slide['has_image']:
                print(f"Slide {slide['index']}: Image already exists, skipping...")
                modified_slides.append(slide['content'])
                continue

            # 画像がまだある場合は挿入
            if image_index < len(image_files):
                image_file = image_files[image_index]
                modified_content = self.insert_image_to_slide(
                    slide['content'],
                    image_file
                )
                modified_slides.append(modified_content)
                print(f"Slide {slide['index']}: Inserted {image_file.name}")
                image_index += 1
            else:
                # 画像が足りない場合
                print(f"Slide {slide['index']}: No more images available")
                modified_slides.append(slide['content'])

        # マークダウンを再構築
        new_content = '\n---\n'.join(modified_slides)

        # ファイルに保存
        with open(self.md_file, 'w', encoding='utf-8') as f:
            f.write(new_content)

        print(f"\n✓ Images inserted into {self.md_file}")
        print(f"  Total slides: {len(slides)}")
        print(f"  Images inserted: {image_index}")


def main():
    parser = argparse.ArgumentParser(
        description='Insert images into presentation slides'
    )
    parser.add_argument('md_file', help='Path to markdown file')
    parser.add_argument(
        '--images-dir',
        required=True,
        help='Directory containing images'
    )
    parser.add_argument(
        '--alignment',
        choices=['right', 'left'],
        default='right',
        help='Image alignment (default: right)'
    )
    parser.add_argument(
        '--width',
        default='45%',
        help='Image width (default: 45%%)'
    )
    parser.add_argument(
        '--aspect-ratio',
        choices=['3:4', '4:3', '16:9', '9:16'],
        default='3:4',
        help='Image aspect ratio (default: 3:4)'
    )

    args = parser.parse_args()

    inserter = SlideImageInserter(
        md_file=args.md_file,
        images_dir=args.images_dir,
        alignment=args.alignment,
        width=args.width,
        aspect_ratio=args.aspect_ratio
    )

    inserter.process()


if __name__ == '__main__':
    main()
