# 画像自動生成ワークフロー

テキストだけのスライドに対して、AIで画像を自動生成し、動画化するワークフローです。

## 概要

1. **画像プロンプト生成**: Geminiを使って各スライドに適した画像生成プロンプトを作成
2. **画像生成**: Stable Diffusion APIまたはプレースホルダー画像を生成
3. **スライド画像化**: Marpで画像付きスライドを個別画像として出力
4. **動画作成**: ffmpegで動画に変換

## 前提条件

### 必須ツール

```bash
# Node.js (Marp CLI用)
npm install -g @marp-team/marp-cli

# Python 3.11+
pip install google-generativeai pillow requests pyyaml

# ffmpeg (動画作成用)
brew install ffmpeg  # macOS
# または
sudo apt-get install ffmpeg  # Linux
```

### 環境変数

```bash
# Google AI API キー（必須）
export GOOGLE_AI_API_KEY="your-google-ai-api-key"

# Stability AI API キー（オプション、画像生成を使用する場合）
export STABILITY_API_KEY="your-stability-ai-api-key"
```

Stability AI APIキーがない場合は、プレースホルダー画像が生成されます。

## 使い方

### 1. 画像生成

```bash
python3 scripts/generate_slide_images.py \
  "presentations/②AIを使って画像生成をしてみよう/②AIを使って画像生成をしてみよう.md"
```

#### オプション

- `--api`: 使用する画像生成API
  - `stable-diffusion` (デフォルト): Stability AI
  - `imagen`: Google Imagen (未実装)

#### 出力

- `presentations/②AIを使って画像生成をしてみよう/images/040___.png`
- `presentations/②AIを使って画像生成をしてみよう/images/041___.png`
- ...

各スライドに対応する画像が `images/` フォルダに生成されます。

### 2. 動画作成

```bash
python3 scripts/create_presentation_video.py \
  "presentations/②AIを使って画像生成をしてみよう/②AIを使って画像生成をしてみよう.md" \
  --duration 5 \
  --output "presentations/②AIを使って画像生成をしてみよう/output"
```

#### オプション

- `--duration`, `-d`: 各スライドの表示時間（秒、デフォルト: 5）
- `--output`, `-o`: 出力ディレクトリ
- `--transitions`, `-t`: トランジション効果を追加

#### 出力

- `presentations/②AIを使って画像生成をしてみよう/output/②AIを使って画像生成をしてみよう.mp4`

### 3. 一括実行

```bash
# 画像生成 + 動画作成
bash scripts/generate_presentation_video.sh \
  "presentations/②AIを使って画像生成をしてみよう/②AIを使って画像生成をしてみよう.md"
```

## Marp画像配置の仕様

### 背景画像の配置

Marpでは以下の形式で背景画像を配置します：

```markdown
![bg right:45%](images/image.png)
```

#### パラメータ

- `bg`: 背景画像として配置
- `right`: 右側に配置（`left`も可能）
- `45%`: 画像の幅（スライドの45%）
- 画像は自動的に上下の高さをスライドに合わせて拡大/縮小されます

### 推奨画像サイズ

- **横長画像**: 1792x1008 (16:9比率)
- **縦長画像**: 1080x1920 (9:16比率)

### カスタムスタイル

より細かい調整が必要な場合は、CSSを使用：

```markdown
<style>
section {
  background-size: contain;
  background-position: right center;
}
</style>

![bg right](images/image.png)
```

## トラブルシューティング

### 画像が表示されない

1. **画像パスを確認**
   ```bash
   ls presentations/②AIを使って画像生成をしてみよう/images/
   ```

2. **Marpの`--allow-local-files`オプションを確認**
   ```bash
   npx @marp-team/marp-cli \
     --allow-local-files \
     ②AIを使って画像生成をしてみよう.md
   ```

3. **画像の相対パス**
   - `.md`ファイルから見た相対パスで指定
   - `images/040___.png` (OK)
   - `/absolute/path/images/040___.png` (NG)

### 画像サイズが合わない

1. **アスペクト比を確認**
   ```bash
   file presentations/*/images/*.png
   ```

2. **Marpテーマで調整**
   ```css
   section {
     background-size: cover;  /* または contain */
   }
   ```

### 動画作成が失敗する

1. **ffmpegのインストール確認**
   ```bash
   ffmpeg -version
   ```

2. **スライド画像の確認**
   ```bash
   ls presentations/②AIを使って画像生成をしてみよう/*.png
   ```

## 画像生成プロンプトのカスタマイズ

`scripts/generate_slide_images.py`の`generate_image_prompt()`メソッドを編集：

```python
def generate_image_prompt(self, slide: Dict[str, str]) -> str:
    prompt_request = f"""以下のスライド用の背景画像プロンプトを作成:

タイトル: {slide['title']}
内容: {slide['content'][:500]}

要件:
- プロフェッショナル
- 16:9横長
- テキストなし
- [カスタム要件を追加]

英語のプロンプトのみ出力:"""

    # ...
```

## 参考リンク

- [Marp公式ドキュメント](https://marpit.marp.app/)
- [Marp画像構文](https://marpit.marp.app/image-syntax)
- [Stability AI API](https://platform.stability.ai/)
- [Google AI Studio](https://makersuite.google.com/)
- [ffmpeg Documentation](https://ffmpeg.org/documentation.html)

## ライセンス

このワークフローで生成された画像の利用については、各APIの利用規約を確認してください：

- **Stability AI**: [Terms of Service](https://stability.ai/terms-of-service)
- **Google AI**: [Terms of Service](https://ai.google.dev/terms)
