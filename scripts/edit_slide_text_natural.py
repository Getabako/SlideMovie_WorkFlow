#!/usr/bin/env python3
"""
自然言語の指示に基づいてスライドのテキストを編集するスクリプト
"""

import yaml
import sys
import os
import json
import subprocess
import shutil
from pathlib import Path
import google.generativeai as genai

def parse_edit_instructions(yaml_content: str, edit_instructions: str) -> list:
    """
    自然言語の編集指示を解析する

    Args:
        yaml_content: YAMLファイルの内容
        edit_instructions: ユーザーの編集指示

    Returns:
        編集内容のリスト
    """

    api_key = os.getenv('GOOGLE_AI_API_KEY')
    if not api_key:
        raise ValueError("GOOGLE_AI_API_KEY環境変数が設定されていません")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        'gemini-2.5-flash',
        generation_config=genai.GenerationConfig(
            temperature=0.1,
            response_mime_type="application/json",
        )
    )

    prompt = f"""以下のプレゼンテーションに対して、ユーザーの編集指示を解析してください。

プレゼンテーションの現在の内容:
```yaml
{yaml_content}
```

編集指示:
{edit_instructions}

上記の編集指示に基づいて、どのスライドのどの部分をどのように変更するかを解析し、以下の形式のJSONで応答してください。
編集指示に複数のスライドの変更が含まれる場合は、すべての変更をリストに含めてください。

JSONスキーマ:
{{
  "edits": [
    {{
      "slide_number": (整数),
      "edit_type": "(string: title/content/both/delete)",
      "new_title": "(string, オプション)",
      "new_content": "(string, オプション)",
      "reasoning": "(string)"
    }}
  ]
}}

重要な注意事項：
1. slide_number は 1 から始まる整数です
2. edit_type は "title"（タイトルのみ変更）、"content"（本文のみ変更）、"both"（両方変更）、"delete"（スライド削除）のいずれかです
3. スライドを削除する場合は、edit_type を "delete" にして、new_title と new_content は省略してください
4. テキストの一部を削除する場合は、削除後の完全なテキストを new_content に入れてください
5. 箇条書きを1つの文にまとめる場合は、箇条書きを解除して通常の文章にしてください
6. 「テキストエリアの横幅を伸ばす」などのレイアウト変更は、テキスト編集では対応できないため無視してください
"""

    response = model.generate_content(prompt)
    response_text = response.text.strip()

    # JSONブロックを抽出（マークダウンのコードブロックがある場合）
    if '```json' in response_text:
        response_text = response_text.split('```json')[1].split('```')[0].strip()
    elif '```' in response_text:
        response_text = response_text.split('```')[1].split('```')[0].strip()

    # JSONコメントを削除 (// ... 形式)
    import re
    response_text = re.sub(r'//.*$', '', response_text, flags=re.MULTILINE)

    try:
        result = json.loads(response_text)
        return result.get('edits', [])
    except json.JSONDecodeError as e:
        print(f"エラー: AIの応答をJSON形式で解析できませんでした: {e}")
        print(f"応答内容: {response_text[:1000]}...")

        # デバッグ用にファイルに保存
        with open('/tmp/gemini_response.json', 'w', encoding='utf-8') as f:
            f.write(response_text)
        print("完全な応答を /tmp/gemini_response.json に保存しました")

        # 制御文字の修正を試みる
        print("\n制御文字の修正を試みています...")
        try:
            # 不正な制御文字を修正
            fixed_text = response_text.encode('utf-8').decode('unicode_escape').encode('latin1').decode('utf-8')
            result = json.loads(fixed_text)
            print("✓ 修正に成功しました")
            return result.get('edits', [])
        except Exception as e2:
            print(f"修正も失敗しました: {e2}")

            # JSONを行単位で解析して部分的に復元を試みる
            print("\n部分的な復元を試みています...")
            try:
                # 簡易的なJSON修正: 不完全な文字列を削除
                lines = response_text.split('\n')
                fixed_lines = []
                for line in lines:
                    # 不完全な文字列を検出して修正
                    if line.strip().endswith('"') and line.count('"') % 2 == 0:
                        fixed_lines.append(line)
                    elif '":' in line:
                        fixed_lines.append(line)
                    elif line.strip() in ['{', '}', '[', ']', ',']:
                        fixed_lines.append(line)

                fixed_text = '\n'.join(fixed_lines)
                result = json.loads(fixed_text)
                print("✓ 部分的な復元に成功しました")
                return result.get('edits', [])
            except Exception as e3:
                print(f"部分的な復元も失敗しました: {e3}")
                print("\n複雑すぎる編集指示のため、処理を分割することをお勧めします。")
                print("編集指示を少数のスライドに分けて実行してください。")
                sys.exit(1)


