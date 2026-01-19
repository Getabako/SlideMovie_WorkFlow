# サムネイル生成コマンド

指定されたプレゼンテーションのYouTubeサムネイルを生成します。

## 引数
- `$ARGUMENTS`: プレゼンテーション名（例: `②AIを使って画像生成をしてみよう`）

## 処理手順

1. **プレゼンテーションの確認**
   - `presentations/$ARGUMENTS/` ディレクトリが存在するか確認
   - 動画ファイル（`video_output/output.mp4`）があればその情報も参照

2. **サムネイル生成スクリプトの実行**
   ```bash
   source venv/bin/activate
   GOOGLE_AI_API_KEY=AIzaSyBX5vrS6gUyRPJmeVEeuYhIjDPsMx3V5pY python scripts/generate_thumbnail.py "$ARGUMENTS"
   ```

3. **生成完了の確認**
   - 生成されたサムネイル画像のパスを表示
   - `presentations/$ARGUMENTS/video_output/thumbnail.png` に保存される

## 使用するモデル
- **Gemini 2.5 Flash Preview** (gemini-2.5-flash-preview-05-20)
- 画像生成対応の最新モデル

## 自動設定される項目
- **サイズ**: 1280x720ピクセル（YouTube推奨サイズ）
- **キャラクター**: 塾頭高崎翔太（目はヘアバンドで隠れている）
- **ロゴ**: IF塾ロゴ
- **テキストエフェクト**: 縁取り、ドロップシャドウ、グロー効果

## キャラクター設定（重要）
- 黒いヘアバンドで目が**完全に隠れている**
- 髪は黒くてボサボサ
- 黒いTシャツと黒いハーフパンツ
- 赤い下駄
- 腕にサイバー風のタトゥー
- ノートパソコンを持っているポーズ

## オプション
- `--character <path>`: キャラクター画像のパス
- `--logo <path>`: ロゴ画像のパス
- `--output-dir <path>`: 出力ディレクトリ

## 使用例
```bash
# 基本的な使い方
python scripts/generate_thumbnail.py "②AIを使って画像生成をしてみよう"

# カスタムキャラクター画像を使用
python scripts/generate_thumbnail.py "②AIを使って画像生成をしてみよう" --character "/path/to/character.png"
```

## 出力ファイル
- `presentations/$ARGUMENTS/video_output/thumbnail.png`

## YouTube Studioでの設定
生成されたサムネイルは手動でYouTube Studioからアップロードしてください：
1. YouTube Studio を開く
2. 対象の動画を選択
3. 「サムネイル」セクションで「カスタムサムネイルをアップロード」
4. 生成された `thumbnail.png` を選択

## トラブルシューティング

### 画像が生成されない場合
- API キーが正しく設定されているか確認
- Gemini APIの画像生成機能が有効か確認

### キャラクターの目が見えてしまう場合
- 再生成を試みる（プロンプトに厳格な指示が含まれています）
- 手動で画像編集ソフトで修正
