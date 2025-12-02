# ゆっくり動画風プレゼンテーション自動生成システム

このリポジトリは、YAMLファイルからAI画像付きプレゼンテーションとゆっくり動画風の動画を自動生成する2段階のワークフローシステムです。GitHub Actions上で完全に動作します。

## 特徴

- **2段階ワークフロー**: プレゼンテーション生成 → 動画生成
- **AI画像生成**: Gemini 2.5 Flash Image で各スライドに適した画像を自動生成
- **AI原稿生成**: Gemini 2.0 Flash が自然な原稿を自動生成
- **音声合成**: Edge TTS による高品質な日本語音声
- **字幕自動生成**: 音声に合わせた字幕を自動生成
- **キャラクターアニメーション**: 喋っている時と待機時で異なるアニメーション
  - 喋っている時: talk1~talk6 を循環再生
  - 待機時: idle1~idle6 を循環再生
- **完全アーカイブ**: すべての成果物をリポジトリに自動保存
- **GitHub Actions統合**: クラウド上で完全に動作

## 5段階ワークフロー

### ワークフロー1: プレゼンテーション生成

```
YAML入力 → スライド生成 → AI画像生成 → 画像埋め込み → HTML/PDF生成 → 個別画像出力 → リポジトリ保存
```

1. **スライド生成**: YAMLからMarp形式のMarkdownスライドを生成
2. **AI画像プロンプト生成**: Gemini APIで各スライドに適した画像プロンプトを生成
3. **AI画像生成**: Gemini 2.5 Flash Image で3:4縦長画像を生成
4. **画像埋め込み**: スライドに画像を右端揃えで埋め込み
5. **HTML/PDF変換**: Marpで見栄えの良いプレゼンテーションを生成
6. **個別画像出力**: 各スライドを1枚ずつPNG画像として出力
7. **リポジトリ保存**: `presentations/<トピック名>/` に全ファイルを保存

### ワークフロー2: 画像プロンプト生成

既存のプレゼンテーションから画像プロンプトを生成します。

### ワークフロー3: スライドに画像を挿入

生成された画像をスライドに挿入します。

### ワークフロー4: スライドテキスト編集

```
編集指示入力 → AI解析 → テキスト修正 → 画像再生成（オプション） → スライド再生成（オプション） → 保存
```

1. **編集指示入力**: プレゼンテーション名と自然言語の編集指示を入力
2. **AI解析**: Gemini APIが編集指示を解析し、どのスライドをどう変更するか判断
3. **テキスト修正**: タイトルや本文を自動的に編集
4. **画像再生成**: 必要に応じて該当スライドの画像を再生成
5. **スライド再生成**: 必要に応じてHTML/PDF、個別画像を再生成
6. **保存**: 変更内容をリポジトリに保存

自然言語でスライドのテキストを編集（文字の見切れや表現の調整など細かい修正に最適）

### ワークフロー5: 動画生成

```
プレゼンテーション選択 → 原稿生成 → 音声生成 → タイミング計算 → 動画レンダリング → リポジトリ保存
```

1. **スライド画像準備**: 既存のプレゼンテーションからスライド画像を取得
2. **原稿生成**: Gemini APIでスライド内容から自然な原稿を生成
3. **音声生成**: Edge TTSで音声ファイルを生成
4. **タイミング計算**: 音声の長さから字幕のタイミングを計算
5. **動画レンダリング**: Remotionでスライド画像+キャラクター+字幕の動画を生成
6. **リポジトリ保存**: `videos/<トピック名>/` に全ファイルを保存

## セットアップ

### 1. 必要なシークレットの設定

GitHub リポジトリの Settings > Secrets and variables > Actions で以下を設定:

- `GOOGLE_AI_API_KEY`: Google AI Studio で取得したAPIキー
  - https://aistudio.google.com/apikey
- `ANTHROPIC_API_KEY` (オプション): Anthropic Claude API キー
  - プレゼンテーション編集機能で使用（未設定の場合はGemini APIにフォールバック）
  - https://console.anthropic.com/

### 2. GitHub Pagesの有効化（推奨）

プレゼンテーションをオンラインで確認できるようにするため、GitHub Pagesを有効にします：

1. リポジトリの `Settings` > `Pages` を開く
2. `Source` を `Deploy from a branch` に設定
3. `Branch` を `main` / `(root)` に設定
4. `Save` をクリック

数分後、以下のURLでプレゼンテーション一覧が確認できます：
```
https://<your-username>.github.io/SlideMovie_WorkFlow/
```