def apply_edits(yaml_path: str, edits: list):
    """
    解析された編集内容を適用する

    Args:
        yaml_path: YAMLファイルのパス
        edits: 編集内容のリスト
    """

    # YAMLファイルを読み込む
    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    # 削除するスライド番号を収集（降順でソート）
    slides_to_delete = []

    # 各編集を適用
    for edit in edits:
        slide_number = edit['slide_number']
        edit_type = edit['edit_type']

        # スライド番号の検証
        if slide_number < 1 or slide_number > len(data['slides']):
            print(f"警告: スライド番号 {slide_number} は範囲外です（1-{len(data['slides'])}）。スキップします。")
            continue

        slide_index = slide_number - 1

        # スライド削除
        if edit_type == 'delete':
            slides_to_delete.append(slide_number)
            print(f"✓ スライド{slide_number}を削除対象にマークしました")
            if 'reasoning' in edit:
                print(f"  理由: {edit['reasoning']}")
            print()
            continue

        # タイトルを変更
        if edit_type in ['title', 'both'] and 'new_title' in edit:
            old_title = data['slides'][slide_index]['title']
            data['slides'][slide_index]['title'] = edit['new_title']
            print(f"✓ スライド{slide_number}のタイトルを更新しました")
            print(f"  変更前: {old_title}")
            print(f"  変更後: {edit['new_title']}")

        # 本文を変更
        if edit_type in ['content', 'both'] and 'new_content' in edit:
            old_content = data['slides'][slide_index]['content']
            data['slides'][slide_index]['content'] = edit['new_content']
            print(f"✓ スライド{slide_number}の本文を更新しました")
            if len(old_content) < 100:
                print(f"  変更前: {old_content}")
            else:
                print(f"  変更前: {old_content[:100]}...")
            if len(edit['new_content']) < 100:
                print(f"  変更後: {edit['new_content']}")
            else:
                print(f"  変更後: {edit['new_content'][:100]}...")

        # 理由を表示
        if 'reasoning' in edit:
            print(f"  理由: {edit['reasoning']}")
        print()

    # スライドを削除（番号の大きい順に削除してインデックスのずれを防ぐ）
    if slides_to_delete:
        slides_to_delete.sort(reverse=True)
        for slide_num in slides_to_delete:
            del data['slides'][slide_num - 1]
            print(f"✓ スライド{slide_num}を削除しました")

    # YAMLファイルに書き込む
    with open(yaml_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    print(f"\n✓ {len(edits)}件の編集を {yaml_path} に適用しました")

    return data  # 編集後のデータを返す


def generate_and_update_markdown(yaml_path: str, topic: str):
    """
    input.ymlからMarkdownファイルを生成し、presentationsフォルダに配置する

    Args:
        yaml_path: YAMLファイルのパス
        topic: プレゼンテーションのトピック名
    """
    script_dir = Path(__file__).parent

    # create_slide.pyを実行
    create_slide_script = script_dir / "create_slide.py"

    print("\nMarkdownファイルを生成中...")
    try:
        # create_slide.pyを実行してMarkdownファイルを生成
        result = subprocess.run(
            [sys.executable, str(create_slide_script), yaml_path],
            capture_output=True,
            text=True,
            check=True
        )

        if result.stdout:
            print(result.stdout.strip())
    except subprocess.CalledProcessError as e:
        print(f"エラー: Markdownファイルの生成に失敗しました: {e}")
        if e.stderr:
            print(f"エラー出力: {e.stderr}")
        return

    # 生成されたMarkdownファイルのパスを取得
    safe_topic = topic.replace(' ', '_').replace('/', '_').replace('\\', '_')
    slides_dir = script_dir.parent / "slides"
    generated_md = slides_dir / f"{safe_topic}_slide.md"

    if not generated_md.exists():
        print(f"エラー: 生成されたMarkdownファイル {generated_md} が見つかりません")
        return

    # presentationsフォルダの適切な場所にコピー
    presentation_dir = Path(yaml_path).parent

    # 元のMarkdownファイル名を決定（優先順位で確認）
    original_md = None
    possible_names = [
        f"{topic}.md",
        f"{topic}_slide.md",
        f"{topic}_slide_with_images.md"
    ]

    for name in possible_names:
        candidate = presentation_dir / name
        if candidate.exists():
            original_md = candidate
            break

    if not original_md:
        # 元のファイルが見つからない場合は新規作成
        original_md = presentation_dir / f"{topic}.md"

    # バックアップを作成
    if original_md.exists():
        backup_path = original_md.with_suffix('.md.backup')
        shutil.copy2(original_md, backup_path)
        print(f"✓ バックアップを作成: {backup_path}")

    # 生成されたMarkdownファイルをコピー
    shutil.copy2(generated_md, original_md)
    print(f"✓ Markdownファイルを更新: {original_md}")

    # _slide.mdも更新（存在する場合）
    slide_md = presentation_dir / f"{topic}_slide.md"
    if slide_md.exists() and slide_md != original_md:
        shutil.copy2(generated_md, slide_md)
        print(f"✓ {topic}_slide.md も更新しました")


def main():
    if len(sys.argv) < 3:
        print("使用方法:")
        print("  python edit_slide_text_natural.py <yaml_path> <edit_instructions>")
        print("\n例:")
        print("  python edit_slide_text_natural.py presentations/①すごいぞAI_AI概論/input.yml 'スライド8の構成要素を大きく、目立つ、短く、簡潔にして'")
        sys.exit(1)

    yaml_path = sys.argv[1]
    edit_instructions = sys.argv[2]

    if not os.path.exists(yaml_path):
        print(f"エラー: {yaml_path} が見つかりません")
        sys.exit(1)

    # YAMLファイルを読み込む
    with open(yaml_path, 'r', encoding='utf-8') as f:
        yaml_content = f.read()

    print("編集指示を解析中...")
    print(f"指示: {edit_instructions}\n")

    # 編集内容を解析
    edits = parse_edit_instructions(yaml_content, edit_instructions)

    if not edits:
        print("エラー: 編集内容を解析できませんでした")
        sys.exit(1)

    print(f"{len(edits)}件の編集を検出しました\n")

    # 編集を適用
    edited_data = apply_edits(yaml_path, edits)

    # トピック名を取得
    topic = edited_data.get('topic', 'presentation')

    # Markdownファイルを生成して元のファイルを更新
    generate_and_update_markdown(yaml_path, topic)


if __name__ == "__main__":
    main()
