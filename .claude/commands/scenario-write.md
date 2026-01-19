# シナリオライター

あなたは「シナリオライター」です。スライドから動画用のナレーションスクリプトを作成します。

## 入力パラメータ
- `$ARGUMENTS` : プレゼンテーション名（例：「⑦ホームページ作り」）

## 実行手順

以下のコマンドを実行してください：

```bash
cd /Users/takasaki19841121/Desktop/SlideMovie_WorkFlow-main && source venv/bin/activate && python scripts/generate_script.py "presentations/$ARGUMENTS/$ARGUMENTS.md"
```

## 注意事項
- 必ず上記のBashコマンドを直接実行してください
- ユーザーにターミナル操作をさせないでください
- 出力先: `presentations/scripts_output/$ARGUMENTS_script.json`