### 3. リポジトリのクローン

```bash
git clone <your-repo-url>
cd <repo-name>
```

## 使用方法

### ステップ1: プレゼンテーション生成

#### 方法A: 手動実行

1. GitHub リポジトリの「Actions」タブを開く
2. 「1. Generate Presentation」ワークフローを選択
3. 「Run workflow」をクリック
4. 入力YAMLファイルのパスを指定（例: `inputs/ai_industry_trends_2025.yml`）
5. 「Run workflow」を実行

#### 方法B: 自動実行（プッシュトリガー）

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

#### 生成されるファイル

プレゼンテーションは `presentations/<トピック名>/` ディレクトリに保存されます：

- `input.yml` - 元のYAML入力ファイル
- `<トピック名>_slide.md` - Markdownスライド
- `<トピック名>_slide_with_images.md` - 画像埋め込み済みMarkdownスライド
- `<トピック名>.html` - HTMLプレゼンテーション
- `<トピック名>.pdf` - PDFプレゼンテーション
- `slide-001.png`, `slide-002.png`, ... - 個別スライド画像
- `images/` - AI生成画像

### ステップ2: 画像生成（オプション）

既存のプレゼンテーションから画像プロンプトを生成する場合：

1. GitHub リポジトリの「Actions」タブを開く
2. 「2. Generate Presentation Images」ワークフローを選択
3. 「Run workflow」をクリック

### ステップ3: 画像挿入（オプション）

生成された画像をスライドに挿入する場合：

1. GitHub リポジトリの「Actions」タブを開く
2. 「3. Insert Images to Slides」ワークフローを選択
3. 「Run workflow」をクリック

### ステップ4: スライドテキスト編集（オプション）

自然言語で特定のスライドのテキストを編集したい場合（文字の見切れなどの細かい修正に最適）：

1. GitHub リポジトリの「Actions」タブを開く
2. 「4. Edit Slide Text」ワークフローを選択
3. 「Run workflow」をクリック
4. 以下を入力：
   - **Presentation name**: プレゼンテーション名（例: `③バナー作り`）
   - **Edit instructions**: 編集指示（例: `スライド8の構成要素を大きく、目立つ、短く、簡潔にして`）
   - **Regenerate images**: 画像を再生成する（デフォルト: true）
   - **Regenerate all**: スライド全体を再生成する（デフォルト: true）
5. 「Run workflow」を実行

AIが編集指示を解析して、適切なスライドのタイトルや本文を自動的に修正します。

#### 使用例

**例1: 文字を短く簡潔にする**
```
Presentation name: ③バナー作り
Edit instructions: スライド8の構成要素を大きく、目立つ、短く、簡潔にして
Regenerate images: ✓
Regenerate all: ✓
```

**例2: 特定の箇条書きを変更**
```
Presentation name: ①すごいぞAI_AI概論
Edit instructions: スライド13の手順の4番目を「文字を自分の好きな内容に変更」に変えて
Regenerate images: ✓
Regenerate all: ✓
```

**例3: タイトルを変更**
```
Presentation name: ③バナー作り
Edit instructions: スライド8のタイトルを「実習1：テンプレートから簡単作成（15分）」に変更して
Regenerate images: ✓
Regenerate all: ✓
```

**例4: 複数のスライドを同時に修正**
```
Presentation name: ③バナー作り
Edit instructions: スライド5と7と9のタイトルを短くして。スライド10の本文を3行にまとめて
Regenerate images: ✗
Regenerate all: ✓
```

**例5: 箇条書きを追加・削除**
```
Presentation name: ①すごいぞAI_AI概論
Edit instructions: スライド8の手順から2番目を削除して、最後に「保存して共有」を追加して
Regenerate images: ✓
Regenerate all: ✓
```

#### 編集指示のコツ

- スライド番号を明確に指定する（例: `スライド8`、`8番目のスライド`）
- 何を変更したいか具体的に書く（例: `タイトルを変更`、`本文を短く`、`箇条書きを追加`）
- 抽象的な指示も可能（例: `大きく`、`簡潔に`、`わかりやすく`）
- 複数のスライドを同時に編集可能

#### 生成されるファイル

修正されたプレゼンテーションは、元のディレクトリに保存されます：

- `presentations/<トピック名>/input.yml` - 修正されたYAML
- オプションに応じて、HTML/PDF、画像なども再生成されます

### ステップ5: 動画生成

プレゼンテーションが生成されたら、動画を作成できます：

