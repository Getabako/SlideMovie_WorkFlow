# ステップ5: 動画結合

チャンクを結合して最終動画を作成するサブタスク

## 引数
$ARGUMENTS - プレゼンテーションのパスと出力先

## タスク
1. concat_list.txt を作成（チャンクファイル一覧）
2. FFmpegでチャンクを結合
3. 最終動画をデスクトップにコピー

## FFmpegコマンド
```bash
# concat_list.txt 作成
for f in presentations/[プレゼン名]/video_output/chunks/chunk_*.mp4; do
  echo "file '$f'" >> concat_list.txt
done

# 結合
ffmpeg -f concat -safe 0 -i concat_list.txt -c copy output.mp4
```

## 最終動画の配置
- デスクトップに `[プレゼン名].mp4` としてコピー
- 例: `/Users/takasaki19841121/Desktop/⑦ホームページ作り.mp4`

## 確認事項
1. 動画の冒頭を確認（スライド、キャラクター、字幕）
2. 動画の中盤を確認
3. 動画の終盤を確認
4. 音声が正しく再生されること

## 確認コマンド
```bash
ls -la /Users/takasaki19841121/Desktop/[プレゼン名].mp4
ffprobe -i output.mp4 2>&1 | grep Duration
```

## 完了報告
最終動画が完成したら、以下を報告:
- 動画ファイルパス
- 動画サイズ
- 動画の長さ
- 目視確認結果
