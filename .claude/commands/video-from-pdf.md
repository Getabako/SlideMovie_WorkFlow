# PDF解説動画作成コマンド

PDFファイル（または結合済みPDF）から、キャラクターが解説する動画を作成します。

## 引数
- `$ARGUMENTS`: プレゼンテーション名（例: `子どもへのIT・AI教育`）

## 前提条件

事前に `/pdf-merge` コマンドでPDFを結合しておくことを推奨します：
```
/pdf-merge 子どもへのIT・AI教育
```

または、`merged.pdf` を手動で配置してください。

## 処理手順

1. **PDFファイルの確認**
   ```
   presentations/$ARGUMENTS/merged.pdf を優先
   なければ presentations/$ARGUMENTS/*.pdf を番号順に処理
   ```

2. **PDF内容の抽出**
   - PyMuPDFでページを画像化
   - **Gemini Vision API**でテキスト内容を読み取り
   - テキストが画像化されているスライドも正確に認識

3. **解説原稿の生成**
   - 各ページの内容から補足解説を生成
   - 講師「塾頭高崎翔太」が視聴者に語りかける形式
   - 30〜60秒/ページ程度の原稿

4. **動画作成スクリプトの実行**
   ```bash
   source venv/bin/activate
   export GOOGLE_AI_API_KEY="<APIキー>"
   python scripts/create_video_from_pdf.py \
     "presentations/$ARGUMENTS" \
     --voice-engine voicepeak \
     --narrator "Japanese Female 1" \
     --speed 150
   ```

## 出力ファイル

- 動画: `presentations/$ARGUMENTS/video_output/output.mp4`
- 原稿: `presentations/$ARGUMENTS/video_output/script.json`
- 音声: `presentations/$ARGUMENTS/video_output/audio/`
- スライド画像: `presentations/$ARGUMENTS/video_output/slides/`
- チャンク動画: `presentations/$ARGUMENTS/video_output/chunks/`

## 動画の特徴

- キャラクターが話している時: talk1.png〜talk6.png をループアニメーション
- キャラクターが待機中: idle1.png〜idle6.png をループアニメーション
- **PDFの内容に合わせた補足解説**（字幕付き）
- VOICEPEAKによる高品質日本語ナレーション
- スライドはフェードイン/アウトアニメーション付き

## PDF読み取りの仕組み

1. **テキスト抽出**: PyMuPDFでテキストを抽出
2. **Vision API**: テキストが少ない場合（画像化されている場合）、Gemini Vision APIで画像から内容を読み取り
3. **原稿生成**: 読み取った内容から解説原稿を自動生成

## 音声エンジンオプション

### VOICEPEAK（推奨）
- `--voice-engine voicepeak`: VOICEPEAKを使用（デフォルト）
- `--narrator "Japanese Female 1"`: ナレーター選択
  - 利用可能: Japanese Female 1/2/3, Japanese Male 1/2/3
- `--speed 150`: 話速（50-200、推奨150でハキハキ）
- `--pitch 0`: 声の高さ（-300〜300）

## その他のオプション

- `--skip-script`: 既存の原稿を再利用
- `--skip-audio`: 既存の音声を再利用
- `--fps 30`: フレームレートを指定（デフォルト: 30）

## 必要な環境変数

- `GOOGLE_AI_API_KEY`: Gemini API キー（PDF読み取り・原稿生成用）

## 必要なパッケージ

```bash
pip install PyMuPDF google-generativeai mutagen
```

## 使用例

### 基本的な流れ

```bash
# 1. PDFを結合
/pdf-merge 子どもへのIT・AI教育

# 2. 動画を作成
/video-from-pdf 子どもへのIT・AI教育
```

### 出力例

```
=== PDF解説動画作成 ===
入力: presentations/子どもへのIT・AI教育/

=== PDFファイル検出 ===
  merged.pdf を使用（45ページ）

=== ステップ1: PDF内容抽出 ===
  ページ 1/45: Vision APIで読み取り中...
  ページ 2/45: Vision APIで読み取り中...
  ...

=== ステップ2: 解説原稿生成 ===
  ページ 1: 完了（245文字）
  ...

=== ステップ3: 音声生成 ===
  VOICEPEAK: Japanese Female 1
  ...

完了!
出力動画: presentations/子どもへのIT・AI教育/video_output/output.mp4
```

## チャンク動画の結合

動画は5スライドずつチャンクに分けてレンダリングされ、最後にffmpegで結合されます。
もし結合が失敗した場合：

```bash
cd "presentations/$ARGUMENTS/video_output/chunks"
for i in chunk_*.mp4; do echo "file '$i'"; done > concat_list.txt
ffmpeg -f concat -safe 0 -i concat_list.txt -c copy "../output.mp4"
```
