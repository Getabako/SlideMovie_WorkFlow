#!/usr/bin/env python3
"""
画像プロンプト生成スクリプト
スライドファイルを読み込み、各ページに適した画像プロンプトを生成してCSVに保存します
"""

import sys
import os
import csv
import re
from pathlib import Path
from google import genai


def parse_slides(slide_file):
    """
    Marpスライドファイルを解析してページごとに分割

    Args:
        slide_file: スライドファイルのパス

    Returns:
        ページごとの内容のリスト
    """
    with open(slide_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # ヘッダー部分を除去
    parts = content.split('---\n')

    # 最初の2つはヘッダーなので除外
    slides = []
    current_slide = []

    for i, part in enumerate(parts):
        if i == 0:  # 最初の空の部分
            continue
        if i == 1:  # Marpヘッダー
            continue

        # 空でない部分はスライドとして追加
        if part.strip():
            slides.append(part.strip())

    return slides


def generate_image_prompt(slide_content, slide_number, api_key):
    """
    Gemini APIを使用してスライド内容から画像プロンプトを生成

    Args:
        slide_content: スライドの内容
        slide_number: スライド番号
        api_key: Google AI APIキー

    Returns:
        生成された画像プロンプト
    """
    client = genai.Client(api_key=api_key)

    prompt = f"""以下のスライドの内容に基づいて、このスライドに添える画像の説明（画像生成AIへのプロンプト）を作成してください。

スライド内容:
{slide_content}

要件:
- 画像は縦長（3:4の比率）
- スライドの内容を視覚的に補完する画像
- プロフェッショナルで洗練されたスタイル
- 抽象的すぎず、具体的すぎない
- 1-2文で簡潔に

画像プロンプト（日本語または英語）:"""

    response = client.models.generate_content(
        model="gemini-2.0-flash-exp",
        contents=prompt
    )

    return response.text.strip()


def create_image_prompts_csv(slide_file, output_dir, api_key):
    """
    スライドファイルから画像プロンプトCSVを作成

    Args:
        slide_file: スライドファイルのパス
        output_dir: 出力ディレクトリ
        api_key: Google AI APIキー

    Returns:
        生成されたCSVファイルのパス
    """
    # スライドを解析
    slides = parse_slides(slide_file)

    # 出力ファイル名を生成
    slide_name = Path(slide_file).stem.replace('_slide', '')
    output_file = Path(output_dir) / f"{slide_name}_imageprompt.csv"

    # CSVファイルを作成
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['page_number', 'image_prompt'])

        for i, slide_content in enumerate(slides, start=1):
            print(f"ページ {i}/{len(slides)} の画像プロンプトを生成中...")

            # Gemini APIを使用してプロンプトを生成
            try:
                image_prompt = generate_image_prompt(slide_content, i, api_key)
                writer.writerow([i, image_prompt])
                print(f"  → {image_prompt}")
            except Exception as e:
                print(f"  エラー: {e}")
                # エラーの場合はスライドのタイトルを使用
                title_match = re.search(r'#\s+(.+)', slide_content)
                if title_match:
                    fallback_prompt = f"Illustration for: {title_match.group(1)}"
                else:
                    fallback_prompt = f"Illustration for slide {i}"
                writer.writerow([i, fallback_prompt])
                print(f"  → フォールバック: {fallback_prompt}")

    print(f"\n画像プロンプトCSVを作成しました: {output_file}")
    return str(output_file)


def main():
    if len(sys.argv) < 2:
        print("使用方法: python generate_image_prompts.py <slide_file>")
        sys.exit(1)

    slide_file = sys.argv[1]

    if not os.path.exists(slide_file):
        print(f"エラー: スライドファイルが見つかりません: {slide_file}")
        sys.exit(1)

    # APIキーを環境変数から取得
    api_key = os.environ.get('GOOGLE_AI_API_KEY')
    if not api_key:
        print("エラー: GOOGLE_AI_API_KEY環境変数が設定されていません")
        sys.exit(1)

    # 出力ディレクトリ
    script_dir = Path(__file__).parent
    output_dir = script_dir.parent / "slides"
    output_dir.mkdir(exist_ok=True)

    # 画像プロンプトCSVを作成
    csv_file = create_image_prompts_csv(slide_file, output_dir, api_key)

    # 次のステップのために環境変数に保存
    if 'GITHUB_ENV' in os.environ:
        with open(os.environ['GITHUB_ENV'], 'a') as f:
            f.write(f"IMAGE_PROMPT_CSV={csv_file}\n")


if __name__ == "__main__":
    main()
