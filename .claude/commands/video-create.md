# キャラクター付き動画作成コマンド

指定されたプレゼンテーションからキャラクター付き動画を作成します。

## 引数
- `$ARGUMENTS`: プレゼンテーション名（例: `⑦ホームページ作り`）

## 処理手順

1. **プレゼンテーションの確認**
   - `presentations/$ARGUMENTS/` ディレクトリを確認
   - マークダウンファイル（`$ARGUMENTS.md`）を確認

2. **依存パッケージの確認**
   - VOICEPEAK: 音声生成用（推奨、商用可能6ナレーターセット）
   - mutagen: 音声長さ取得用（オプション）
   - Remotion: 動画レンダリング用
   - ffmpeg: 動画結合・音声変換用

3. **動画作成スクリプトの実行**
   ```bash
   source venv/bin/activate
   export GOOGLE_AI_API_KEY="<APIキー>"
   python scripts/create_video_with_character.py \
     "presentations/$ARGUMENTS/$ARGUMENTS.md" \
     --voice-engine voicepeak \
     --narrator "Japanese Female 1" \
     --speed 150
   ```

4. **出力ファイル**
   - 動画: `presentations/$ARGUMENTS/video_output/$ARGUMENTS.mp4`
   - 原稿: `presentations/$ARGUMENTS/video_output/script.json`
   - 音声: `presentations/$ARGUMENTS/video_output/audio/`
   - スライド画像: `presentations/$ARGUMENTS/video_output/slides/`
   - チャンク動画: `presentations/$ARGUMENTS/video_output/chunks/`

## 動画の特徴
- キャラクターが話している時: talk1.png〜talk6.png をループアニメーション
- キャラクターが待機中: idle1.png〜idle6.png をループアニメーション
- スライド内容に合わせた自動字幕（文字数比例でタイミング配分）
- VOICEPEAKによる高品質日本語ナレーション
- スライドはフェードイン/アウトアニメーション付き

### 重要: 音声と字幕の同期

字幕タイミングは**文字数に比例して**配分されます。これにより、音声合成の読み上げ速度と字幕表示が同期します。

- 長い文 → 長い表示時間
- 短い文 → 短い表示時間

**注意**: 均等割りは使用しないでください。音声とズレます。

## 音声エンジンオプション

### VOICEPEAK（推奨）
- `--voice-engine voicepeak`: VOICEPEAKを使用（デフォルト）
- `--narrator "Japanese Female 1"`: ナレーター選択
  - 利用可能: Japanese Female 1/2/3, Japanese Male 1/2/3
- `--speed 150`: 話速（50-200、推奨150でハキハキ）
- `--pitch 0`: 声の高さ（-300〜300）

**注意**: VOICEPEAKは1回のリクエストで140文字まで。長い原稿は自動的に句点で分割し、複数の音声を生成して結合します。

### その他のエンジン（フォールバック用）
- `--voice-engine gtts`: Google Text-to-Speech
- `--voice-engine edge_tts`: Microsoft Edge TTS

## その他のオプション
- `--skip-script`: 既存の原稿を再利用
- `--skip-audio`: 既存の音声を再利用
- `--fps 30`: フレームレートを指定（デフォルト: 30）

## 必要な環境変数
- `GOOGLE_AI_API_KEY`: Gemini API キー（原稿生成用）

## チャンク動画の結合

動画は5スライドずつチャンクに分けてレンダリングされ、最後にffmpegで結合されます。
もし結合が失敗した場合は、以下のコマンドで手動結合できます：

```bash
cd "presentations/$ARGUMENTS/video_output/chunks"
# concat_list.txtを作成
for i in chunk_*.mp4; do echo "file '$i'"; done > concat_list.txt
# ffmpegで結合
ffmpeg -f concat -safe 0 -i concat_list.txt -c copy "../$ARGUMENTS.mp4"
```
