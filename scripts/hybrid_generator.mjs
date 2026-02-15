#!/usr/bin/env node
/**
 * ハイブリッドスライド画像ジェネレーター
 *
 * 1. まず「スライド」モード（無料）で画像生成を試みる
 * 2. レート制限を検知したら Gemini API にフォールバック
 * 3. 各スライドごとに制限チェックを行い、API代を最小化
 *
 * Usage:
 *   node scripts/hybrid_generator.mjs <URL> --slides 6,16,17,18,21,22,23 --prompts prompts.json
 */

import puppeteer from 'puppeteer-core';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { execSync } from 'child_process';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = path.resolve(__dirname, '..');

const args = process.argv.slice(2);
let url = '', specificSlides = [], promptsFile = '';
let cdpPort = 18800, delayMs = 15000, genTimeout = 120000;

for (let i = 0; i < args.length; i++) {
  if (args[i] === '--slides') specificSlides = args[++i].split(',').map(Number);
  else if (args[i] === '--prompts') promptsFile = args[++i];
  else if (args[i] === '--cdp-port') cdpPort = parseInt(args[++i]);
  else if (args[i] === '--delay') delayMs = parseInt(args[++i]);
  else if (args[i] === '--gen-timeout') genTimeout = parseInt(args[++i]);
  else if (!args[i].startsWith('--')) url = args[i];
}

