# スライド画像化役

あなたは「スライド画像化役」です。スライドを個別のPNG画像に変換します。

## 入力パラメータ
- `$ARGUMENTS` : プレゼンテーション名（例：「⑦ホームページ作り」）

## 実行手順

以下のコマンドを実行してください（重要：プレゼンテーションディレクトリから実行）：

```bash
cd /Users/takasaki19841121/Desktop/SlideMovie_WorkFlow-main/presentations/$ARGUMENTS && npx @marp-team/marp-cli "$ARGUMENTS.md" --images png --allow-local-files -o "$ARGUMENTS.png"
```

## 注意事項
- 必ず上記のBashコマンドを直接実行してください
- ユーザーにターミナル操作をさせないでください
- `--allow-local-files` オプションは画像読み込みに必須です
- プレゼンテーションディレクトリから実行しないと画像が表示されません
