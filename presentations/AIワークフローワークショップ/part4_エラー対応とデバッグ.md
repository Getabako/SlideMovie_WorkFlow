# AIワークフローワークショップ
## Part4: エラー対応とデバッグ（約1時間）

---

# エラーは必ず起きる

## GitHub Actionsの現実

- 最初から完璧に動くことはほぼない
- 1工程ずつエラーを潰していく作業が必要
- **エラーログを読む → AIに聞く → 修正**の繰り返し

**エラー対応スキルが最も重要！**

---

# エラーログの確認方法（1/2）

## GitHub Actionsのログを開く

1. リポジトリの「Actions」タブ
2. 失敗したワークフロー（赤い×）をクリック
3. 失敗したジョブ名をクリック
4. エラーが出ているステップを展開

---

# エラーログの確認方法（2/2）

## ログの読み方

```
Run npm start
  > daily-note-blog@1.0.0 start
  > npx tsx src/main.ts

  Error: Cannot find module '@google/generative-ai'
  ↑ ここがエラーメッセージ

  at ModuleLoader.resolveModule (node:internal/modules/esm/loader:...)
  ↑ ここはスタックトレース（場所の情報）
```

**エラーメッセージを正確にコピーすることが重要**

---

# エラーをAIに伝えるプロンプト

## そのまま使えるテンプレート

```
GitHub Actionsで以下のエラーが出ています。
原因と解決方法を教えてください。

【エラーメッセージ】
（ここにエラーログを貼り付け）

【実行したコマンド】
npm start

【関連するコード】
（該当するファイルの内容を貼り付け）

【環境】
- Node.js 20
- Ubuntu (GitHub Actions)
```

---

# よくあるエラー①

## モジュールが見つからない

```
Error: Cannot find module '@google/generative-ai'
```

## 原因

- `npm install` が実行されていない
- package.jsonに依存関係が書かれていない

## 解決方法

package.jsonを確認：

```json
"dependencies": {
  "@google/generative-ai": "^0.21.0"
}
```

---

# よくあるエラー②

## APIキーが設定されていない

```
Error: GEMINI_API_KEY が設定されていません
```

## 原因

- GitHub Secretsに登録されていない
- ワークフローで環境変数を渡していない

## 解決方法

daily-post.ymlを確認：

```yaml
env:
  GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
```

---

# よくあるエラー③

## APIエラー（認証失敗）

```
Error: 401 Unauthorized - Invalid API key
```

## 原因

- APIキーが間違っている
- APIキーの権限が不足

## 解決方法

1. Google AI Studioで新しいキーを発行
2. GitHub Secretsを更新
3. 再実行

---

# よくあるエラー④

## JSONパースエラー

```
SyntaxError: Unexpected token 'A' at position 0
```

## 原因

- AIの出力がJSON形式になっていない
- MarkdownのコードブロックがついてしまっAている

## 解決方法

出力のクリーニング処理を追加：

```typescript
let text = result.response.text();
// ```json と ``` を除去
text = text.replace(/```json\n?/g, '').replace(/```\n?/g, '');
return JSON.parse(text);
```

---

# よくあるエラー⑤

## タイムアウトエラー

```
Error: The operation was aborted due to timeout
```

## 原因

- 処理に時間がかかりすぎた
- APIの応答が遅い

## 解決方法

ワークフローにタイムアウト設定を追加：

```yaml
jobs:
  post:
    runs-on: ubuntu-latest
    timeout-minutes: 30  # 30分でタイムアウト
```

---

# エラー対応のプロセス

## 1. エラーログをコピー

```
Actions → 失敗したジョブ → ログを展開
→ エラーメッセージをコピー
```

## 2. AIに質問

```
GitHub Actionsで以下のエラーが出ています。
原因と解決方法を教えてください。

【エラーメッセージ】
（コピーしたログを貼り付け）
```

---

# エラー対応のプロセス

## 3. 修正をコミット

AIの回答をもとにコードを修正：

1. GitHubでファイルを開く
2. 鉛筆アイコン（Edit）をクリック
3. コードを修正
4. 「Commit changes」で保存

## 4. 再実行

```
Actions → Run workflow → 実行
```

**成功するまで繰り返す！**

---

# デバッグ用のログを追加

## 問題箇所を特定するために

```typescript
async function main() {
  console.log('🚀 開始');

  console.log('📊 リサーチ開始...');
  const research = await runResearcher(topic);
  console.log('📊 リサーチ完了:', JSON.stringify(research).slice(0, 100));

  console.log('✍️ 執筆開始...');
  const article = await runWriter(research);
  console.log('✍️ 執筆完了:', article.title);

  console.log('🎨 画像生成開始...');
  // ...
}
```

**どこで止まったかわかるようにログを入れる**

---

# 完成したら確認すること

## チェックリスト

- [ ] 毎日自動で実行されるか（cron設定）
- [ ] エラー時に通知が来るか
- [ ] noteに正しく投稿されるか
- [ ] 画像が表示されているか
- [ ] 記事の内容が問題ないか

## 最初は下書き投稿がおすすめ

```typescript
status: 'draft' // 公開前に内容確認
```

---

# 応用：エラー通知を追加

## Slackに通知する

```yaml
- name: Notify on failure
  if: failure()
  uses: slackapi/slack-github-action@v1
  with:
    channel-id: 'your-channel-id'
    slack-message: '⚠️ Daily Blog Postが失敗しました'
  env:
    SLACK_BOT_TOKEN: ${{ secrets.SLACK_BOT_TOKEN }}
```

**失敗したらすぐに気づける仕組み**

---

# ワークショップまとめ

## 今日学んだこと

1. **AIエージェント設計** - 役割分担の考え方
2. **GitHub環境構築** - リポジトリとSecrets
3. **GitHub Actions** - 自動実行の設定
4. **エラー対応** - ログを読んでAIに聞く

## 今後の発展

- 複数のSNSに同時投稿
- 画像のバリエーション増加
- 投稿分析と改善の自動化

**お疲れ様でした！**