1. GitHub リポジトリの「Actions」タブを開く
2. 「5. Create Video」ワークフローを選択
3. 「Run workflow」をクリック
4. プレゼンテーション名を指定（例: `最新のAI業界の動向2025`）
   - これは `presentations/` ディレクトリにあるフォルダ名です
5. 「Run workflow」を実行

#### 生成されるファイル

動画は `videos/<トピック名>/` ディレクトリに保存されます：

- `video.mp4` - 最終動画ファイル
- `video_timings.json` - タイミング情報
- `scripts_output/` - 生成された原稿
- `audio_output/` - 音声ファイル

### ステップ6: プレゼンテーション編集（オプション）

既存のプレゼンテーションを修正したい場合：

#### 方法A: GitHub Actions UI（短いプロンプト向け）

1. GitHub リポジトリの「Actions」タブを開く
2. 「3. Edit Presentation」ワークフローを選択
3. 「Run workflow」をクリック
4. 以下を入力：
   - **Presentation to edit**: 編集するプレゼンテーション名（例: `最新のAI業界の動向2025`）
   - **Edit instructions**: 修正内容を自然言語で記述（例: `スライド3の内容をより詳しくして、最新の統計データを追加してください`）
5. 「Run workflow」を実行

#### 方法B: Issue経由（長いプロンプト向け）

長い修正指示を入力したい場合は、Issueコメントを使用します：

1. リポジトリで新しいIssueを作成（タイトルは任意）
2. コメント欄に以下の形式で記述：

   **パターン1: プレゼンテーション名を指定**
   ```
   @claude 最新のAI業界の動向2025 スライド3の内容をより詳しくして、最新の統計データを追加してください。

   さらに、各スライドのタイトルをより魅力的な表現に変更し、
   全体的に専門的なトーンから初心者向けのわかりやすい表現に変更してください。
   ```

   **パターン2: プレゼンテーション名を省略（1つだけの場合）**
   ```
   @claude スライドのタイトルをもっとキャッチーに修正してください。
   ```

   **フォーマット:**
   ```
   @claude [プレゼンテーション名] [修正指示（複数行可）]
   ```
   または
   ```
   @claude [修正指示（複数行可）]
   ```
   （プレゼンテーションが1つだけの場合は自動検出）

3. コメントを送信すると、GitHub Actionsが自動的に実行されます
4. 完了すると、Issueに結果がコメントされます

#### 編集例

**修正指示の例：**

- `スライド5を削除して、新しいスライド「まとめ」を最後に追加してください`
- `各スライドのタイトルをより魅力的な表現に変更してください`
- `2番目のスライドの箇条書きを3つから5つに増やしてください`
- `全体的に専門的なトーンから初心者向けのわかりやすい表現に変更してください`

#### 生成されるファイル

編集されたプレゼンテーションは、元のディレクトリに上書き保存されます：

- `presentations/<トピック名>/` - すべてのファイルが更新されます
  - `input.yml` - 編集された入力ファイル
  - HTML/PDF、画像なども再生成されます

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

## リポジトリ内のファイル構造

すべての成果物はリポジトリに保存され、履歴として残ります：

```
.
├── .github/workflows/
│   ├── 1-generate-presentation.yml    # プレゼンテーション生成ワークフロー
│   ├── 2-generate-presentation-images.yml  # 画像プロンプト生成ワークフロー
│   ├── 3-insert-images-to-slides.yml  # 画像挿入ワークフロー
│   ├── 4-edit-slide-text.yml          # スライドテキスト編集ワークフロー
│   ├── 5-create-video.yml             # 動画生成ワークフロー
│   └── claude_bot.yml                 # Claude Code Bot (Issueコメントで実行)
├── inputs/                            # 入力YAMLファイル
│   └── ai_industry_trends_2025.yml    # サンプル入力
├── presentations/                     # 生成されたプレゼンテーション（リポジトリに保存）
│   └── <トピック名>/
│       ├── input.yml                  # 元のYAML
│       ├── <トピック名>_slide.md      # Markdownスライド
│       ├── <トピック名>_slide_with_images.md  # 画像付きスライド
│       ├── <トピック名>.html          # HTMLプレゼンテーション
│       ├── <トピック名>.pdf           # PDFプレゼンテーション
│       ├── slide-001.png ~ slide-NNN.png  # 個別スライド画像
│       └── images/                    # AI生成画像
├── videos/                            # 生成された動画（リポジトリに保存）
│   └── <トピック名>/
│       ├── video.mp4                  # 最終動画
│       ├── video_timings.json         # タイミング情報
│       ├── scripts_output/            # 原稿データ
│       └── audio_output/              # 音声ファイル
├── scripts/                           # 処理スクリプト
│   ├── create_slide.py                # スライド生成
│   ├── edit_presentation.py           # プレゼンテーション編集（AI・全体編集）
│   ├── edit_slide_text.py             # スライドテキスト編集（旧・直接編集）
│   ├── edit_slide_text_natural.py     # スライドテキスト編集（新・自然言語）
│   ├── generate_script.py             # 原稿生成
│   ├── generate_audio.py              # 音声生成
│   ├── generate_timings.py            # タイミング計算
│   └── prepare_slides_for_video.py    # スライド画像準備
├── remotion-project/                  # Remotionプロジェクト
│   ├── src/
│   │   ├── Video.tsx                  # メインビデオコンポーネント
│   │   └── Root.tsx                   # Remotionルート
│   └── public/                        # キャラクター画像
│       ├── idle1.png ~ idle6.png      # 待機アニメーション
│       └── talk1.png ~ talk6.png      # 会話アニメーション
├── PresentationWorkFlow/              # プレゼンテーション生成スクリプト
└── requirements.txt                   # Python依存パッケージ
```

