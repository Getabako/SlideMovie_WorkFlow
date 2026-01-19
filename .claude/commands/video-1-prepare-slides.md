# ステップ1: スライド準備

プレゼンテーションのスライド画像を準備するサブタスク

## 引数
$ARGUMENTS - プレゼンテーションのMarkdownファイルパス (例: presentations/⑦ホームページ作り/⑦ホームページ作り.md)

## タスク
1. プレゼンテーションフォルダ内のスライド画像（.XXX.png形式）を確認
2. スライド画像を `remotion-project/public/slides/` にコピー
   - ファイル名を `slide_01.png`, `slide_02.png` 形式に変換
3. `remotion-project/slides_metadata.json` のスライド数を更新

## 重要な注意事項
- test_output.XXX.png ではなく、プレゼンテーション名.XXX.png を使用すること
- 画像のコピー後、正しいスライドがコピーされたことを確認すること
- slides_metadata.json の total_slides が正確であること

## 確認コマンド
```bash
ls remotion-project/public/slides/
cat remotion-project/slides_metadata.json
```

## 完了報告
スライド準備が完了したら、以下を報告:
- コピーしたスライド数
- slides_metadata.json の内容
