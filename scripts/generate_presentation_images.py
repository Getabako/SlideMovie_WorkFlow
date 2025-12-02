#!/usr/bin/env python3
"""
プレゼンテーション画像生成スクリプト（3:4縦長対応）

各スライドの内容を読み取り、適切な画像を生成します。
"""

import os
import re
import sys
import time
import argparse
from pathlib import Path
from typing import List, Dict
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO


class PresentationImageGenerator:
    """プレゼンテーション画像生成クラス"""

    ASPECT_RATIOS = {
        '3:4': (1080, 1440),   # 縦長
        '4:3': (1440, 1080),   # 横長
        '16:9': (1792, 1008),  # ワイド横長
        '9:16': (1008, 1792),  # 縦長動画
    }

    def __init__(self, md_file: str, api_key: str, aspect_ratio: str = '3:4'):
        """
        初期化

        Args:
            md_file: マークダウンファイルのパス
            api_key: Google AI APIキー
            aspect_ratio: 画像のアスペクト比 ('3:4', '16:9', '4:3', '9:16')
        """
        self.md_file = Path(md_file)
        self.api_key = api_key
        self.aspect_ratio = aspect_ratio

        # アスペクト比に対応する画像サイズ
        self.width, self.height = self.ASPECT_RATIOS.get(
            aspect_ratio,
            self.ASPECT_RATIOS['3:4']  # デフォルト
        )

        # Google AI Client初期化（NanoBanana用）
        self.client = genai.Client(api_key=self.api_key)

    def parse_slides(self) -> List[Dict[str, str]]:
        """
        マークダウンファイルからスライドを解析

        Returns:
            スライド情報のリスト
        """
        with open(self.md_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # スライドを分割（---で区切られている）
        slides = content.split('\n---\n')

        slide_data = []
        for i, slide in enumerate(slides, 1):
            # ヘッダー（marp設定）をスキップ
            if i == 1 and 'marp: true' in slide:
                continue

            # タイトルを抽出
            title_match = re.search(r'^#+ (.+)$', slide, re.MULTILINE)
            title = title_match.group(1).strip() if title_match else f"Slide {i}"

            # スライド内容全体
            content_text = slide.strip()

            # 内容が空でなければ追加
            if content_text:
                slide_data.append({
                    'number': i,
                    'title': title,
                    'content': content_text
                })

        return slide_data

    def generate_slide_image(self, slide: Dict[str, str], output_path: str) -> bool:
        """
        NanoBanana (Gemini 2.5 Flash Image)を使ってスライド内容に合った画像を生成

        Args:
            slide: スライド情報
            output_path: 出力先パス

        Returns:
            成功した場合True
        """
        print(f"\nSlide {slide['number']}: {slide['title']}")
        print(f"  Generating image with NanoBanana (Gemini 2.5 Flash Image)...")

        # 画像生成プロンプト
        prompt = f"Create a professional abstract background image for a business presentation about: {slide['title']}. Vertical format, elegant design, sophisticated atmosphere, no text."

        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"  [Attempt {attempt + 1}/{max_retries}] Calling NanoBanana API...")

                # NanoBanana (Gemini 2.5 Flash Image) で画像を生成
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash-image",
                    contents=[prompt],
                    config=types.GenerateContentConfig(
                        image_config=types.ImageConfig(
                            aspect_ratio=self.aspect_ratio,
                        )
                    )
                )

                # 画像を保存
                for part in response.candidates[0].content.parts:
                    if part.inline_data is not None:
                        # BytesIOを使って画像を読み込み
                        image = Image.open(BytesIO(part.inline_data.data))

                        # 画像を保存
                        image.save(output_path)
                        print(f"  ✓ Image saved: {output_path} ({image.size[0]}x{image.size[1]})")
                        return True

                # 画像が見つからなかった場合
                print(f"  ⚠ No image data in response")
                time.sleep(2)

            except Exception as e:
                print(f"  ✗ Error: {type(e).__name__}: {str(e)[:150]}")
                if attempt < max_retries - 1:
                    print(f"  Retrying in 2 seconds...")
                    time.sleep(2)
                else:
                    print(f"  ✗ All attempts failed for slide {slide['number']}")
                    return False

        return False


    def process_all_slides(self, output_dir: Path):
        """
        すべてのスライドの画像を生成

        Args:
            output_dir: 出力ディレクトリ
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"Processing slides from: {self.md_file}")
        print(f"Aspect ratio: {self.aspect_ratio} ({self.width}x{self.height})")
        print(f"Output directory: {output_dir}")

        slides = self.parse_slides()
        print(f"Found {len(slides)} slides\n")

        for i, slide in enumerate(slides):
            # 画像ファイル名（連番）
            image_filename = f"{i+1:03d}.png"
            output_path = output_dir / image_filename

            # すでに画像が存在する場合はスキップ
            if output_path.exists():
                print(f"Slide {slide['number']}: Image already exists, skipping...")
                continue

            # NanoBananaで画像生成
            success = self.generate_slide_image(slide, str(output_path))

            if not success:
                print(f"  ⚠ Failed to generate image for slide {slide['number']}, skipping...")

            # API rate limit対策: 少し待機
            if i < len(slides) - 1:
                wait_time = 2
                print(f"  Waiting {wait_time}s before next slide...")
                time.sleep(wait_time)

        print(f"\n✓ All {len(slides)} slides processed!")
        print(f"Images saved to: {output_dir}")


def main():
    parser = argparse.ArgumentParser(
        description='Generate images for presentation slides'
    )
    parser.add_argument('md_file', help='Path to markdown file')
    parser.add_argument(
        '--aspect-ratio',
        choices=['3:4', '4:3', '16:9', '9:16'],
        default='3:4',
        help='Image aspect ratio (default: 3:4 for portrait)'
    )
    parser.add_argument(
        '--output-dir',
        help='Output directory for images',
        default=None
    )

    args = parser.parse_args()

    # 出力ディレクトリの決定
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        md_path = Path(args.md_file)
        output_dir = md_path.parent / 'images'

    # APIキーを環境変数から取得
    api_key = os.environ.get('GOOGLE_AI_API_KEY')
    if not api_key:
        print("Error: GOOGLE_AI_API_KEY environment variable not set")
        sys.exit(1)

    # 画像生成
    generator = PresentationImageGenerator(
        md_file=args.md_file,
        api_key=api_key,
        aspect_ratio=args.aspect_ratio
    )

    generator.process_all_slides(output_dir)


if __name__ == '__main__':
    main()
