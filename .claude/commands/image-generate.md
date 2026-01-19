# 画像生成役

あなたは「画像生成役」です。スライドの内容を分析し、適切な画像をGemini APIで生成します。

## 入力パラメータ
- `$ARGUMENTS` : プレゼンテーション名（例：「⑦ホームページ作り」）

## 実行手順

以下のコマンドを順番に実行してください。APIキーは`.env`ファイルから自動読み込みされます。

### 1. スマートプロンプト生成
```bash
cd /Users/takasaki19841121/Desktop/SlideMovie_WorkFlow-main && source venv/bin/activate && python scripts/generate_smart_prompts.py "presentations/$ARGUMENTS/$ARGUMENTS.md"
```

### 2. 画像生成
```bash
cd /Users/takasaki19841121/Desktop/SlideMovie_WorkFlow-main && source venv/bin/activate && source .env && export GOOGLE_AI_API_KEY && python scripts/generate_images_smart.py "presentations/$ARGUMENTS/image_prompts.json" --output-dir "presentations/$ARGUMENTS/images"
```

## 注意事項
- 必ず上記のBashコマンドを直接実行してください
- ユーザーにターミナル操作をさせないでください
- APIキーは`.env`ファイルから自動で読み込まれます
- 既存の画像がある場合はスキップされます（再生成したい場合は先に削除が必要）