if (!url || specificSlides.length === 0) {
  console.error('Usage: node scripts/hybrid_generator.mjs <URL> --slides N,N,N --prompts prompts.json');
  process.exit(1);
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

// プロンプト読み込み
let prompts = {};
if (promptsFile && fs.existsSync(promptsFile)) {
  prompts = JSON.parse(fs.readFileSync(promptsFile, 'utf-8'));
}

// Gemini API用のスライドプロンプト
// api_prompts.json から読み込み。--api-prompts オプションで指定可能
let apiPromptsFile = '';
for (let i = 0; i < args.length; i++) {
  if (args[i] === '--api-prompts') apiPromptsFile = args[++i];
}

let slideContentPrompts = {};
if (apiPromptsFile && fs.existsSync(apiPromptsFile)) {
  slideContentPrompts = JSON.parse(fs.readFileSync(apiPromptsFile, 'utf-8'));
  console.log(`APIプロンプト読み込み: ${Object.keys(slideContentPrompts).length}件 (${apiPromptsFile})`);
} else {
  // レガシー: ハードコードされたプロンプト（後方互換）
  slideContentPrompts = {
  '6': `以下の内容のプレゼンテーションスライド画像を生成してください。16:9横向き、ダーク系の温かみのある背景デザイン。

タイトル: なぜ訪問看護で活用できるのか？
サブタイトル: 引きこもり支援との親和性

内容（箇条書き）:
・本人に直接アプローチが難しい場面が多い
・保護者を通じた間接的な支援が有効
・家庭内の関わり方を変えることで状況が動き出す
・訪問看護師が保護者のコーチ役になれる

デザイン: 茶色〜オレンジ系グラデーション背景、家のシルエット、プロフェッショナルで安心感のあるデザイン。テキストは白で大きく読みやすく。`,

  '16': `以下の内容のプレゼンテーションスライド画像を生成してください。16:9横向き。

タイトル: ブロークンレコード法
サブタイトル: 同じことを穏やかに繰り返す

内容:
子ども：「うるさい！放っておいて！」
親：「心配しているよ」
子ども：「来るなって言ってるだろ！」
親：「心配しているよ。ご飯はここに置いておくね」

ポイント:
・感情的にならない
・売り言葉に買い言葉をしない
・伝えたいメッセージだけを穏やかに繰り返す

デザイン: ダークブルー〜パープル背景、対話の吹き出しイメージ。テキストは白で読みやすく。`,

  '17': `以下の内容のプレゼンテーションスライド画像を生成してください。16:9横向き。

タイトル: 行動観察シートの活用
サブタイトル: 記録をつけると変化が見える

記録する項目:
・いつ（日時）
・どんな場面で（きっかけ）
・どんな行動があったか
・どう対応したか
・結果はどうだったか

ABC分析:
A（きっかけ）→ B（行動）→ C（結果）

デザイン: ダークティール背景、フローチャート矢印デザイン、記録用紙アイコン。テキストは白で読みやすく。`,

  '18': `以下の内容のプレゼンテーションスライド画像を生成してください。16:9横向き。

タイトル: スモールステップで考える
サブタイトル: いきなり大きな変化を求めない

引きこもりのステップ例:
1. 部屋のドアを開けている
2. リビングに顔を出す
3. 家族と食事を一緒にとる
4. 近所のコンビニに行く
5. 短時間の外出ができる

→ 各ステップで「できた」を認めていく
→ 後戻りしても責めない

デザイン: ダークブルー〜ゴールドグラデーション背景、階段を登るイメージ、5段のステップ。テキストは白で読みやすく。`,

  '21': `以下の内容のプレゼンテーションスライド画像を生成してください。16:9横向き。

タイトル: よくある質問
サブタイトル: Q&A

Q: 褒めるところが見つかりません
A: 「起きている」「生きている」も立派な行動です

Q: 無視したら余計に暴れました
A: 消去バーストです。一貫した対応を続けましょう

Q: 何年も引きこもっています。今からでも遅くない？
A: 関わり方を変えれば、関係性は必ず変化します

デザイン: ダークブルー〜シアン背景、Q&Aのクエスチョンマークアイコン、明るく開放的なイメージ。テキストは白で読みやすく。`,

  '22': `以下の内容のプレゼンテーションスライド画像を生成してください。16:9横向き。

タイトル: まとめ
サブタイトル: 本日のふりかえり

チェックリスト形式:
✓ 行動を3つに分けて対応を変える
✓ 好ましい行動には肯定的な注目を
✓ 25%ルール：少しでもできたら褒める
✓ CCQ：穏やかに・近づいて・静かに
✓ スモールステップで焦らない
✓ 保護者自身のケアも忘れずに

デザイン: ダークネイビー〜ゴールド背景、チェックリストデザイン、達成感と学びのイメージ。テキストは白で読みやすく。`,

  '23': `以下の内容のプレゼンテーションスライド画像を生成してください。16:9横向き。

タイトル: 参考文献・リソース
サブタイトル: もっと学びたい方へ

・井上雅彦『家庭で無理なく対応できるペアレント・トレーニング』
・岩坂英巳『困っている子をほめて育てるペアレント・トレーニング』
・まめの木クリニック ペアレントトレーニング資料
・鳥取大学 井上研究室

デザイン: ダークブラウン〜グレー背景、本棚のシルエット、学術的で落ち着いたデザイン。テキストは白で読みやすく。`,
  };
}

let currentSlideNum = 1;

async function navigateToSlide(page, n) {
  await page.mouse.click(700, 400);
  await sleep(200);
  await page.keyboard.press('Home');
  await sleep(500);
  currentSlideNum = 1;

  for (let i = 0; i < n - 1; i++) {
    await page.keyboard.press('PageDown');
    await sleep(250);
  }
  currentSlideNum = n;
  await sleep(300);
}

async function closePanel(page) {
  const f = page.mainFrame();
  const closeBtn = await f.evaluate(() => {
    const btns = document.querySelectorAll('[role="button"], button');
    for (const btn of btns) {
      const label = btn.getAttribute('aria-label') || '';
      if (label === '閉じる' || label === 'Close') {
        const rect = btn.getBoundingClientRect();
        if (rect.height > 0 && rect.x > 600) return { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 };
      }
    }
    return null;
  });
  if (closeBtn) {
    await page.mouse.click(closeBtn.x, closeBtn.y);
    await sleep(1000);
  } else {
    await page.keyboard.press('Escape');
    await sleep(500);
    await page.keyboard.press('Escape');
    await sleep(500);
  }
}

async function ensureSlideModePanel(page) {
  const f = page.mainFrame();

  // パネルが開いているか確認
  let hasTextarea = await f.evaluate(() => {
    const textareas = document.querySelectorAll('textarea');
    return Array.from(textareas).some(t => t.offsetHeight > 0);
  });

  if (!hasTextarea) {
    // パネルを開く
    for (let retry = 0; retry < 5; retry++) {
      await page.mouse.click(400, 300);
      await sleep(500);

      const panelBtn = await f.evaluate(() => {
        const btns = document.querySelectorAll('[role="button"], button');
        for (const btn of btns) {
          const label = btn.getAttribute('aria-label') || '';
          if (label === '画像作成サポート' || label === 'スライド画像を作成する') {
            const rect = btn.getBoundingClientRect();
            if (rect.height > 0) return { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 };
          }
        }
        return null;
      });

      if (panelBtn) {
        await page.mouse.click(panelBtn.x, panelBtn.y);
        await sleep(3000);
      }

      hasTextarea = await f.evaluate(() => {
        const textareas = document.querySelectorAll('textarea');
        return Array.from(textareas).some(t => t.offsetHeight > 0);
      });
      if (hasTextarea) break;
      console.log(`  パネルを開いています... (${retry + 2}/5)`);
    }

    if (!hasTextarea) throw new Error('パネルを開けませんでした');
  }

  // 「スライド」タブを選択
  const slideTabBox = await f.evaluate(() => {
    const tabs = document.querySelectorAll('[role="tab"]');
    for (const tab of tabs) {
      const text = (tab.textContent || '').trim();
      if (text === 'スライド' && tab.getAttribute('aria-selected') !== 'true') {
        const rect = tab.getBoundingClientRect();
        if (rect.height > 0) return { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 };
      }
    }
    return null;
  });
  if (slideTabBox) {
    await page.mouse.click(slideTabBox.x, slideTabBox.y);
    await sleep(1000);
  }
}

async function typePromptInPanel(page, prompt) {
  const f = page.mainFrame();
  const taInfo = await f.evaluate(() => {
    const textareas = document.querySelectorAll('textarea');
    for (const ta of textareas) {
      if (ta.offsetHeight > 0) {
        const rect = ta.getBoundingClientRect();
        return { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 };
      }
    }
    return null;
  });

  if (!taInfo) throw new Error('テキストエリアが見つかりません');

  // クリア
  await page.mouse.click(taInfo.x, taInfo.y);
  await sleep(200);
  await page.keyboard.down('Meta');
  await page.keyboard.press('a');
  await page.keyboard.up('Meta');
  await page.keyboard.press('Backspace');
  await sleep(300);

  // execCommandで入力
  await f.evaluate((text) => {
    const textareas = document.querySelectorAll('textarea');
    for (const ta of textareas) {
      if (ta.offsetHeight > 0) {
        ta.focus();
        ta.select();
        document.execCommand('insertText', false, text);
        return;
      }
    }
  }, prompt);
  await sleep(800);
}

async function clickCreateButton(page) {
  const f = page.mainFrame();
  const btnPos = await f.evaluate(() => {
    // aside内の作成ボタンを探す
    const aside = document.querySelector('aside[aria-label="画像作成サポート"]');
    const root = aside || document;
    const buttons = root.querySelectorAll('button, [role="button"]');
    for (const btn of buttons) {
      const label = btn.getAttribute('aria-label') || '';
      const classes = btn.className?.toString() || '';
      if ((label === '作成' || classes.includes('image-synthesis-creation-button')) && !btn.disabled) {
        const rect = btn.getBoundingClientRect();
        if (rect.height > 0) return { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 };
      }
    }
    return null;
  });

  if (!btnPos) {
    // keyboard.typeでフォールバック
    const taInfo = await f.evaluate(() => {
      const textareas = document.querySelectorAll('textarea');
      for (const ta of textareas) {
        if (ta.offsetHeight > 0) {
          const rect = ta.getBoundingClientRect();
          return { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2, value: ta.value };
        }
      }
      return null;
    });
    if (taInfo) {
      console.log('  作成ボタンが無効 → keyboard.typeで再入力...');
      await page.mouse.click(taInfo.x, taInfo.y);
      await sleep(200);
      await page.keyboard.down('Meta');
      await page.keyboard.press('a');
      await page.keyboard.up('Meta');
      await page.keyboard.press('Backspace');
      await sleep(300);
      const text = taInfo.value || '';
      await page.keyboard.type(text.substring(0, 200), { delay: 8 });
      await sleep(800);
    }

    // 再度ボタンを探す
    const retryBtn = await f.evaluate(() => {
      const aside = document.querySelector('aside[aria-label="画像作成サポート"]');
      const root = aside || document;
      const buttons = root.querySelectorAll('button, [role="button"]');
      for (const btn of buttons) {
        const label = btn.getAttribute('aria-label') || '';
        const classes = btn.className?.toString() || '';
        if ((label === '作成' || classes.includes('image-synthesis-creation-button')) && !btn.disabled) {
          const rect = btn.getBoundingClientRect();
          if (rect.height > 0) return { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 };
        }
      }
      return null;
    });
    if (!retryBtn) throw new Error('作成ボタンが有効になりません');
    await page.mouse.click(retryBtn.x, retryBtn.y);
  } else {
    await page.mouse.click(btnPos.x, btnPos.y);
  }
}

/**
 * レート制限チェック: 「作成」クリック後、タブが「画像」に切り替わるかどうか
 * @returns 'ok' (スライドモード生成中) or 'rate-limited' (画像タブに切り替わった)
 */
async function checkRateLimit(page) {
  await sleep(3000);
  const f = page.mainFrame();

  const activeTab = await f.evaluate(() => {
    const tabs = document.querySelectorAll('[role="tab"]');
    for (const tab of tabs) {
      if (tab.getAttribute('aria-selected') === 'true') {
        return (tab.textContent || '').trim();
      }
    }
    return '';
  });

  if (activeTab === '画像') {
    return 'rate-limited';
  }

  // 「作成しています」が表示されているかも確認
  const generating = await f.evaluate(() => {
    const btns = document.querySelectorAll('button, [role="button"]');
    for (const btn of btns) {
      const text = btn.getAttribute('aria-label') || btn.textContent?.trim() || '';
      if (text.includes('作成しています')) return true;
    }
    return false;
  });

  if (generating || activeTab === 'スライド') return 'ok';

  // 不明な状態 - もう少し待つ
  await sleep(3000);
  const recheck = await f.evaluate(() => {
    const tabs = document.querySelectorAll('[role="tab"]');
    for (const tab of tabs) {
      if (tab.getAttribute('aria-selected') === 'true') return (tab.textContent || '').trim();
    }
    return '';
  });
  return recheck === '画像' ? 'rate-limited' : 'ok';
}

/**
 * スライドモードでの生成完了待ち
 */
async function waitForSlideGeneration(page, timeoutMs) {
  const f = page.mainFrame();
  const start = Date.now();
  process.stdout.write('  生成待ち');

  while (Date.now() - start < timeoutMs) {
    const status = await f.evaluate(() => {
      // ダイアログチェック
      const dialogs = document.querySelectorAll('[role="dialog"]');
      for (const dialog of dialogs) {
        const style = window.getComputedStyle(dialog);
        if (style.display === 'none') continue;
        const rect = dialog.getBoundingClientRect();
        if (rect.height === 0) continue;
        const btns = dialog.querySelectorAll('button, [role="button"]');
        let hasGenerating = false;
        let hasAction = false;
        for (const btn of btns) {
          const text = btn.textContent?.trim() || btn.getAttribute('aria-label') || '';
          const r = btn.getBoundingClientRect();
          if (text.includes('作成しています') || text.includes('再作成しています')) hasGenerating = true;
          if (r.height > 0 && (text.includes('置き換える') || text.includes('その他のオプション') || text.includes('新しいスライドとして挿入'))) hasAction = true;
        }
        if (hasGenerating) return 'generating';
        if (hasAction) return 'ready';
      }

      // パネル内サムネイルチェック
      const aside = document.querySelector('aside[aria-label="画像作成サポート"]');
      if (aside) {
        const btns = aside.querySelectorAll('button, [role="button"]');
        for (const btn of btns) {
          const label = btn.getAttribute('aria-label') || btn.textContent?.trim() || '';
          if (label.includes('作成しています')) return 'generating';
        }
        const menuItems = aside.querySelectorAll('[role="menuitem"]');
        for (const item of menuItems) {
          if ((item.textContent || '').includes('プレビュー')) return 'thumbnail-ready';
        }
      }

      return 'waiting';
    });

    if (status === 'ready' || status === 'thumbnail-ready') {
      console.log(' 完了');
      return status;
    }
    process.stdout.write(status === 'generating' ? '>' : '.');
    await sleep(3000);
  }
  throw new Error(`生成タイムアウト (${timeoutMs / 1000}秒)`);
}

/**
 * 生成結果を挿入（「置き換える」ボタンクリック）
 */
async function insertSlideResult(page) {
  const f = page.mainFrame();

  // まずサムネイルをクリックしてプレビューダイアログを開く
  const thumbBox = await f.evaluate(() => {
    const aside = document.querySelector('aside[aria-label="画像作成サポート"]');
    if (!aside) return null;
    const menuItems = aside.querySelectorAll('[role="menuitem"]');
    let lastThumb = null;
    for (const item of menuItems) {
      if ((item.textContent || '').includes('プレビュー')) lastThumb = item;
    }
    if (!lastThumb) return null;
    lastThumb.scrollIntoView({ behavior: 'instant', block: 'center' });
    return true;
  });

  if (thumbBox) {
    await sleep(500);
    const coords = await f.evaluate(() => {
      const aside = document.querySelector('aside[aria-label="画像作成サポート"]');
      if (!aside) return null;
      const menuItems = aside.querySelectorAll('[role="menuitem"]');
      let lastThumb = null;
      for (const item of menuItems) {
        if ((item.textContent || '').includes('プレビュー')) lastThumb = item;
      }
      if (!lastThumb) return null;
      const rect = lastThumb.getBoundingClientRect();
      return { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 };
    });
    if (coords) {
      await page.mouse.click(coords.x, coords.y);
      await sleep(2000);
    }
  }

  // ダイアログ待ち
  process.stdout.write('  ダイアログ待ち');
  let dialogReady = false;
  for (let i = 0; i < 60; i++) {
    const check = await f.evaluate(() => {
      const dialogs = document.querySelectorAll('[role="dialog"]');
      for (const dialog of dialogs) {
        const style = window.getComputedStyle(dialog);
        if (style.display === 'none') continue;
        const rect = dialog.getBoundingClientRect();
        if (rect.height === 0) continue;
        const btns = dialog.querySelectorAll('button, [role="button"]');
        for (const btn of btns) {
          const text = btn.textContent?.trim() || btn.getAttribute('aria-label') || '';
          const r = btn.getBoundingClientRect();
          if (r.height > 0 && (text.includes('置き換える') || text.includes('その他のオプション') || text.includes('新しいスライドとして挿入'))) return 'ready';
        }
        return 'visible-no-buttons';
      }
      return 'waiting';
    });
    if (check === 'ready') { dialogReady = true; console.log(' OK'); break; }
    process.stdout.write('.');
    await sleep(1000);
  }

  if (!dialogReady) throw new Error('プレビューダイアログが表示されません');

  // 「置き換える」ボタンをクリック
  const actionBtn = await f.evaluate(() => {
    const dialogs = document.querySelectorAll('[role="dialog"]');
    for (const dialog of dialogs) {
      const style = window.getComputedStyle(dialog);
      if (style.display === 'none') continue;
      const rect = dialog.getBoundingClientRect();
      if (rect.height === 0) continue;
      const btns = dialog.querySelectorAll('button, [role="button"]');
      for (const btn of btns) {
        const text = btn.textContent?.trim() || '';
        const label = btn.getAttribute('aria-label') || '';
        if (text.includes('置き換える') || text.includes('新しいスライドとして挿入') || label.includes('置き換える')) {
          const r = btn.getBoundingClientRect();
          if (r.height > 0) return { x: r.x + r.width / 2, y: r.y + r.height / 2, text };
        }
      }
    }
    return null;
  });

  if (actionBtn) {
    await page.mouse.click(actionBtn.x, actionBtn.y);
    const action = actionBtn.text.includes('置き換える') ? 'replaced' : 'inserted-as-new-slide';
    console.log(`  「${actionBtn.text}」をクリック`);
    await sleep(3000);
    return action;
  }
  throw new Error('アクションボタンが見つかりません');
}

/**
 * Gemini APIでスライド画像を生成してセットする（Python呼び出し）
 */
async function generateWithGeminiAPI(presId, slideIndex, prompt) {
  console.log('  → Gemini API フォールバック実行中...');
  const escapedPrompt = prompt.replace(/'/g, "'\\''");
  const cmd = `cd "${PROJECT_ROOT}" && python3 scripts/gemini_slide_generator.py ${presId} ${slideIndex} '${escapedPrompt}'`;
  try {
    const output = execSync(cmd, { timeout: 120000, encoding: 'utf-8' });
    console.log(output.trim().split('\n').map(l => '    ' + l).join('\n'));
    return true;
  } catch (e) {
    console.error(`  ✗ Gemini API エラー: ${e.message}`);
    return false;
  }
}

/**
 * テキスト要素を削除（Python呼び出し）
 */
async function deleteTextElements(presId, slideNum) {
  const cmd = `cd "${PROJECT_ROOT}" && python3 scripts/delete_text_elements.py ${presId} ${slideNum}`;
  try {
    const output = execSync(cmd, { timeout: 30000, encoding: 'utf-8' });
    const lines = output.trim().split('\n');
    for (const line of lines) {
      console.log(`  テキスト削除: ${line.trim()}`);
    }
    return true;
  } catch (e) {
    console.warn(`  ⚠ テキスト削除失敗: ${e.message}`);
    return false;
  }
}

/**
 * 「新しいスライドとして挿入」の場合のAPI転送
 */
async function transferNewSlide(presId, targetSlideIndex) {
  const cmd = `cd "${PROJECT_ROOT}" && python3 scripts/transfer_new_slide.py ${presId} ${targetSlideIndex}`;
  try {
    const output = execSync(cmd, { timeout: 30000, encoding: 'utf-8' });
    console.log(`  API転送: ${output.trim()}`);
    return true;
  } catch (e) {
    console.warn(`  ⚠ API転送失敗: ${e.message}`);
    return false;
  }
}

// --- Main ---
async function main() {
  const presMatch = url.match(/\/d\/([a-zA-Z0-9_-]+)/);
  const presId = presMatch ? presMatch[1] : '';
  if (!presId) {
    console.error('プレゼンテーションIDが取得できません');
    process.exit(1);
  }

  console.log('=== ハイブリッドスライドジェネレーター ===');
  console.log(`対象スライド: ${specificSlides.join(', ')}`);
  console.log(`方式: スライドモード優先 → Gemini API フォールバック`);
  console.log(`プロンプト: ${Object.keys(prompts).length}件\n`);

  const browser = await puppeteer.connect({
    browserURL: `http://127.0.0.1:${cdpPort}`,
    defaultViewport: null,
    protocolTimeout: 120000,
  });

  const pages = await browser.pages();
  let page = pages.find(p => p.url().includes('docs.google.com/presentation'));
  if (!page) {
    page = pages[0] || await browser.newPage();
    await page.goto(url, { waitUntil: 'networkidle2', timeout: 60000 });
    await sleep(5000);
  }

  // ウィンドウ復元
  try {
    const client = await page.target().createCDPSession();
    const { windowId } = await client.send('Browser.getWindowForTarget');
    const { bounds } = await client.send('Browser.getWindowBounds', { windowId });
    if (bounds.windowState === 'minimized') {
      await client.send('Browser.setWindowBounds', {
        windowId, bounds: { windowState: 'normal', width: 1440, height: 900 }
      });
      console.log('ウィンドウを復元しました');
      await sleep(2000);
    }
    await client.detach();
  } catch (e) { /* ignore */ }

  const results = [];
  const startTime = Date.now();
  let rateLimited = false; // 一度制限検知後は以降全てAPIを使用

  for (let si = 0; si < specificSlides.length; si++) {
    const slideNum = specificSlides[si];
    const slideIndex = slideNum - 1;
    console.log(`\n[${si + 1}/${specificSlides.length}] スライド${slideNum}`);

    try {
      // 1. スライドに移動
      await navigateToSlide(page, slideNum);
      console.log('  移動完了');

      let method = '';

      if (rateLimited) {
        // 既に制限済み → 直接APIを使用
        console.log('  レート制限中 → Gemini API使用');
        method = 'api';
      } else {
        // 2. スライドモードを試す
        await ensureSlideModePanel(page);
        const jpPrompt = prompts[String(slideNum)] || `このスライドをプロフェッショナルなデザインにリデザインしてください。`;
        console.log(`  プロンプト: ${jpPrompt.substring(0, 50)}...`);
        await typePromptInPanel(page, jpPrompt);

        // 3. 「作成」をクリック
        await clickCreateButton(page);
        console.log('  「作成」クリック → レート制限チェック中...');

        // 4. レート制限チェック
        const limitStatus = await checkRateLimit(page);

        if (limitStatus === 'rate-limited') {
          console.log('  ⚠ レート制限検知！→ Gemini APIに切り替え');
          rateLimited = true;
          method = 'api';

          // パネルの操作をキャンセル
          await page.keyboard.press('Escape');
          await sleep(500);
          await closePanel(page);
          await sleep(1000);
        } else {
          console.log('  ✓ スライドモード利用可能');
          method = 'slide-mode';
        }
      }

      if (method === 'slide-mode') {
        // スライドモードで生成続行
        const genStatus = await waitForSlideGeneration(page, genTimeout);
        const action = await insertSlideResult(page);
        console.log(`  挿入結果: ${action}`);

        if (action === 'inserted-as-new-slide') {
          await transferNewSlide(presId, slideIndex);
          await sleep(2000);
          await page.keyboard.press('Home');
          await sleep(1000);
          currentSlideNum = 1;
          await navigateToSlide(page, slideNum);
        }

        // テキスト要素を削除
        await sleep(2000);
        await deleteTextElements(presId, slideNum);

        results.push({ slide: slideNum, status: 'success', method: 'slide-mode' });

      } else if (method === 'api') {
        // Gemini APIで生成
        const apiPrompt = slideContentPrompts[String(slideNum)];
        if (!apiPrompt) {
          console.error(`  ✗ APIプロンプトが未定義: スライド${slideNum}`);
          results.push({ slide: slideNum, status: 'error', method: 'api', error: 'プロンプト未定義' });
          continue;
        }

        const success = await generateWithGeminiAPI(presId, slideIndex, apiPrompt);
        results.push({ slide: slideNum, status: success ? 'success' : 'error', method: 'api' });
      }

    } catch (err) {
      console.error(`  ✗ エラー: ${err.message}`);
      results.push({ slide: slideNum, status: 'error', error: err.message });

      // リカバリ
      try {
        await page.keyboard.press('Escape');
        await sleep(500);
        await page.keyboard.press('Escape');
        await sleep(500);
      } catch (e) {}
    }

    // クールダウン
    if (si < specificSlides.length - 1) {
      const cooldown = rateLimited ? 5000 : delayMs;
      console.log(`  クールダウン: ${cooldown / 1000}秒...`);
      await sleep(cooldown);
    }
  }

  // サマリー
  const totalTime = ((Date.now() - startTime) / 1000).toFixed(0);
  const successCount = results.filter(r => r.status === 'success').length;
  const slideMode = results.filter(r => r.method === 'slide-mode').length;
  const apiMode = results.filter(r => r.method === 'api').length;

  console.log('\n=== 結果 ===');
  console.log(`成功: ${successCount} / ${results.length}`);
  console.log(`スライドモード: ${slideMode}, API: ${apiMode}`);
  console.log(`所要時間: ${totalTime}秒`);
  for (const r of results) {
    console.log(`  スライド${r.slide}: ${r.status} (${r.method || 'unknown'})`);
  }

  const outPath = path.join(PROJECT_ROOT, 'hybrid_generation_results.json');
  fs.writeFileSync(outPath, JSON.stringify({ timestamp: new Date().toISOString(), results }, null, 2));

  browser.disconnect();
}

main().catch(err => { console.error('Fatal:', err); process.exit(1); });
