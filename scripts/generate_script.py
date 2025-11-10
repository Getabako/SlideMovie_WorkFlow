#!/usr/bin/env python3
"""
スライドから原稿を生成するスクリプト
Gemini APIを使用してスライドの内容から自然な原稿を生成します
"""

import sys
import os
import json
from pathlib import Path
import google.generativeai as genai

def parse_marp_slides(slide_file):
    """
    Marp形式のMarkdownスライドを解析してスライドごとに分割

    Args:
        slide_file: スライドファイルのパス

    Returns:
        スライドのリスト（各スライドは辞書形式）
    """
    with open(slide_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # スライドを分割（---で区切られている）
    slides_raw = content.split('---')

    slides = []
    for i, slide_raw in enumerate(slides_raw):
        slide_raw = slide_raw.strip()
        if not slide_raw or slide_raw.startswith('marp:'):
            continue

        # タイトルと内容を抽出
        lines = slide_raw.split('\n')
        title = ''
        content_lines = []

        for line in lines:
            if line.startswith('# '):
                title = line[2:].strip()
            elif line.strip():
                content_lines.append(line)

        slides.append({
            'index': len(slides) + 1,
            'title': title,
            'content': '\n'.join(content_lines)
        })

    return slides

def generate_script_for_slide(model, slide, total_slides):
    """
    1枚のスライドに対する原稿を生成

    Args:
        model: Gemini モデル
        slide: スライド情報（辞書）
        total_slides: 総スライド数

    Returns:
        生成された原稿テキスト
    """
    prompt = f"""
あなたはプレゼンテーションの原稿を作成する専門家です。
以下のスライド情報から、自然で分かりやすい原稿を日本語で作成してください。

スライド番号: {slide['index']} / {total_slides}
タイトル: {slide['title']}
内容:
{slide['content']}

要件:
1. 自然な話し言葉で書いてください
2. 1スライドあたり30〜60秒程度の長さにしてください
3. 箇条書きは自然な文章に変換してください
4. 聞き手に語りかけるような口調にしてください
5. 「えー」「あのー」などの言葉は入れないでください
6. スライド番号や「このスライドでは」などの言及は避けてください

原稿のみを出力してください（説明や補足は不要です）。
"""

    response = model.generate_content(prompt)
    return response.text.strip()

def generate_full_script(slide_file, output_file):
    """
    スライドファイル全体の原稿を生成

    Args:
        slide_file: スライドファイルのパス
        output_file: 出力ファイルのパス
    """
    # APIキーの確認
    api_key = os.environ.get('GOOGLE_AI_API_KEY')
    if not api_key:
        raise ValueError("GOOGLE_AI_API_KEY環境変数が設定されていません")

    # Gemini APIの初期化
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash-exp')

    # スライドを解析
    print(f"スライドを解析中: {slide_file}")
    slides = parse_marp_slides(slide_file)
    print(f"スライド数: {len(slides)}")

    # 各スライドの原稿を生成
    scripts = []
    for slide in slides:
        print(f"原稿生成中: スライド {slide['index']} - {slide['title']}")
        script = generate_script_for_slide(model, slide, len(slides))

        scripts.append({
            'index': slide['index'],
            'title': slide['title'],
            'script': script
        })

        print(f"  生成完了: {len(script)}文字")

    # JSONとして保存
    output_data = {
        'slides': scripts,
        'total_slides': len(slides)
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"\n原稿を保存しました: {output_file}")

    # テキスト版も保存
    text_output = str(output_file).replace('.json', '.txt')
    with open(text_output, 'w', encoding='utf-8') as f:
        for script in scripts:
            f.write(f"=== スライド {script['index']}: {script['title']} ===\n\n")
            f.write(script['script'])
            f.write("\n\n")

    print(f"テキスト版も保存しました: {text_output}")

    return output_file

def main():
    if len(sys.argv) < 2:
        print("使用方法: python generate_script.py <slide_file>")
        sys.exit(1)

    slide_file = sys.argv[1]

    if not os.path.exists(slide_file):
        print(f"エラー: スライドファイルが見つかりません: {slide_file}")
        sys.exit(1)

    # 出力ディレクトリとファイル名
    slide_path = Path(slide_file)
    output_dir = slide_path.parent.parent / "scripts_output"
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / f"{slide_path.stem}_script.json"

    # 原稿を生成
    script_file = generate_full_script(slide_file, output_file)

    # GitHub Actions用に環境変数に保存
    if 'GITHUB_ENV' in os.environ:
        with open(os.environ['GITHUB_ENV'], 'a') as f:
            f.write(f"SCRIPT_FILE={script_file}\n")

if __name__ == "__main__":
    main()
