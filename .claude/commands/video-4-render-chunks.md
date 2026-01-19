# ステップ4: チャンクレンダリング

Remotionでチャンク単位で動画をレンダリングするサブタスク

## 引数
$ARGUMENTS - プレゼンテーションのパス

## タスク
1. 総フレーム数からチャンク数を計算（3000フレーム/チャンク）
2. 各チャンクをRemotionでレンダリング
3. チャンクを `presentations/[プレゼン名]/video_output/chunks/` に保存

## レンダリングコマンド
```bash
cd remotion-project
npx remotion render Video [出力パス]/chunk_XXX.mp4 --frames [開始]-[終了] --concurrency 2
```

## 動画仕様（必須）
- フレームレート: 30fps
- 解像度: 1920x1080
- チャンクサイズ: 3000フレーム
- 背景: background.png（最背面、画面いっぱい）
- スライド背景色: 空色グラデーション

## 表示要素（zIndex順）
1. 背景画像 (zIndex: 0)
2. 空色グラデーション背景 (zIndex: 1)
3. スライド画像 (zIndex: 2)
4. キャラクター (zIndex: 3)
5. 字幕 (zIndex: 4)

## 確認コマンド
```bash
ls presentations/[プレゼン名]/video_output/chunks/chunk_*.mp4 | wc -l
```

## 完了報告
レンダリングが完了したら、以下を報告:
- レンダリングしたチャンク数
- 各チャンクのサイズ