### Artifacts

各ワークフロー実行後、以下がArtifactsとしてもダウンロード可能：

**ワークフロー1: プレゼンテーション生成**
- `presentation-<トピック名>` - すべてのプレゼンテーションファイル

**ワークフロー4: スライドテキスト編集**
- `edited-presentation-<トピック名>` - 編集されたプレゼンテーションファイル

**ワークフロー5: 動画生成**
- `video-<トピック名>` - 動画と関連ファイル

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

### プレゼンテーション生成（ローカル）

```bash
# Python依存パッケージのインストール
pip install pyyaml google-generativeai pillow

# Marp CLIのインストール
npm install -g @marp-team/marp-cli

# 環境変数の設定
export GOOGLE_AI_API_KEY="your-api-key"

# ディレクトリ作成
mkdir -p slides images output presentations

# スライド生成
python3 scripts/create_slide.py inputs/ai_industry_trends_2025.yml

# 画像プロンプト生成
python3 PresentationWorkFlow/scripts/generate_image_prompts.py slides/最新のAI業界の動向2025_slide.md

# 画像生成
python3 PresentationWorkFlow/scripts/generate_images.py slides/最新のAI業界の動向2025_imageprompt.csv 最新のAI業界の動向2025

# 画像埋め込み
python3 PresentationWorkFlow/scripts/embed_images.py slides/最新のAI業界の動向2025_slide.md images 最新のAI業界の動向2025

# HTML/PDF生成
marp slides/最新のAI業界の動向2025_slide_with_images.md -o output/最新のAI業界の動向2025.html --html --allow-local-files
marp slides/最新のAI業界の動向2025_slide_with_images.md -o output/最新のAI業界の動向2025.pdf --pdf --allow-local-files

# 個別画像出力
mkdir -p presentations/最新のAI業界の動向2025
marp slides/最新のAI業界の動向2025_slide_with_images.md -o presentations/最新のAI業界の動向2025/slide-%d.png --images png --allow-local-files
```

### 動画生成（ローカル）

```bash
# Python依存パッケージのインストール（追加）
pip install edge-tts pydub

# ffmpegのインストール（macOS）
brew install ffmpeg

# Node.js依存パッケージのインストール
cd remotion-project
npm install
cd ..

# スライド画像準備
python3 scripts/prepare_slides_for_video.py presentations/最新のAI業界の動向2025

# 原稿生成
python3 scripts/generate_script.py presentations/最新のAI業界の動向2025/最新のAI業界の動向2025_slide_with_images.md

# 音声生成
python3 scripts/generate_audio.py scripts_output/最新のAI業界の動向2025_slide_with_images_script.json

# タイミング生成
python3 scripts/generate_timings.py audio_output/audio_metadata.json

# Remotionプロジェクトにファイル配置
cp audio_output/video_timings.json remotion-project/timings.json
mkdir -p remotion-project/public/audio remotion-project/public/slides
cp audio_output/*.mp3 remotion-project/public/audio/
cp slide_images/*.png remotion-project/public/slides/
cp slide_images/slides_metadata.json remotion-project/

# 動画レンダリング
cd remotion-project
npm run build
cd ..

# 生成された動画: remotion-project/out/video.mp4
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