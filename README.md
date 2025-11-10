# ゆっくり動画風プレゼンテーション自動生成システム

このリポジトリは、YAMLファイルからゆっくり動画風のプレゼンテーション動画を自動生成するシステムです。GitHub Actions上で完全に動作します。

## 特徴

- **完全自動化**: YAMLファイルを作成してプッシュするだけで動画が生成されます
- **AI原稿生成**: Gemini 2.0 Flash が自然な原稿を自動生成
- **音声合成**: Edge TTS による高品質な日本語音声
- **字幕自動生成**: 音声に合わせた字幕を自動生成
- **キャラクターアニメーション**: 喋っている時と待機時で異なるアニメーション
  - 喋っている時: talk1~talk6 を循環再生
  - 待機時: idle1~idle6 を循環再生
- **GitHub Actions統合**: クラウド上で完全に動作

## ワークフロー

```
YAML入力 → スライド生成 → 原稿生成 → 音声生成 → タイミング計算 → 動画レンダリング
```

1. **スライド生成**: YAMLからMarp形式のMarkdownスライドを生成
2. **原稿生成**: Gemini APIでスライド内容から自然な原稿を生成
3. **音声生成**: Edge TTSで音声ファイルを生成
4. **タイミング計算**: 音声の長さから字幕のタイミングを計算
5. **動画レンダリング**: Remotionでキャラクターアニメーション付き動画を生成

## セットアップ

### 1. 必要なシークレットの設定

GitHub リポジトリの Settings > Secrets and variables > Actions で以下を設定:

- `GOOGLE_AI_API_KEY`: Google AI Studio で取得したAPIキー
  - https://aistudio.google.com/apikey

### 2. リポジトリのクローン

```bash
git clone <your-repo-url>
cd <repo-name>
```

## 使用方法

### 方法1: 手動実行

1. GitHub リポジトリの「Actions」タブを開く
2. 「Create Yukkuri Video」ワークフローを選択
3. 「Run workflow」をクリック
4. 入力YAMLファイルのパスを指定（例: `inputs/ai_industry_trends_2025.yml`）
5. 「Run workflow」を実行

### 方法2: 自動実行（プッシュトリガー）

`inputs/` ディレクトリにYAMLファイルをコミット・プッシュすると自動実行されます:

```bash
# 新しいプレゼンテーション用のYAMLファイルを作成
cp inputs/ai_industry_trends_2025.yml inputs/my_presentation.yml

# 内容を編集
vi inputs/my_presentation.yml

# コミット＆プッシュ
git add inputs/my_presentation.yml
git commit -m "Add new presentation"
git push
```

## 入力YAMLファイルの形式

```yaml
topic: "プレゼンテーションのタイトル"

slides:
  - title: "スライド1のタイトル"
    content: |
      スライド1の内容

      - 箇条書き1
      - 箇条書き2

  - title: "スライド2のタイトル"
    content: |
      ## セクション

      スライド2の内容
```

### サンプル

`inputs/ai_industry_trends_2025.yml` にAI業界の動向についての10枚のスライドサンプルがあります。

## 生成される成果物

ワークフロー実行後、以下がArtifactsからダウンロード可能:

1. **動画ファイル**: `yukkuri-video-<トピック名>`
   - 最終的な動画ファイル (MP4形式)

2. **全出力ファイル**: `all-outputs-<トピック名>`
   - スライド (Markdown)
   - 原稿 (JSON, TXT)
   - 音声ファイル (MP3)
   - タイミング情報 (JSON)

## ディレクトリ構造

```
.
├── .github/
│   └── workflows/
│       ├── create-yukkuri-video.yml  # 動画生成ワークフロー
│       └── remotion-render.yml        # Remotionレンダリング（旧）
├── inputs/                            # 入力YAMLファイル
│   └── ai_industry_trends_2025.yml    # サンプル入力
├── scripts/                           # 処理スクリプト
│   ├── create_slide.py                # スライド生成
│   ├── generate_script.py             # 原稿生成
│   ├── generate_audio.py              # 音声生成
│   ├── generate_timings.py            # タイミング計算
│   └── create_video.py                # メインオーケストレーション
├── remotion-project/                  # Remotionプロジェクト
│   ├── src/
│   │   ├── Video.tsx                  # メインビデオコンポーネント
│   │   └── Root.tsx                   # Remotionルート
│   └── public/                        # 画像・音声ファイル
│       ├── idle1.png ~ idle6.png      # 待機アニメーション
│       └── talk1.png ~ talk6.png      # 会話アニメーション
├── PresentationWorkFlow/              # 従来のプレゼンテーション生成
└── requirements.txt                   # Python依存パッケージ
```

## カスタマイズ

### キャラクター画像の変更

`remotion-project/public/` ディレクトリの以下の画像を差し替えてください:

- `idle1.png` ~ `idle6.png`: 待機時のアニメーション（6フレーム）
- `talk1.png` ~ `talk6.png`: 会話時のアニメーション（6フレーム）

### 音声の変更

`scripts/generate_audio.py` の `voice` パラメータを変更:

```python
voice='ja-JP-NanamiNeural'  # デフォルト（女性）
voice='ja-JP-KeitaNeural'   # 男性
```

利用可能な音声: https://learn.microsoft.com/ja-jp/azure/ai-services/speech-service/language-support

### アニメーション速度の変更

`remotion-project/src/Video.tsx` の以下の行を変更:

```typescript
const imageIndex = Math.floor(frame / 5) % images.length;
```

`/ 5` の数値を変更（小さくすると速く、大きくすると遅くなります）

### 動画の解像度・フレームレート

`remotion-project/src/Root.tsx` で変更:

```typescript
fps={30}          // フレームレート
width={1920}      // 幅
height={1080}     // 高さ
```

## ローカルでの実行

```bash
# Python依存パッケージのインストール
pip install -r requirements.txt

# 環境変数の設定
export GOOGLE_AI_API_KEY="your-api-key"

# 動画生成
python3 scripts/create_video.py inputs/ai_industry_trends_2025.yml

# 生成された動画
# remotion-project/out/video.mp4
```

## トラブルシューティング

### APIキーエラー

```
エラー: GOOGLE_AI_API_KEY環境変数が設定されていません
```

→ GitHub Secretsに `GOOGLE_AI_API_KEY` を正しく設定してください

### 音声生成エラー

```
エラー: 音声の生成に失敗しました
```

→ Edge TTSの接続を確認してください（通常は自動的にリトライされます）

### Remotionレンダリングエラー

```
エラー: Could not find the browser executable
```

→ GitHub Actionsでは自動的にブラウザがインストールされます
→ ローカルでは `npx remotion browser ensure` を実行してください

### タイムアウトエラー

長い動画（10スライド以上）の場合、GitHub Actionsのタイムアウト（60分）に達する可能性があります。
必要に応じて `.github/workflows/create-yukkuri-video.yml` の `timeout-minutes` を調整してください。

## ライセンス

MIT License

## 貢献

プルリクエストやイシューの報告を歓迎します。

## 参考リンク

- [Remotion](https://www.remotion.dev/) - React ベースの動画生成フレームワーク
- [Marp](https://marp.app/) - Markdown Presentation Ecosystem
- [Google Gemini API](https://ai.google.dev/) - AI原稿生成
- [Edge TTS](https://github.com/rany2/edge-tts) - Microsoft Edge の音声合成