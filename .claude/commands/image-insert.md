# 画像貼り付け役

あなたは「画像貼り付け役」です。生成された画像をスライドに挿入します。

## 入力パラメータ
- `$ARGUMENTS` : プレゼンテーション名（例：「⑦ホームページ作り」）

## 実行手順

以下のコマンドを実行してください：

```bash
cd /Users/takasaki19841121/Desktop/SlideMovie_WorkFlow-main && source venv/bin/activate && python scripts/insert_images_to_slides.py "presentations/$ARGUMENTS/$ARGUMENTS.md" --images-dir "presentations/$ARGUMENTS/images"
```

## 注意事項
- 必ず上記のBashコマンドを直接実行してください
- ユーザーにターミナル操作をさせないでください
- 画像が既に挿入されているスライドはスキップされます
