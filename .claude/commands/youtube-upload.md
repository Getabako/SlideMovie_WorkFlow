# YouTube投稿コマンド

指定されたプレゼンテーションの動画をYouTubeにアップロードします。

## 引数
- `$ARGUMENTS`: プレゼンテーション名（例: `⑦ホームページ作り`）

## 処理手順

1. **動画ファイルの確認**
   - `presentations/$ARGUMENTS/video_output/$ARGUMENTS.mp4` が存在するか確認
   - 存在しない場合は `/video-create` コマンドを先に実行するよう案内

2. **公開設定の確認**
   ユーザーに公開設定を確認:
   - `public`: 公開（誰でも視聴可能）
   - `unlisted`: 限定公開（URLを知っている人のみ、デフォルト）
   - `private`: 非公開（自分のみ）

3. **YouTube投稿スクリプトの実行**
   ```bash
   source venv/bin/activate
   python scripts/upload_to_youtube.py "$ARGUMENTS" --privacy <選択した公開設定>
   ```

4. **投稿完了の確認**
   - 投稿されたURLを表示
   - サムネイル設定の案内（YouTube Studioで手動設定）

## 投稿先チャンネル
https://www.youtube.com/@if-juku

## 自動設定される項目
- **タイトル**: プレゼン名から自動生成（AI/IT/教育キーワード判定）
- **説明文**: チャンネル紹介、動画内容、CTA（いいね・登録促進）を含む
- **タグ**: 検索されやすいキーワードを自動設定
- **カテゴリ**: 教育（ID: 27）
- **言語**: 日本語

## 初回認証について
初回実行時はブラウザでGoogleアカウント認証が必要です。
- ブラウザが自動で開きます
- Googleアカウントにログイン
- チャンネルへのアクセスを許可
- 認証後は `youtube_token.pickle` に保存され、次回以降は自動認証

## オプション
- `--privacy public|unlisted|private`: 公開設定（デフォルト: unlisted）

## 使用例
```bash
# 限定公開（デフォルト）
python scripts/upload_to_youtube.py "⑦ホームページ作り"

# 公開
python scripts/upload_to_youtube.py "⑦ホームページ作り" --privacy public

# 非公開
python scripts/upload_to_youtube.py "⑦ホームページ作り" --privacy private
```

## トラブルシューティング

### 認証エラーが出る場合
- `youtube_token.pickle` を削除して再認証
- Google Cloud Console でOAuth同意画面の設定を確認

### アップロードが失敗する場合
- ファイルサイズ制限: 未認証チャンネルは15分/128GB以下
- APIクォータ: 1日のアップロード数に制限あり
- ネットワーク接続を確認
