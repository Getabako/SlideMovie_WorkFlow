#!/usr/bin/env python3
"""
画像生成スクリプト
CSVファイルから画像プロンプトを読み込み、NanoBanana (Gemini 2.5 Flash Image)で画像を生成します
"""

import sys
import os
import csv
import time
from pathlib import Path
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO


def generate_images_from_csv(csv_file, output_dir, topic_name, api_key):
    """
    CSVファイルから画像プロンプトを読み込み、画像を生成

    Args:
        csv_file: 画像プロンプトCSVファイルのパス
        output_dir: 出力ディレクトリ
        topic_name: トピック名（ファイル名のプレフィックス）
        api_key: Google AI APIキー

    Returns:
        生成された画像ファイルのリスト
    """
    # Google AI Clientを初期化
    client = genai.Client(api_key=api_key)

    # CSVファイルを読み込む
    prompts = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            prompts.append({
                'page_number': int(row['page_number']),
                'prompt': row['image_prompt']
            })

    # 画像を生成
    generated_images = []
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    for item in prompts:
        page_num = item['page_number']
        prompt = item['prompt']

        print(f"\nページ {page_num} の画像を生成中...")
        print(f"プロンプト: {prompt}")

        try:
            # NanoBanana (Gemini 2.5 Flash Image) で画像を生成
            # 3:4の縦長アスペクト比を指定
            response = client.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=[prompt],
                config=types.GenerateContentConfig(
                    image_config=types.ImageConfig(
                        aspect_ratio="3:4",
                    )
                )
            )

            # 画像を保存
            for part in response.candidates[0].content.parts:
                if part.inline_data is not None:
                    image = Image.open(BytesIO(part.inline_data.data))

                    # ファイル名を生成
                    image_filename = f"{topic_name}_page{page_num:02d}.png"
                    image_path = output_path / image_filename

                    # 画像を保存
                    image.save(image_path)
                    generated_images.append(str(image_path))

                    print(f"  → 保存しました: {image_path}")

            # API rate limitを考慮して少し待機
            time.sleep(2)

        except Exception as e:
            print(f"  エラー: {e}")
            # エラーの場合はプレースホルダー画像を作成
            image = Image.new('RGB', (768, 1024), color=(200, 200, 200))
            image_filename = f"{topic_name}_page{page_num:02d}.png"
            image_path = output_path / image_filename
            image.save(image_path)
            generated_images.append(str(image_path))
            print(f"  → プレースホルダー画像を保存しました: {image_path}")

    print(f"\n合計 {len(generated_images)} 枚の画像を生成しました")
    return generated_images


def main():
    if len(sys.argv) < 3:
        print("使用方法: python generate_images.py <csv_file> <topic_name>")
        sys.exit(1)

    csv_file = sys.argv[1]
    topic_name = sys.argv[2]

    if not os.path.exists(csv_file):
        print(f"エラー: CSVファイルが見つかりません: {csv_file}")
        sys.exit(1)

    # APIキーを環境変数から取得
    api_key = os.environ.get('GOOGLE_AI_API_KEY')
    if not api_key:
        print("エラー: GOOGLE_AI_API_KEY環境変数が設定されていません")
        sys.exit(1)

    # 出力ディレクトリ
    script_dir = Path(__file__).parent
    output_dir = script_dir.parent / "images"
    output_dir.mkdir(exist_ok=True)

    # 画像を生成
    generated_images = generate_images_from_csv(csv_file, output_dir, topic_name, api_key)

    # 次のステップのために環境変数に保存
    if 'GITHUB_ENV' in os.environ:
        with open(os.environ['GITHUB_ENV'], 'a') as f:
            f.write(f"GENERATED_IMAGES={','.join(generated_images)}\n")
            f.write(f"IMAGE_DIR={output_dir}\n")


if __name__ == "__main__":
    main()
