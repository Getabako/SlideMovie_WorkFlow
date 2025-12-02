# AI画像付きプレゼンテーション自動生成ワークフロー

このリポジトリは、GitHub Actions上でAI生成画像付きのプレゼンテーションスライドを自動作成するワークフローを提供します。

## 概要

YAMLファイルでスライドの内容を定義すると、以下の処理が自動的に実行されます：

1. Marp形式のMarkdownスライドを生成
2. 各スライドの内容に適した画像プロンプトをGemini 2.0 Flashが生成
3. Gemini 2.5 Flash Image (NanoBanana) で3:4の縦長画像を生成
4. 生成された画像をスライドに右端揃えで埋め込む
5. MarpでHTML・PDF形式に変換

## ディレクトリ構造

```
PresentationWorkFlow/
├── .github/
│   └── workflows/
│       └── generate_presentation.yml  # GitHub Actionsワークフロー
├── scripts/
│   ├── create_slide.py               # スライド作成スクリプト
│   ├── generate_image_prompts.py     # 画像プロンプト生成スクリプト
│   ├── generate_images.py            # 画像生成スクリプト
│   └── embed_images.py               # 画像埋め込みスクリプト
├── inputs/                           # 入力YAMLファイル
│   └── sample.yml                    # サンプル入力ファイル
├── slides/                           # 生成されたスライド
├── images/                           # 生成された画像
├── output/                           # 最終成果物（HTML/PDF）
├── themes/                           # Marpカスタムテーマ
└── .marprc.yml                       # Marp設定ファイル
```

## セットアップ

### 1. リポジトリのセットアップ

このリポジトリをGitHubにプッシュします：

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin <your-repository-url>
git push -u origin main
```

### 2. APIキーの設定

GitHub リポジトリの Settings > Secrets and variables > Actions で、以下のシークレットを設定します：

- `GOOGLE_AI_API_KEY`: Google AI API キー（Gemini用）
  - https://aistudio.google.com/apikey で取得

## 使用方法

### 方法1: 手動実行

1. GitHub リポジトリの「Actions」タブを開く
2. 「Generate Presentation with AI Images」ワークフローを選択
3. 「Run workflow」をクリック
4. 入力YAMLファイルのパスを指定（例: `inputs/sample.yml`）
5. 「Run workflow」を実行

### 方法2: 自動実行

`inputs/` ディレクトリにYAMLファイルをコミットしてプッシュすると、自動的にワークフローが実行されます：

```bash
# 新しいプレゼンテーション用のYAMLファイルを作成
cp inputs/sample.yml inputs/my_presentation.yml

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

### フィールドの説明

- `topic`: プレゼンテーションのタイトル（ファイル名にも使用されます）
- `slides`: スライドのリスト
  - `title`: スライドのタイトル
  - `content`: スライドの内容（Markdown形式）

## 生成される成果物

ワークフロー実行後、以下のファイルが生成されます：

1. **Markdownスライド**: `slides/<topic>_slide_with_images.md`
2. **HTMLスライド**: `output/<topic>.html`
3. **PDFスライド**: `output/<topic>.pdf`
4. **生成画像**: `images/<topic>_page*.png`

成果物は GitHub Actions の Artifacts からダウンロードできます。

## ローカルでの実行

ローカル環境でテストする場合：

```bash
# 依存関係のインストール
pip install pyyaml google-genai pillow
npm install -g @marp-team/marp-cli

# 環境変数の設定
export GOOGLE_AI_API_KEY="your-google-ai-api-key"

# スライド作成
python scripts/create_slide.py inputs/sample.yml

# 画像プロンプト生成
python scripts/generate_image_prompts.py slides/AI技術の未来_slide.md

# 画像生成
python scripts/generate_images.py slides/AI技術の未来_imageprompt.csv AI技術の未来

# 画像埋め込み
python scripts/embed_images.py slides/AI技術の未来_slide.md images AI技術の未来

# Marpで変換
marp slides/AI技術の未来_slide_with_images.md -o output/AI技術の未来.pdf --pdf --allow-local-files
marp slides/AI技術の未来_slide_with_images.md -o output/AI技術の未来.html --html --allow-local-files
```

## カスタマイズ

### 画像のアスペクト比を変更

`scripts/generate_images.py` の `aspect_ratio` パラメータを変更：

```python
aspect_ratio="3:4"  # 縦長
aspect_ratio="16:9" # ワイド
aspect_ratio="1:1"  # 正方形
```

### 画像の配置を変更

`scripts/embed_images.py` の `![bg right:40% fit]` 部分を変更：

```markdown
![bg right:40% fit](image.png)  # 右側40%
![bg right:50% fit](image.png)  # 右側50%
![bg left:40% fit](image.png)   # 左側40%
```

### Marpテーマのカスタマイズ

`themes/` ディレクトリにカスタムテーマCSSファイルを追加し、スライドのヘッダーで指定：

```yaml
---
marp: true
theme: custom
---
```

## トラブルシューティング

### APIキーのエラー

```
エラー: GOOGLE_AI_API_KEY環境変数が設定されていません
```

→ GitHub Secrets に正しくAPIキーが設定されているか確認してください。

### 画像生成のエラー

```
エラー: 画像の生成に失敗しました
```

→ Google AI API の利用制限を超えている可能性があります。APIの使用量を確認してください。

### Marp変換のエラー

```
エラー: 画像ファイルが見つかりません
```

→ 画像ファイルのパスが正しいか確認してください。相対パスが正しく設定されているか確認してください。

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 貢献

プルリクエストやイシューの報告を歓迎します。

## 参考リンク

- [Marp](https://marp.app/) - Markdown Presentation Ecosystem
- [Google Gemini API](https://ai.google.dev/)
- [Gemini 2.0 Flash](https://ai.google.dev/gemini-api/docs/models/gemini-v2)
- [Gemini 2.5 Flash Image (NanoBanana)](https://ai.google.dev/gemini-api/docs/image-generation)
