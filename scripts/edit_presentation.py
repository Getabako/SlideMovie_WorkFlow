#!/usr/bin/env python3
"""
プレゼンテーション編集スクリプト
Claude APIを使用して既存のプレゼンテーションを修正します
"""

import sys
import os
import yaml
from pathlib import Path


def edit_presentation_with_claude(input_file, edit_prompt):
    """
    Claude APIを使用してプレゼンテーションを編集

    Args:
        input_file: 既存のinput.ymlファイルのパス
        edit_prompt: 修正指示のプロンプト

    Returns:
        編集されたYAMLデータ
    """
    # 既存のYAMLファイルを読み込む
    with open(input_file, 'r', encoding='utf-8') as f:
        current_data = yaml.safe_load(f)
        current_yaml_text = yaml.dump(current_data, allow_unicode=True, sort_keys=False)

    # Anthropic APIキーを取得
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("警告: ANTHROPIC_API_KEYが設定されていません。Google AI APIを試します...")
        return edit_presentation_with_google_ai(current_data, edit_prompt)

    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=api_key)

        # Claude APIを呼び出してYAMLを編集
        system_prompt = """あなたはプレゼンテーション編集のエキスパートです。
ユーザーの指示に従って、既存のプレゼンテーションYAMLファイルを修正してください。

重要な制約：
1. 必ずYAML形式で出力してください
2. 既存の構造（topic, slides配列）を維持してください
3. 各スライドはtitleとcontentを持つ必要があります
4. 指示に従って、スライドの追加、削除、修正、並び替えを行ってください
5. 修正後のYAMLのみを出力し、説明文は不要です
6. YAMLブロックの前後に```yamlや```などのマークダウン記法を使わないでください
"""

        user_prompt = f"""現在のプレゼンテーション:

```yaml
{current_yaml_text}
```

修正指示:
{edit_prompt}

上記の指示に従って、プレゼンテーションYAMLを修正してください。
修正後のYAMLのみを出力してください（コードブロックやマークダウン記法は不要）。"""

        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=8000,
            temperature=0.7,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )

        # レスポンスからYAMLテキストを抽出
        edited_yaml_text = message.content[0].text.strip()

        # マークダウンコードブロックを除去（念のため）
        if edited_yaml_text.startswith('```yaml'):
            edited_yaml_text = edited_yaml_text.split('```yaml', 1)[1]
        if edited_yaml_text.startswith('```'):
            edited_yaml_text = edited_yaml_text.split('```', 1)[1]
        if edited_yaml_text.endswith('```'):
            edited_yaml_text = edited_yaml_text.rsplit('```', 1)[0]

        edited_yaml_text = edited_yaml_text.strip()

        # YAMLをパースして検証
        edited_data = yaml.safe_load(edited_yaml_text)

        # 基本的な構造を検証
        if 'topic' not in edited_data:
            raise ValueError("編集後のYAMLに'topic'フィールドがありません")
        if 'slides' not in edited_data:
            raise ValueError("編集後のYAMLに'slides'フィールドがありません")
        if not isinstance(edited_data['slides'], list):
            raise ValueError("'slides'はリスト形式である必要があります")

        print(f"✓ Claude APIによる編集が完了しました")
        print(f"  - トピック: {edited_data['topic']}")
        print(f"  - スライド数: {len(edited_data['slides'])} (元: {len(current_data['slides'])})")

        return edited_data

    except Exception as e:
        print(f"エラー: Claude APIでの編集に失敗しました: {e}")
        print("Google AI APIにフォールバックします...")
        return edit_presentation_with_google_ai(current_data, edit_prompt)


def edit_presentation_with_google_ai(current_data, edit_prompt):
    """
    Google AI APIを使用してプレゼンテーションを編集（フォールバック）

    Args:
        current_data: 現在のYAMLデータ
        edit_prompt: 修正指示のプロンプト

    Returns:
        編集されたYAMLデータ
    """
    api_key = os.environ.get('GOOGLE_AI_API_KEY')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEYまたはGOOGLE_AI_API_KEYのいずれかが必要です")

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')

        current_yaml_text = yaml.dump(current_data, allow_unicode=True, sort_keys=False)

        prompt = f"""あなたはプレゼンテーション編集のエキスパートです。
以下のYAML形式のプレゼンテーションを、指示に従って修正してください。

現在のプレゼンテーション:
```yaml
{current_yaml_text}
```

修正指示:
{edit_prompt}

重要な制約:
1. 必ずYAML形式で出力してください
2. 既存の構造（topic, slides配列）を維持してください
3. 各スライドはtitleとcontentを持つ必要があります
4. 修正後のYAMLのみを出力し、説明文は不要です
5. YAMLブロックの前後に```yamlや```などのマークダウン記法を使わないでください

修正後のYAMLを出力してください:"""

        response = model.generate_content(prompt)
        edited_yaml_text = response.text.strip()

        # マークダウンコードブロックを除去
        if edited_yaml_text.startswith('```yaml'):
            edited_yaml_text = edited_yaml_text.split('```yaml', 1)[1]
        if edited_yaml_text.startswith('```'):
            edited_yaml_text = edited_yaml_text.split('```', 1)[1]
        if edited_yaml_text.endswith('```'):
            edited_yaml_text = edited_yaml_text.rsplit('```', 1)[0]

        edited_yaml_text = edited_yaml_text.strip()

        # YAMLをパース
        edited_data = yaml.safe_load(edited_yaml_text)

        # 基本的な構造を検証
        if 'topic' not in edited_data:
            raise ValueError("編集後のYAMLに'topic'フィールドがありません")
        if 'slides' not in edited_data:
            raise ValueError("編集後のYAMLに'slides'フィールドがありません")

        print(f"✓ Google AI APIによる編集が完了しました")
        print(f"  - トピック: {edited_data['topic']}")
        print(f"  - スライド数: {len(edited_data['slides'])} (元: {len(current_data['slides'])})")

        return edited_data

    except Exception as e:
        raise RuntimeError(f"Google AI APIでの編集に失敗しました: {e}")


def main():
    if len(sys.argv) < 3:
        print("使用方法: python edit_presentation.py <input_yaml_file> <edit_prompt>")
        sys.exit(1)

    input_file = sys.argv[1]
    edit_prompt = sys.argv[2]

    if not os.path.exists(input_file):
        print(f"エラー: 入力ファイルが見つかりません: {input_file}")
        sys.exit(1)

    print(f"プレゼンテーションを編集中: {input_file}")
    print(f"修正指示: {edit_prompt}")
    print("-" * 60)

    # プレゼンテーションを編集
    edited_data = edit_presentation_with_claude(input_file, edit_prompt)

    # 編集したYAMLを元のファイルに上書き保存
    with open(input_file, 'w', encoding='utf-8') as f:
        yaml.dump(edited_data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

    print("-" * 60)
    print(f"✓ プレゼンテーションを更新しました: {input_file}")
    print(f"  - トピック: {edited_data['topic']}")
    print(f"  - スライド数: {len(edited_data['slides'])}")


if __name__ == "__main__":
    main()
