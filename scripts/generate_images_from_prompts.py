#!/usr/bin/env python3
"""
画像プロンプトCSVから画像生成スクリプト（キャラクター対応）

画像プロンプト.csvを読み込み、NanoBananaで画像を生成します。
キャラクターが指定されている場合はimage-to-imageを使用します。
"""

import os
import csv
import sys
import time
import argparse
from pathlib import Path
from typing import Dict, Optional
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO


class CharacterImageGenerator:
    """キャラクター対応画像生成クラス"""

    def __init__(self, api_key: str, character_dir: Path):
        self.api_key = api_key
        self.character_dir = character_dir

        # Google AI Client初期化（NanoBanana用）
        self.client = genai.Client(api_key=self.api_key)

        # キャラクター画像パスのキャッシュ
        self.character_images = self._load_character_images()

    def _load_character_images(self) -> Dict[str, Path]:
        """キャラクター画像パスを読み込み"""
        images = {}

        for char_folder in self.character_dir.iterdir():
            if not char_folder.is_dir() or char_folder.name == 'ロゴ':
                continue

            # 画像ファイルを探す
            image_files = list(char_folder.glob('*.png')) + list(char_folder.glob('*.jpg'))
            if image_files:
                images[char_folder.name] = image_files[0]

        return images

    def get_character_image_path(self, character_name: str) -> Optional[Path]:
        """キャラクター名から画像パスを取得"""
        for name, path in self.character_images.items():
            if character_name in name:
                return path
        return None

    def generate_image(
        self,
        prompt: str,
        character: str,
        aspect_ratio: str,
        output_path: Path
    ) -> bool:
        """
        画像を生成

        Args:
            prompt: 画像生成プロンプト
            character: キャラクター名（「なし」の場合はtext-to-image）
            aspect_ratio: アスペクト比
            output_path: 出力先パス

        Returns:
            成功した場合True
        """

        # キャラクター画像パスを取得
        character_image_path = None
        if character and character != 'なし':
            character_image_path = self.get_character_image_path(character)

        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"  [Attempt {attempt + 1}/{max_retries}] Generating image...")

                # 文字描画を避ける指示と日本人デフォルトを追加
                no_text_instruction = "\n\nIMPORTANT: Do not include any text, letters, words, signs, labels, or written content in the image. Keep the image purely visual without any typography. When generating people, default to Japanese people unless otherwise specified."

                if character_image_path:
                    # Image-to-image生成
                    print(f"  Using character image: {character_image_path.name}")

                    # キャラクター画像を読み込み
                    with open(character_image_path, 'rb') as f:
                        character_image_data = f.read()

                    # プロンプトにキャラクター情報を追加
                    enhanced_prompt = f"{prompt}\n\nInclude the character from the reference image in the scene.{no_text_instruction}"

                    # NanoBananaでimage-to-image生成
                    response = self.client.models.generate_content(
                        model="gemini-2.5-flash-image",
                        contents=[
                            types.Part.from_bytes(
                                data=character_image_data,
                                mime_type="image/png"
                            ),
                            enhanced_prompt
                        ],
                        config=types.GenerateContentConfig(
                            image_config=types.ImageConfig(
                                aspect_ratio=aspect_ratio,
                            )
                        )
                    )
                else:
                    # Text-to-image生成
                    text_prompt = f"{prompt}{no_text_instruction}"
                    response = self.client.models.generate_content(
                        model="gemini-2.5-flash-image",
                        contents=[text_prompt],
                        config=types.GenerateContentConfig(
                            image_config=types.ImageConfig(
                                aspect_ratio=aspect_ratio,
                            )
                        )
                    )

                # 画像を保存
                for part in response.candidates[0].content.parts:
                    if part.inline_data is not None:
                        image = Image.open(BytesIO(part.inline_data.data))
                        image.save(output_path)
                        print(f"  ✓ Image saved: {output_path.name} ({image.size[0]}x{image.size[1]})")
                        return True

                print(f"  ⚠ No image data in response")
                time.sleep(2)

            except Exception as e:
                print(f"  ✗ Error: {type(e).__name__}: {str(e)[:150]}")
                if attempt < max_retries - 1:
                    print(f"  Retrying in 2 seconds...")
                    time.sleep(2)
                else:
                    print(f"  ✗ All attempts failed")
                    return False

        return False


def main():
    parser = argparse.ArgumentParser(
        description='Generate images from CSV prompts with character support'
    )
    parser.add_argument('csv_file', help='Path to image prompts CSV file')
    parser.add_argument(
        '--output-dir',
        help='Output directory for images',
        default=None
    )
    parser.add_argument(
        '--character-dir',
        help='Path to character directory',
        default='presentations/character'
    )

    args = parser.parse_args()

    # パス設定
    csv_path = Path(args.csv_file)
    if not csv_path.exists():
        print(f"Error: CSV file not found: {csv_path}")
        sys.exit(1)

    # 出力ディレクトリの決定
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = csv_path.parent / 'images'

    output_dir.mkdir(parents=True, exist_ok=True)

    # キャラクターディレクトリ
    character_dir = Path(args.character_dir)
    if not character_dir.exists():
        print(f"Warning: Character directory not found: {character_dir}")
        print("Proceeding with text-to-image only...")

    # APIキー取得
    api_key = os.environ.get('GOOGLE_AI_API_KEY')
    if not api_key:
        print("Error: GOOGLE_AI_API_KEY environment variable not set")
        sys.exit(1)

    print(f"Processing prompts from: {csv_path}")
    print(f"Output directory: {output_dir}")
    print(f"Character directory: {character_dir}")

    # 画像生成器初期化
    generator = CharacterImageGenerator(api_key, character_dir)
    print(f"Loaded {len(generator.character_images)} character images\n")

    # CSV読み込み
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Found {len(rows)} image prompts\n")

    # 画像生成
    success_count = 0
    for i, row in enumerate(rows, 1):
        slide_number = row.get('slide_number', str(i).zfill(3))
        title = row.get('title', f'Slide {i}')
        prompt = row.get('prompt', '')
        character = row.get('character', 'なし')
        aspect_ratio = row.get('aspect_ratio', '3:4')

        output_path = output_dir / f"{slide_number}.png"

        # すでに画像が存在する場合はスキップ
        if output_path.exists():
            print(f"[{i}/{len(rows)}] {title}")
            print(f"  Image already exists, skipping...")
            success_count += 1
            continue

        print(f"[{i}/{len(rows)}] {title}")
        print(f"  Character: {character}")

        # 画像生成
        success = generator.generate_image(
            prompt=prompt,
            character=character,
            aspect_ratio=aspect_ratio,
            output_path=output_path
        )

        if success:
            success_count += 1
        else:
            print(f"  ⚠ Failed to generate image for slide {slide_number}")

        # API rate limit対策
        if i < len(rows):
            time.sleep(2)

    print(f"\n✓ Image generation complete!")
    print(f"Success: {success_count}/{len(rows)} images")
    print(f"Output directory: {output_dir}")


if __name__ == '__main__':
    main()
