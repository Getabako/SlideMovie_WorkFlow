#!/usr/bin/env python3
"""
スライド画像自動生成スクリプト

各スライドの内容から画像プロンプトを生成し、
Stable Diffusion APIまたはGoogle Imagen APIを使用して画像を生成します。
"""

import os
import re
import sys
import json
import argparse
import requests
from pathlib import Path
from typing import List, Dict, Tuple
import google.generativeai as genai


class SlideImageGenerator:
    """スライド画像生成クラス"""

    def __init__(self, md_file: str, api_key: str, image_api: str = "stable-diffusion"):
        """
        初期化

        Args:
            md_file: マークダウンファイルのパス
            api_key: Google AI APIキー
            image_api: 使用する画像生成API ("stable-diffusion" or "imagen")
        """
        self.md_file = Path(md_file)
        self.api_key = api_key
        self.image_api = image_api
        self.images_dir = self.md_file.parent / "images"
        self.images_dir.mkdir(exist_ok=True)

        # Gemini設定
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')

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
            # 既存の画像パスを抽出
            image_match = re.search(r'!\[bg [^\]]*\]\(([^)]+)\)', slide)
            existing_image = image_match.group(1) if image_match else None

            # タイトルを抽出
            title_match = re.search(r'^#+ (.+)$', slide, re.MULTILINE)
            title = title_match.group(1) if title_match else f"Slide {i}"

            # スライド内容（画像タグを除く）
            content_without_image = re.sub(r'!\[bg [^\]]*\]\([^)]+\)\n?', '', slide).strip()

            slide_data.append({
                'number': i,
                'title': title,
                'content': content_without_image,
                'existing_image': existing_image
            })

        return slide_data

    def generate_image_prompt(self, slide: Dict[str, str]) -> str:
        """
        スライド内容から画像生成プロンプトを作成

        Args:
            slide: スライド情報

        Returns:
            画像生成プロンプト
        """
        prompt_request = f"""以下のプレゼンテーションスライドの内容を含む、完成されたスライド画像を生成するためのプロンプトを作成してください。

スライドタイトル: {slide['title']}

スライド内容:
{slide['content'][:500]}

要件:
- 日本語テキスト（タイトルと内容）を画像内に直接レンダリングすること
- タイトルは大きく目立つように配置
- 内容テキストは読みやすく配置
- プロフェッショナルで洗練されたデザイン
- 16:9の横長比率
- スライド全体が1枚の完成画像として成立すること

画像生成プロンプトのみを出力してください（説明は不要）。
プロンプトは日本語で、スライドに表示するテキスト内容も含めて具体的に記述してください。"""

        response = self.model.generate_content(prompt_request)
        image_prompt = response.text.strip()

        # もし日本語が含まれていたら再試行
        if any('\u3040' <= c <= '\u309F' or '\u30A0' <= c <= '\u30FF' or '\u4E00' <= c <= '\u9FFF' for c in image_prompt):
            prompt_request += "\n\n重要: プロンプトは必ず英語で出力してください。"
            response = self.model.generate_content(prompt_request)
            image_prompt = response.text.strip()

        print(f"  Generated prompt: {image_prompt[:100]}...")
        return image_prompt

    def generate_image_stable_diffusion(self, prompt: str, output_path: str) -> bool:
        """
        Stable Diffusion APIで画像生成（Stability AIの公式API使用）

        Args:
            prompt: 画像生成プロンプト
            output_path: 出力先パス

        Returns:
            成功した場合True
        """
        # Stability AI API（要APIキー）
        # https://platform.stability.ai/
        api_key = os.environ.get("STABILITY_API_KEY")

        if not api_key:
            print("  Warning: STABILITY_API_KEY not set. Using placeholder image.")
            return self._create_placeholder_image(output_path, prompt)

        url = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        data = {
            "text_prompts": [
                {
                    "text": prompt,
                    "weight": 1
                }
            ],
            "cfg_scale": 7,
            "height": 1024,
            "width": 1792,  # 16:9 aspect ratio
            "samples": 1,
            "steps": 30,
        }

        try:
            response = requests.post(url, headers=headers, json=data, timeout=60)
            response.raise_for_status()

            result = response.json()

            # 画像データを保存
            import base64
            image_data = base64.b64decode(result["artifacts"][0]["base64"])

            with open(output_path, 'wb') as f:
                f.write(image_data)

            print(f"  ✓ Image generated: {output_path}")
            return True

        except Exception as e:
            print(f"  Error generating image: {e}")
            return self._create_placeholder_image(output_path, prompt)

    def _create_placeholder_image(self, output_path: str, prompt: str) -> bool:
        """
        プレースホルダー画像を作成（APIが使えない場合）

        Args:
            output_path: 出力先パス
            prompt: プロンプト（画像にテキストとして表示）

        Returns:
            成功した場合True
        """
        try:
            from PIL import Image, ImageDraw, ImageFont

            # 16:9比率の画像を作成
            width, height = 1792, 1008

            # グラデーション背景
            img = Image.new('RGB', (width, height), color='#2C3E50')
            draw = ImageDraw.Draw(img)

            # グラデーション効果
            for y in range(height):
                r = int(44 + (100 - 44) * y / height)
                g = int(62 + (120 - 62) * y / height)
                b = int(80 + (140 - 80) * y / height)
                draw.line([(0, y), (width, y)], fill=(r, g, b))

            # プロンプトをテキストとして中央に配置
            try:
                # フォントサイズを調整
                font = ImageFont.truetype("/System/Library/Fonts/Hiragino Sans GB.ttc", 40)
            except:
                font = ImageFont.load_default()

            # テキストを折り返し
            words = prompt.split()
            lines = []
            current_line = []

            for word in words:
                current_line.append(word)
                test_line = ' '.join(current_line)
                bbox = draw.textbbox((0, 0), test_line, font=font)
                if bbox[2] - bbox[0] > width - 100:
                    current_line.pop()
                    lines.append(' '.join(current_line))
                    current_line = [word]

            if current_line:
                lines.append(' '.join(current_line))

            # テキストを中央に描画
            y_offset = (height - len(lines) * 60) // 2
            for i, line in enumerate(lines[:5]):  # 最大5行まで
                bbox = draw.textbbox((0, 0), line, font=font)
                text_width = bbox[2] - bbox[0]
                x = (width - text_width) // 2
                y = y_offset + i * 60

                # 影
                draw.text((x+2, y+2), line, fill='#000000', font=font)
                # テキスト
                draw.text((x, y), line, fill='#ECF0F1', font=font)

            img.save(output_path)
            print(f"  ✓ Placeholder image created: {output_path}")
            return True

        except Exception as e:
            print(f"  Error creating placeholder: {e}")
            return False

    def process_all_slides(self):
        """すべてのスライドの画像を生成"""
        print(f"Processing slides from: {self.md_file}")
        print(f"Images will be saved to: {self.images_dir}")

        slides = self.parse_slides()
        print(f"Found {len(slides)} slides")

        for slide in slides:
            print(f"\nProcessing Slide {slide['number']}: {slide['title']}")

            # 既存の画像パスから番号を抽出
            if slide['existing_image']:
                # images/040___.png -> 040
                match = re.search(r'(\d+)', slide['existing_image'])
                if match:
                    image_number = match.group(1)
                else:
                    image_number = f"{slide['number']:03d}"
            else:
                image_number = f"{slide['number'] + 39:03d}"  # 040から開始

            output_filename = f"{image_number}_______________________________.png"
            output_path = self.images_dir / output_filename

            # すでに画像が存在する場合はスキップ
            if output_path.exists():
                print(f"  Image already exists, skipping...")
                continue

            # 画像プロンプトを生成
            image_prompt = self.generate_image_prompt(slide)

            # 画像を生成
            if self.image_api == "stable-diffusion":
                self.generate_image_stable_diffusion(image_prompt, str(output_path))
            else:
                print(f"  Image API '{self.image_api}' not yet implemented")
                self._create_placeholder_image(str(output_path), image_prompt)

        print("\n✓ All slides processed!")


def main():
    parser = argparse.ArgumentParser(description='Generate images for presentation slides')
    parser.add_argument('md_file', help='Path to markdown file')
    parser.add_argument('--api', choices=['stable-diffusion', 'imagen'],
                       default='stable-diffusion',
                       help='Image generation API to use')

    args = parser.parse_args()

    # APIキーを環境変数から取得
    google_api_key = os.environ.get('GOOGLE_AI_API_KEY')
    if not google_api_key:
        print("Error: GOOGLE_AI_API_KEY environment variable not set")
        sys.exit(1)

    # 画像生成
    generator = SlideImageGenerator(
        md_file=args.md_file,
        api_key=google_api_key,
        image_api=args.api
    )

    generator.process_all_slides()


if __name__ == '__main__':
    main()
