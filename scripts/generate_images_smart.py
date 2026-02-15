#!/usr/bin/env python3
"""
スマート画像生成スクリプト

プロンプトJSONファイルを読み込み、各スライドに適した画像を生成します。
講義場面では講師キャラクターとロゴを含めた画像を生成します。
"""

import os
import re
import sys
import json
import time
import argparse
import base64
from pathlib import Path
from typing import List, Dict, Optional
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO


class SmartImageGenerator:
    """スマート画像生成クラス"""

    # キャラクター・ロゴのパス設定
    CHARACTER_DIR = Path(__file__).parent.parent / "presentations" / "character"
    INSTRUCTOR_IMAGE = CHARACTER_DIR / "塾頭高崎翔太" / "塾頭高崎翔太.png"
    INSTRUCTOR_IMAGE_ANGLED = CHARACTER_DIR / "塾頭高崎翔太" / "塾頭高崎翔太斜め.png"
    LOGO_IMAGE = CHARACTER_DIR / "ロゴ" / "if塾ロゴ.png"

    # キャラクター詳細（CSVから）
    INSTRUCTOR_DESCRIPTION = """30代前半の日本人男性講師。黒髪ミディアム丈で後ろで小さくまとめ、グレーのニット帽を着用。
黒いテーラードジャケットにインナーは赤色のフード付きパーカー（フードがジャケットから覗いている）。
暖かく友好的な黒い瞳、穏やかな笑顔、親しみやすい雰囲気。"""

    def __init__(self, api_key: str, aspect_ratio: str = '3:4'):
        """初期化"""
        self.api_key = api_key
        self.aspect_ratio = aspect_ratio
        self.client = genai.Client(api_key=self.api_key)

        # 参照画像を読み込み
        self.instructor_image_data = self._load_image(self.INSTRUCTOR_IMAGE)
        self.instructor_angled_data = self._load_image(self.INSTRUCTOR_IMAGE_ANGLED)
        self.logo_image_data = self._load_image(self.LOGO_IMAGE)

    def _load_image(self, image_path: Path) -> Optional[bytes]:
        """画像ファイルを読み込んでバイトデータを返す"""
        if image_path.exists():
            with open(image_path, 'rb') as f:
                return f.read()
        else:
            print(f"Warning: Image not found: {image_path}")
            return None

    def generate_image_with_instructor(self, prompt: str, output_path: str, slide_num: int) -> bool:
        """
        講師キャラクターを含む画像を生成（Gemini 2.5 Flash使用）

        Args:
            prompt: 画像生成プロンプト
            output_path: 出力先パス
            slide_num: スライド番号

        Returns:
            成功した場合True
        """
        print(f"\n[Slide {slide_num}] Generating image with instructor (Gemini 2.5 Flash Image)...")
        print(f"  Prompt: {prompt[:80]}...")

        # 講師用のプロンプトを拡張
        instructor_prompt = f"""Create an educational presentation image with the following requirements:

1. MAIN SCENE: {prompt}

2. INSTRUCTOR: Include a Japanese male instructor (30s) in the scene. He should be:
   - Wearing a black tailored jacket with a red hoodie underneath (hood visible)
   - Wearing a gray knit beanie/cap
   - Having black hair, friendly smile, approachable demeanor
   - Positioned naturally in the scene as if teaching or presenting
   - The instructor should match the reference image provided

3. LOGO: Include a white star-shaped logo (if塾ロゴ) subtly in the corner or background
   - Do NOT modify the logo's shape or colors
   - Keep it small and unobtrusive

4. STYLE: Modern, professional educational presentation style
   - Clean composition
   - Vibrant but professional colors
   - 3:4 vertical aspect ratio
   - No text or words in the image
"""

        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"  [Attempt {attempt + 1}/{max_retries}] Calling Gemini 2.5 Flash Image API...")

                # 参照画像を含むコンテンツを構築
                contents = [instructor_prompt]

                # 講師参照画像を追加
                if self.instructor_image_data:
                    contents.append(types.Part.from_bytes(
                        data=self.instructor_image_data,
                        mime_type="image/png"
                    ))
                    contents.append("This is the reference image for the instructor character. Match this person's appearance.")

                # ロゴ参照画像を追加
                if self.logo_image_data:
                    contents.append(types.Part.from_bytes(
                        data=self.logo_image_data,
                        mime_type="image/png"
                    ))
                    contents.append("This is the logo to include. Do not modify its shape or colors.")

                # Gemini 2.5 Flash Image で画像を生成
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash-image",
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE", "TEXT"],
                    )
                )

                # 画像を保存
                for part in response.candidates[0].content.parts:
                    if part.inline_data is not None:
                        image = Image.open(BytesIO(part.inline_data.data))
                        image.save(output_path)
                        print(f"  ✓ Image saved: {output_path} ({image.size[0]}x{image.size[1]})")
                        return True

                print(f"  ⚠ No image data in response, retrying...")
                time.sleep(2)

            except Exception as e:
                error_msg = str(e)
                print(f"  ✗ Error: {type(e).__name__}: {error_msg[:100]}")

                # Gemini 2.5が画像生成をサポートしていない場合や見つからない場合、2.0にフォールバック
                if 'not supported' in error_msg.lower() or 'invalid' in error_msg.lower() or 'not found' in error_msg.lower():
                    print(f"  Falling back to Gemini 2.0 Flash...")
                    return self.generate_image(prompt, output_path, slide_num)

                # レート制限エラーの場合は長めに待機
                if 'rate' in error_msg.lower() or '429' in error_msg:
                    print(f"  Rate limit hit, waiting 30 seconds...")
                    time.sleep(30)
                elif attempt < max_retries - 1:
                    print(f"  Retrying in 3 seconds...")
                    time.sleep(3)
                else:
                    print(f"  ✗ All attempts failed, falling back to Gemini 2.0 Flash...")
                    return self.generate_image(prompt, output_path, slide_num)

        return False

    def generate_image(self, prompt: str, output_path: str, slide_num: int) -> bool:
        """
        指定されたプロンプトで画像を生成（Gemini 2.0 Flash使用）

        Args:
            prompt: 画像生成プロンプト
            output_path: 出力先パス
            slide_num: スライド番号

        Returns:
            成功した場合True
        """
        print(f"\n[Slide {slide_num}] Generating image (Gemini 2.0 Flash)...")
        print(f"  Prompt: {prompt[:80]}...")

        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"  [Attempt {attempt + 1}/{max_retries}] Calling Gemini API...")

                # Gemini 2.0 Flash Image で画像を生成
                response = self.client.models.generate_content(
                    model="gemini-2.0-flash-exp-image-generation",
                    contents=[prompt],
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE", "TEXT"],
                    )
                )

                # 画像を保存
                for part in response.candidates[0].content.parts:
                    if part.inline_data is not None:
                        image = Image.open(BytesIO(part.inline_data.data))
                        image.save(output_path)
                        print(f"  ✓ Image saved: {output_path} ({image.size[0]}x{image.size[1]})")
                        return True

                print(f"  ⚠ No image data in response, retrying...")
                time.sleep(2)

            except Exception as e:
                error_msg = str(e)
                print(f"  ✗ Error: {type(e).__name__}: {error_msg[:100]}")

                # レート制限エラーの場合は長めに待機
                if 'rate' in error_msg.lower() or '429' in error_msg:
                    print(f"  Rate limit hit, waiting 30 seconds...")
                    time.sleep(30)
                elif attempt < max_retries - 1:
                    print(f"  Retrying in 3 seconds...")
                    time.sleep(3)
                else:
                    print(f"  ✗ All attempts failed for slide {slide_num}")
                    return False

        return False

    def process_prompts(self, prompts_file: str, output_dir: Path):
        """
        プロンプトファイルを処理して画像を生成

        Args:
            prompts_file: プロンプトJSONファイル
            output_dir: 出力ディレクトリ
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        # プロンプトを読み込み
        with open(prompts_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        prompts = data.get('prompts', [])
        print(f"Loaded {len(prompts)} prompts from {prompts_file}")
        print(f"Output directory: {output_dir}")

        # 講師画像の読み込み状況を表示
        if self.instructor_image_data:
            print(f"Instructor image loaded: {self.INSTRUCTOR_IMAGE}")
        if self.logo_image_data:
            print(f"Logo image loaded: {self.LOGO_IMAGE}")

        success_count = 0
        skip_count = 0
        instructor_count = 0

        for p in prompts:
            slide_num = p['slide_number']
            prompt = p['prompt']
            needs_instructor = p.get('needs_instructor', False)

            # 出力ファイル名
            image_filename = f"{slide_num:03d}.png"
            output_path = output_dir / image_filename

            # すでに存在する場合はスキップ
            if output_path.exists():
                print(f"[Slide {slide_num}] Image already exists, skipping...")
                skip_count += 1
                continue

            # 画像を生成（講師が必要な場合はGemini 2.5を使用）
            if needs_instructor:
                instructor_count += 1
                success = self.generate_image_with_instructor(prompt, str(output_path), slide_num)
            else:
                success = self.generate_image(prompt, str(output_path), slide_num)

            if success:
                success_count += 1

            # API rate limit対策
            time.sleep(3)

        print(f"\n=== Summary ===")
        print(f"Total slides: {len(prompts)}")
        print(f"Generated: {success_count}")
        print(f"  - With instructor (2.5 Flash): {instructor_count}")
        print(f"  - Without instructor (2.0 Flash): {success_count - instructor_count if success_count > instructor_count else 0}")
        print(f"Skipped: {skip_count}")
        print(f"Failed: {len(prompts) - success_count - skip_count}")


def main():
    parser = argparse.ArgumentParser(
        description='Generate images from smart prompts'
    )
    parser.add_argument('prompts_file', help='Path to prompts JSON file')
    parser.add_argument(
        '--output-dir',
        required=True,
        help='Output directory for images'
    )
    parser.add_argument(
        '--aspect-ratio',
        choices=['3:4', '4:3', '16:9', '9:16'],
        default='3:4',
        help='Image aspect ratio (default: 3:4)'
    )

    args = parser.parse_args()

    # APIキーを環境変数から取得
    api_key = os.environ.get('GOOGLE_AI_API_KEY')
    if not api_key:
        print("Error: GOOGLE_AI_API_KEY environment variable not set")
        sys.exit(1)

    generator = SmartImageGenerator(
        api_key=api_key,
        aspect_ratio=args.aspect_ratio
    )

    generator.process_prompts(
        prompts_file=args.prompts_file,
        output_dir=Path(args.output_dir)
    )


if __name__ == '__main__':
    main()
