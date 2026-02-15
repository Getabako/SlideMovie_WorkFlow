# バグ修正タスク: slide_image_generator.mjs

## 概要
`scripts/slide_image_generator.mjs` はGoogle Slidesの「画像作成サポート」パネルをPuppeteerで自動操作するスクリプト。
OpenClawブラウザ(CDPポート18800)に接続して動作する。

## 動作確認済み（触らなくていい）
- ✅ CDP接続 (`http://127.0.0.1:18800`)
- ✅ スライドナビゲーション（フィルムストリップのmouse.wheelスクロール+座標クリック）
- ✅ 画像作成サポートパネルの開閉
- ✅ テキストエリアへのプロンプト入力・送信
- ✅ 生成完了検出（ダイアログの「挿入」ボタン存在で判定）

## 修正が必要な箇所（2つ）

### 問題1: 「その他のオプション」→「挿入」のドロップダウン操作

**現在の状況:** `insertImageToSlide()`関数で、プレビューダイアログの「その他のオプション」(▼)ボタンをクリック→ドロップダウンメニューから「挿入」を選択する処理。

**問題:** ドロップダウンメニューの「挿入」テキストが見つからない or クリックが効かない。

**UIの構造（スクショから確認済み）:**
- プレビューダイアログ内に「新しいスライドとして挿入します」ボタンがある
- その右に▼ボタン（aria-label="その他のオプション"、role="button"）がある
- ▼をクリックするとドロップダウンが出て「挿入」メニュー項目がある
- 「挿入」を選ぶと**現在のスライドに画像が挿入される**（「新しいスライドとして」ではない）

**重要:** Google SlidesのカスタムUIはDOM `.click()` が効かない。必ず `page.mouse.click(x, y)` で座標ベースのクリックを使うこと。

### 問題2: 「画像を背景に設定」が右クリックメニューで見つからない

**現在の状況:** `setAsBackground()`関数で、挿入された画像を右クリック→コンテキストメニューから「画像を背景に設定」を選択する処理。

**問題:** 右クリックメニューに「画像を背景に設定」が出てこない。

**考えられる原因:**
1. 画像が正しく挿入されていない（問題1が先に直る必要あり）
2. 右クリックの座標がスライドの画像オブジェクト上でない
3. 画像がスライド上のオブジェクトとして選択されていない

**UIの手順（手動操作で確認済み）:**
1. 挿入された画像がスライド上に表示される
2. 画像を右クリック → コンテキストメニューが出る
3. 「画像を背景に設定」をクリック
4. 画像が背景になる
5. 前面に残った画像オブジェクトをDelete

## テスト方法

```bash
# OpenClawブラウザが起動済みであること（CDPポート18800）
# Google Slidesが開いてログイン済みであること

# スライド5で単体テスト
node scripts/slide_image_generator.mjs "https://docs.google.com/presentation/d/1GeVV-1SvCk0r-htG9Di9CP2yrAxuT1KJfp5eX4G1tWA/edit" --from 5 --to 5

# 成功すると:
# [5/5] スライド5
#   移動完了
#   ...
#   ✓ 成功 (XX秒)
```

## 技術的な注意点

1. **座標ベースのクリック必須**: `element.click()` は効かない。`frame.evaluate()`で座標取得→`page.mouse.click(x, y)`を使う
2. **フレーム**: Google Slidesはサブフレームあり。`page.frames().find(f => f.url().includes('slide='))` がメインフレーム
3. **role="button"**: Google Slidesのボタンは`<button>`タグではなく`<div role="button">`が多い。`querySelectorAll('button, [role="button"]')`で両方取る
4. **Undo**: テスト後にCtrl+Zで戻せる。失敗した挿入は`page.keyboard.down('Meta'); page.keyboard.press('z'); page.keyboard.up('Meta');`で戻る

## ファイル
- スクリプト: `scripts/slide_image_generator.mjs`
- 修正対象関数: `insertImageToSlide()` (約380行目) と `setAsBackground()` (約440行目)
