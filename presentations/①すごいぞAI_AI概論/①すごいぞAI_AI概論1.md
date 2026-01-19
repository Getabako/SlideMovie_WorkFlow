---
marp: true
theme: default
paginate: true
---

<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&display=swap');
section {
  font-family: 'Noto Sans JP', 'Hiragino Sans', 'Hiragino Kaku Gothic ProN', 'Yu Gothic', 'Meiryo', sans-serif;
}
</style>

![bg right](images/001________20_____30______________.png)
# すごいぞAI！AI概論

<small>秋田県IT女性育成プログラム</small>
---

![bg right](images/002_______________________________.png)
## 本日の目標

- AIとは何か理解する
- AIが私たちの生活にどう役立つか理解する
- Geminiの基本的な使い方を学ぶ
- AIを仕事で活用するイメージを持つ
---

![bg right](images/003________20_____30______________.png)
## 講師紹介

<small>

if(塾)塾頭高崎翔太
エンジニア、コンサルタント、高校教諭、臨床心理士

<small>

元々は、(株)LITALICOにて不登校や発達特性のある子へのカウンセリングやゲームの開発を行う。
秋田県に移住してからはテレビ番組のゲーム開発、行政でのコンサルタント、高校教諭などをしながら、高校で出会った生徒たちとif(塾)を開業
現在はAIと起業の使い方、やり方をif(塾)を通して拡大中！

</small>

</small>

---

![bg right:45%](images/001.png)
# 第1部：AIって何？
---

![bg right]()
## AIとは？

**Artificial Intelligence（人工知能）**

人間の知的な活動をコンピュータで再現する技術

- 学習する
- 理解する
- 判断する
- 創造する
---

![bg right:45%](images/002.png)
## AIの種類

### 特化型AI（Narrow AI）
- 特定のタスクに特化
- 現在実用化されているAI
- 例：音声認識、画像認識、翻訳

### 汎用AI（General AI）
- 人間のようにあらゆることができる
- まだ実現していない
---

![bg right:45%](images/003.png)
## 生成AI（Generative AI）とは？

**新しいコンテンツを生み出すAI**

- 文章を書く
- 画像を作る
- 音楽を作る
- プログラムコードを書く
---

![bg right:45%](images/004.png)
## 代表的な生成AI

| AI名 | 提供元 | 得意なこと |
|------|--------|-----------|
| **Google Gemini** | Google | 文章生成、検索、Google連携 |
| ChatGPT | OpenAI | 対話、文章生成 |
| Claude | Anthropic | 文章生成、分析 |
| Copilot | Microsoft | 文章生成、Office連携 |
---

![bg right:45%](images/005.png)
## なぜ今AIが注目されているのか？

### 2022年11月：転換点
- ChatGPTの登場
- 誰でも使えるAIが実現
- 仕事の効率が劇的に向上

### 日本の状況
- DX（デジタルトランスフォーメーション）推進
- 人手不足の解決策
- 新しいスキルとして評価
---

![bg right:45%](images/006.png)
# 第2部：Google Geminiを使ってみよう
---

![bg right:45%](images/007.png)
## Google Geminiとは？

Googleが開発した最新の生成AI

### 特徴
- 無料で使える（有料版もあり）
- Google検索と連携
- Gmail、Google Docs、スプレッドシートと連携
- 日本語に強い
- 画像生成、動画生成、資料作成、リサーチなど幅広い活用ができる
---

![bg right:45%](images/008.png)
## Geminiにアクセスしよう

1. ブラウザで **gemini.google.com** にアクセス
2. Googleアカウントでログイン
3. すぐに使い始められる！
---

![bg right:45%](images/009.png)
## Geminiの画面構成

- **チャット欄**：質問や指示を入力
- **応答エリア**：Geminiの回答が表示
- **履歴**：過去の会話を確認
- **設定**：言語やモデルを選択
---

![bg right:45%](images/010.png)
## プロンプトとは？

**AIに対する質問や指示のこと**
---

![bg right:45%](images/011.png)
## プロンプトの例：悪い例

❌ **悪い例**
```
メールを書いて
```

### 何が足りない？
- 誰に送るメール？
- どんな内容？
- どんなトーン？
