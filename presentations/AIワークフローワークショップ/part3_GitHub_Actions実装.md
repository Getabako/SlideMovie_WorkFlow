# AIワークフローワークショップ
## Part3: GitHub Actions実装（約1時間）

---

# GitHub Actionsとは

## 自動化ワークフローのサービス

- コードがプッシュされたら自動でテスト
- **毎日決まった時間に処理を実行**
- 無料枠：月2000分（十分すぎる）

**今日は「毎朝6時に自動実行」を設定する**

---

# ワークフローファイルを作成

## 場所

```
.github/workflows/daily-post.yml
```

## 作成方法

1. 「Add file」→「Create new file」
2. ファイル名に `.github/workflows/daily-post.yml` と入力
3. 次のスライドのコードを貼り付け

---

# daily-post.yml（1/2）

## ワークフロー定義

```yaml
name: Daily Blog Post

on:
  schedule:
    # 毎日朝6時（日本時間）に実行
    # cronはUTCなので21時 = 日本時間6時
    - cron: '0 21 * * *'
  workflow_dispatch:
    # 手動実行も可能にする

jobs:
  post:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
```

---

# daily-post.yml（2/2）

## 続き

```yaml
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install dependencies
        run: npm install

      - name: Run blog post script
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          NOTE_ACCESS_TOKEN: ${{ secrets.NOTE_ACCESS_TOKEN }}
        run: npm start
```

---

# cronの書き方

## スケジュール設定

```
┌───────────── 分 (0 - 59)
│ ┌───────────── 時 (0 - 23) ※UTC
│ │ ┌───────────── 日 (1 - 31)
│ │ │ ┌───────────── 月 (1 - 12)
│ │ │ │ ┌───────────── 曜日 (0 - 6)
│ │ │ │ │
* * * * *
```

## 例

| cron | 意味 |
|------|------|
| `0 21 * * *` | 毎日21:00 UTC（日本時間6:00） |
| `0 0 * * *` | 毎日0:00 UTC（日本時間9:00） |
| `0 21 * * 1-5` | 平日のみ6:00 |

---

# メイン処理を作成

## src/main.ts

```typescript
import { GoogleGenerativeAI } from '@google/generative-ai';

async function main() {
  console.log('🚀 Daily Blog Post - 開始');

  // 1. 今日のトピックを決定
  const topic = getTodaysTopic();
  console.log(`📝 今日のトピック: ${topic}`);

  // 2. リサーチ
  const research = await runResearcher(topic);

  // 3. 記事執筆
  const article = await runWriter(research);

  // 4. 画像生成
  const imageUrl = await runImageGenerator(article.title);

  // 5. note投稿
  await runPublisher(article, imageUrl);

  console.log('✅ 投稿完了！');
}

main().catch(console.error);
```

---

# トピック選定

## getTodaysTopic関数

```typescript
function getTodaysTopic(): string {
  const topics: { [key: number]: string } = {
    0: 'AIの最新トレンドと活用法',      // 日曜
    1: 'プログラミング初心者向けTips',   // 月曜
    2: 'ChatGPTの便利な使い方',         // 火曜
    3: 'Webサービス開発入門',           // 水曜
    4: '生産性を上げるツール紹介',       // 木曜
    5: '週末に学べる技術書レビュー',     // 金曜
    6: 'エンジニアのキャリア設計',       // 土曜
  };

  const dayOfWeek = new Date().getDay();
  return topics[dayOfWeek];
}
```

---

# リサーチャーの実装

## src/researcher.ts

```typescript
import { GoogleGenerativeAI } from '@google/generative-ai';

export async function runResearcher(topic: string) {
  const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY!);
  const model = genAI.getGenerativeModel({ model: 'gemini-2.0-flash' });

  const prompt = `あなたは優秀なリサーチャーです。
以下のトピックについて、ブログ記事を書くための情報を調査してください。

【トピック】
${topic}

【調査してほしい内容】
1. このトピックの最新トレンドや動向
2. 読者が知りたい具体的な事実やデータ
3. 初心者にもわかりやすい説明のポイント
4. 記事に含めるべき重要なキーワード5つ

【出力形式】
JSON形式で出力してください。`;

  const result = await model.generateContent(prompt);
  return JSON.parse(result.response.text());
}
```

---

# ライターの実装

## src/writer.ts

```typescript
export async function runWriter(research: any) {
  const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY!);
  const model = genAI.getGenerativeModel({ model: 'gemini-2.0-flash' });

  const prompt = `あなたはプロのブログライターです。
以下の調査結果をもとに、noteに投稿するブログ記事を書いてください。

【調査結果】
${JSON.stringify(research, null, 2)}

【記事の要件】
- タイトル：読みたくなる魅力的なもの（30文字以内）
- 文字数：1500〜2000文字
- 構成：導入 → 本文3セクション → まとめ
- 各セクションに見出し（h2）をつける

【出力形式】
JSON形式で出力してください。`;

  const result = await model.generateContent(prompt);
  return JSON.parse(result.response.text());
}
```

---

# 画像生成の実装

## src/imageGenerator.ts

```typescript
export async function runImageGenerator(title: string) {
  const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY!);
  const model = genAI.getGenerativeModel({
    model: 'gemini-2.0-flash-exp-image-generation'
  });

  const prompt = `以下のブログ記事のアイキャッチ画像を生成してください。

【記事タイトル】
${title}

【画像の要件】
- スタイル：モダンでクリーンなイラスト調
- 色使い：明るく親しみやすい配色
- 構図：中央に主要なモチーフを配置
- テキストは含めない
- 16:9のアスペクト比`;

  const result = await model.generateContent(prompt);
  // 画像データを取得して保存
  return result.response.candidates[0].content.parts[0];
}
```

---

# パブリッシャーの実装

## src/publisher.ts

```typescript
export async function runPublisher(article: any, imageUrl: string) {
  // noteへの投稿処理
  const noteApiUrl = 'https://note.com/api/v1/notes';

  const body = {
    title: article.title,
    body: formatArticleBody(article, imageUrl),
    status: 'draft', // 下書きで投稿（確認後に公開）
    hashtags: ['AI', 'プログラミング', '自動投稿']
  };

  const response = await fetch(noteApiUrl, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${process.env.NOTE_ACCESS_TOKEN}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(body)
  });

  if (!response.ok) {
    throw new Error(`note投稿エラー: ${response.status}`);
  }

  console.log('📮 noteに下書き投稿完了');
}
```

---

# 手動実行でテスト

## ワークフローを手動で動かす

1. GitHubリポジトリを開く
2. 「Actions」タブをクリック
3. 左側で「Daily Blog Post」を選択
4. 「Run workflow」ボタンをクリック
5. 実行されるのを確認

**まずは手動で動くか確認しよう！**

---

# 実行結果の確認

## Actionsタブでログを確認

1. 実行中のワークフローをクリック
2. 「post」ジョブをクリック
3. 各ステップのログが見られる

## 成功した場合

✅ 緑のチェックマークが表示
→ noteの下書きを確認

## 失敗した場合

❌ 赤いバツマークが表示
→ 次のPartでエラー対応を学ぶ

