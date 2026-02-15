# AIワークフローワークショップ
## Part2: GitHub環境構築（約1時間）

---

# GitHubアカウント作成

## まだアカウントがない方

1. **github.com** にアクセス
2. 「Sign up」をクリック
3. メールアドレス、パスワード、ユーザー名を入力
4. メール認証を完了
5. プランは「Free」でOK

**すでにアカウントがある方は次へ進もう**

---

# 新しいリポジトリを作成

## 手順

1. GitHubにログイン
2. 右上の「+」→「New repository」
3. 以下を入力：

| 項目 | 設定値 |
|------|--------|
| Repository name | `daily-note-blog` |
| Description | 毎日自動でnoteにブログを投稿 |
| Public/Private | **Private**（推奨） |
| Add a README | **チェックを入れる** |

4. 「Create repository」をクリック

---

# フォルダ構成を作る

## 必要なファイル構成

```
daily-note-blog/
├── .github/
│   └── workflows/
│       └── daily-post.yml    ← GitHub Actions設定
├── src/
│   ├── researcher.ts         ← リサーチャー
│   ├── writer.ts             ← ライター
│   ├── imageGenerator.ts     ← 画像生成
│   ├── publisher.ts          ← note投稿
│   └── main.ts               ← メイン処理
├── package.json
└── README.md
```

---

# ファイルを作成する方法

## GitHub上で直接作成

1. 「Add file」→「Create new file」
2. ファイル名に `src/main.ts` と入力
   - `/`を入れるとフォルダが自動作成される
3. コードを貼り付け
4. 「Commit changes」で保存

**この方法で1つずつファイルを作っていく**

---

# package.jsonを作成

## 依存関係の設定

ファイル名：`package.json`

```json
{
  "name": "daily-note-blog",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "start": "npx tsx src/main.ts"
  },
  "dependencies": {
    "@google/generative-ai": "^0.21.0",
    "node-fetch": "^3.3.2"
  },
  "devDependencies": {
    "tsx": "^4.7.0",
    "typescript": "^5.3.0"
  }
}
```

---

# Google AI Studioとは

## Gemini APIを無料で使えるサービス

- Googleが提供するAI開発プラットフォーム
- **無料枠が非常に大きい**（個人利用には十分）
- テキスト生成も画像生成も1つのAPIキーで利用可能

## 料金

| プラン | 制限 |
|--------|------|
| 無料 | 1分あたり15リクエスト |
| 無料 | 1日あたり1500リクエスト |

**毎日1記事なら余裕で無料！**

---

# Google AI StudioでAPIキー取得（1/2）

## 手順

1. ブラウザで **aistudio.google.com** にアクセス
2. Googleアカウントでログイン
3. 左メニューの「Get API key」をクリック
4. 「Create API key」ボタンをクリック
5. プロジェクトを選択（新規作成でもOK）

## プロジェクト名の例

- `daily-blog-project`
- `my-ai-project`

---

# Google AI StudioでAPIキー取得（2/2）

## APIキーをコピー

1. 作成されたAPIキーが表示される
2. 「Copy」ボタンでコピー

```
AIzaSy...（約40文字の英数字）
```

## 重要な注意

- **このキーは1度しか表示されない**
- 必ずメモ帳などに保存しておく
- 他人に絶対に見せない・共有しない
- 忘れた場合は「Get API key」から新規作成

---

# GitHub Secretsの設定（1/2）

## APIキーを安全に保存する

**重要：APIキーをコードに直接書いてはいけない**

## 手順

1. リポジトリの「Settings」タブをクリック
2. 左メニュー「Secrets and variables」→「Actions」
3. 「New repository secret」をクリック

---

# GitHub Secretsの設定（2/2）

## 登録するSecret

| Name | 内容 | 取得元 |
|------|------|--------|
| `GEMINI_API_KEY` | Gemini APIキー | Google AI Studio |
| `NOTE_ACCESS_TOKEN` | noteのトークン | note設定画面 |

## 入力方法

1. 「Name」に `GEMINI_API_KEY` と入力
2. 「Secret」にコピーしたAPIキーを貼り付け
3. 「Add secret」をクリック
4. NOTE_ACCESS_TOKENも同様に登録

---

# note APIアクセスの準備

## noteアカウントの設定

1. **note.com** にログイン
2. アカウント設定を開く
3. 「外部サービス連携」を確認

## 注意事項

- note APIは公式には限定公開
- 記事投稿には認証が必要
- 代替：ヘッドレスブラウザ（Playwright）を使う方法もある

---

# 環境変数の使い方

## コードでのSecret参照

```typescript
// GitHub ActionsではSecretsが環境変数になる
const geminiApiKey = process.env.GEMINI_API_KEY;
const noteToken = process.env.NOTE_ACCESS_TOKEN;

if (!geminiApiKey) {
  throw new Error('GEMINI_API_KEY が設定されていません');
}
```

**Secretsは `process.env.シークレット名` で取得できる**

---

# ローカルでのテスト用

## .envファイルを作成（ローカル用）

ファイル名：`.env`（GitHubには上げない）

```
GEMINI_API_KEY=あなたのAPIキー
NOTE_ACCESS_TOKEN=あなたのトークン
```

## .gitignoreに追加

```
.env
node_modules/
```

**APIキーがGitHubに公開されるのを防ぐ**

---

# リポジトリの確認

## ここまでの完成状態

```
daily-note-blog/
├── package.json ✓
├── .gitignore ✓
└── README.md ✓
```

## Secrets（Google AI Studioで取得）

- GEMINI_API_KEY ✓
- NOTE_ACCESS_TOKEN ✓

**次はGitHub Actionsのワークフローを作成！**

