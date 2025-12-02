#!/usr/bin/env python3
"""
スライド内容に合わせた画像プロンプト生成スクリプト（キャラクター対応）

スライドの内容を分析し、登場人物を含めた具体的な画像プロンプトを生成します。
"""

import os
import re
import csv
import sys
import argparse
from pathlib import Path
from typing import List, Dict
import google.generativeai as genai


class CharacterManager:
    """キャラクター情報管理クラス"""

    def __init__(self, character_dir: Path):
        self.character_dir = character_dir
        self.characters = self._load_characters()

    def _load_characters(self) -> List[Dict[str, str]]:
        """キャラクターCSVを読み込み"""
        characters = []

        # キャラクターフォルダを探索
        for char_folder in self.character_dir.iterdir():
            if not char_folder.is_dir() or char_folder.name == 'ロゴ':
                continue

            # CSVファイルを探す
            csv_files = list(char_folder.glob('*.csv'))
            if csv_files:
                csv_file = csv_files[0]
                with open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # 画像ファイルパスを追加
                        images = list(char_folder.glob('*.png')) + list(char_folder.glob('*.jpg'))
                        if images:
                            row['image_path'] = str(images[0])
                        characters.append(row)

        return characters

    def get_character_description(self, name: str) -> str:
        """キャラクター名から詳細説明を取得"""
        for char in self.characters:
            if char['name'] == name:
                return f"{char['appearance']}, {char['clothing']}, {char['personality']}"
        return ""

    def get_all_characters_info(self) -> str:
        """全キャラクター情報を文字列で返す"""
        info = []
        for char in self.characters:
            info.append(f"- {char['name']}: {char['appearance']}")
        return "\n".join(info)


class SlideAnalyzer:
    """スライド分析クラス"""

    def __init__(self, md_file: Path, api_key: str, character_manager: CharacterManager):
        self.md_file = md_file
        self.api_key = api_key
        self.character_manager = character_manager

        # Gemini設定
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')

    def parse_slides(self) -> List[Dict[str, str]]:
        """マークダウンファイルからスライドを解析"""
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

            # スライド内容全体（画像参照を削除）
            content_text = re.sub(r'!\[bg.*?\]\(.*?\)', '', slide).strip()

            # 内容が空でなければ追加
            if content_text:
                slide_data.append({
                    'number': len(slide_data) + 1,
                    'title': title,
                    'content': content_text
                })

        return slide_data

    def generate_image_prompt(self, slide: Dict[str, str]) -> str:
        """スライド内容から画像プロンプトを生成"""

        characters_info = self.character_manager.get_all_characters_info()

        prompt = f"""以下のプレゼンテーションスライドの内容に最適な画像を生成するための、詳細なプロンプトを作成してください。

スライドタイトル: {slide['title']}
スライド内容:
{slide['content']}

利用可能な登場人物:
{characters_info}

要件:
1. スライドの内容を視覚的に表現する具体的な画像を提案してください
2. 講師や指導者が必要な場合は、「塾頭高崎翔太」を優先的に使用してください（名前を明記）
3. 抽象的な背景ではなく、スライドの内容を具体的に表現する画像にしてください
4. 縦長（3:4）のアスペクト比に適した構図にしてください
5. 画像は教育・プレゼンテーション用途であることを意識してください
6. 【重要】画像内にテキスト、文字、看板、ラベル、タイトルなどは一切描画しないでください。AI画像生成では文字が崩れるため、純粋にビジュアル要素のみで構成してください
7. 人物を生成する場合は日本人を基本としてください

以下の形式で、画像生成プロンプトのみを出力してください（説明文は不要）:

[プロンプト内容]
登場人物: [使用する人物名、または「なし」]
"""

        try:
            response = self.model.generate_content(prompt)
            result = response.text.strip()

            # プロンプト部分と登場人物部分を分離
            lines = result.split('\n')
            character_line = ""
            prompt_lines = []

            for line in lines:
                if line.startswith('登場人物:'):
                    character_line = line.replace('登場人物:', '').strip()
                elif line.strip():
                    prompt_lines.append(line)

            image_prompt = '\n'.join(prompt_lines)

            return {
                'prompt': image_prompt,
                'character': character_line if character_line else 'なし'
            }

        except Exception as e:
            print(f"  ✗ Error generating prompt for slide {slide['number']}: {e}")
            return {
                'prompt': f"Professional abstract background for: {slide['title']}",
                'character': 'なし'
            }


def main():
    parser = argparse.ArgumentParser(
        description='Generate detailed image prompts for presentation slides with characters'
    )
    parser.add_argument('md_file', help='Path to markdown file')
    parser.add_argument(
        '--output', '-o',
        help='Output CSV file path',
        default=None
    )
    parser.add_argument(
        '--character-dir',
        help='Path to character directory',
        default='presentations/character'
    )

    args = parser.parse_args()

    # パス設定
    md_path = Path(args.md_file)
    if not md_path.exists():
        print(f"Error: Markdown file not found: {md_path}")
        sys.exit(1)

    # 出力パスの決定
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = md_path.parent / '画像プロンプト.csv'

    # キャラクターディレクトリ
    character_dir = Path(args.character_dir)
    if not character_dir.exists():
        print(f"Error: Character directory not found: {character_dir}")
        sys.exit(1)

    # APIキー取得
    api_key = os.environ.get('GOOGLE_AI_API_KEY')
    if not api_key:
        print("Error: GOOGLE_AI_API_KEY environment variable not set")
        sys.exit(1)

    print(f"Processing slides from: {md_path}")
    print(f"Output CSV: {output_path}")
    print(f"Character directory: {character_dir}")

    # キャラクターマネージャー初期化
    char_manager = CharacterManager(character_dir)
    print(f"Loaded {len(char_manager.characters)} characters")

    # スライド分析器初期化
    analyzer = SlideAnalyzer(md_path, api_key, char_manager)

    # スライド解析
    slides = analyzer.parse_slides()
    print(f"Found {len(slides)} slides\n")

    # プロンプト生成
    results = []
    for i, slide in enumerate(slides, 1):
        print(f"Slide {i}/{len(slides)}: {slide['title']}")
        result = analyzer.generate_image_prompt(slide)

        results.append({
            'slide_number': str(slide['number']).zfill(3),
            'title': slide['title'],
            'prompt': result['prompt'],
            'character': result['character'],
            'aspect_ratio': '3:4'
        })

        print(f"  ✓ Generated prompt")
        print(f"  Character: {result['character']}")

    # CSV出力
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        fieldnames = ['slide_number', 'title', 'prompt', 'character', 'aspect_ratio']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\n✓ Image prompts saved to: {output_path}")
    print(f"Total: {len(results)} prompts generated")


if __name__ == '__main__':
    main()
