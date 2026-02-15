#!/usr/bin/env node
/**
 * Google Slides 画像作成サポート 自動化スクリプト
 * 
 * OpenClawブラウザ(CDP)に接続して、Googleスライドの「画像作成サポート」パネルを
 * 自動操作し、各スライドの背景画像を生成・適用する。
 * 
 * 使い方:
 *   node scripts/slide_image_generator.mjs <URL> [--from N] [--to N] [--prompts prompts.json]
 * 
 * オプション:
 *   --from N         開始スライド番号 (デフォルト: 1)
 *   --to N           終了スライド番号 (デフォルト: 最終スライド)
 *   --prompts FILE   プロンプトJSONファイル {"1": "prompt", "2": "prompt", ...}
 *   --cdp-port PORT  CDPポート (デフォルト: 18800)
 *   --dry-run        実際に適用せず、プロンプト確認のみ
 *   --delay MS       スライド間の待機時間ms (デフォルト: 3000)
 *   --gen-timeout MS 生成タイムアウトms (デフォルト: 120000)
 *   --slides N,N,N   処理するスライド番号をカンマ区切りで指定（--from/--toより優先）
 *   --cooldown MS    レート制限対策: スライド間の追加クールダウンms (デフォルト: 0)
 */

import puppeteer from 'puppeteer-core';
import fs from 'fs';
import path from 'path';

// --- 引数パース ---
const args = process.argv.slice(2);
let url = '', fromSlide = 1, toSlide = -1, promptsFile = '';
let cdpPort = 18800, dryRun = false, delayMs = 8000, genTimeout = 120000;
let specificSlides = []; // --slides オプションで指定されたスライド番号
let cooldownMs = 0; // レート制限対策の追加クールダウン

for (let i = 0; i < args.length; i++) {
  if (args[i] === '--from') fromSlide = parseInt(args[++i]);
  else if (args[i] === '--to') toSlide = parseInt(args[++i]);
  else if (args[i] === '--prompts') promptsFile = args[++i];
  else if (args[i] === '--cdp-port') cdpPort = parseInt(args[++i]);
  else if (args[i] === '--dry-run') dryRun = true;
  else if (args[i] === '--delay') delayMs = parseInt(args[++i]);
  else if (args[i] === '--gen-timeout') genTimeout = parseInt(args[++i]);
  else if (args[i] === '--slides') specificSlides = args[++i].split(',').map(Number).filter(n => n > 0);
  else if (args[i] === '--cooldown') cooldownMs = parseInt(args[++i]);
  else if (!args[i].startsWith('--')) url = args[i];
}

if (!url) {
  console.error('Usage: node scripts/slide_image_generator.mjs <Google Slides URL> [options]');
  process.exit(1);
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

/**
 * Google Slidesのメインフレームを取得
 */
function getSlideFrame(page) {
  return page.frames().find(f => f.url().includes('slide=')) || page.mainFrame();
}

/**
 * スライド数を取得
 */
async function getSlideCount(frame) {
  return frame.evaluate(() => document.querySelectorAll('g.punch-filmstrip-thumbnail').length);
}

// Track current slide number for keyboard navigation
let currentSlideNum = 1;

/**
 * N番目のスライドに移動（キーボードベース）
 */
async function navigateToSlide(page, frame, n) {
  // Click on the main canvas area first to ensure keyboard focus
  await page.mouse.click(700, 400);
  await sleep(200);

  if (n === 1 && currentSlideNum === 1) {
    // First slide - press Home to ensure we're at the start
    await page.keyboard.press('Home');
    await sleep(500);
    currentSlideNum = 1;
    return;
  }

  // Calculate how many steps to move
  const diff = n - currentSlideNum;
  
  if (diff === 0) return;

  // Use Page Down/Up for navigation  
  const key = diff > 0 ? 'PageDown' : 'PageUp';
  const steps = Math.abs(diff);

  for (let i = 0; i < steps; i++) {
    await page.keyboard.press(key);
    await sleep(300);
  }
  
  currentSlideNum = n;
  await sleep(300);
}

/**
 * 画像作成サポートパネルを確認・開く
 */
async function ensureImagePanel(page, frame) {
  // テキストエリアが見えるかで判定
  const hasTextarea = await frame.evaluate(() => {
    const textareas = document.querySelectorAll('textarea');
    return Array.from(textareas).some(t => t.offsetHeight > 0);
  });
  
  if (!hasTextarea) {
    console.log('  画像作成サポートパネルを開いています...');
    // 座標ベースでクリック（DOM.clickがGoogle Slidesで効かないため）
    const btnBox = await frame.evaluate(() => {
      // サイドバーの「画像作成サポート」ボタン
      const btn = document.querySelector('[aria-label="画像作成サポート"][role="button"]');
      if (btn) {
        const rect = btn.getBoundingClientRect();
        return { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 };
      }
      // ツールバーの「スライド画像を作成する」ボタン
      const allBtns = document.querySelectorAll('[role="button"], button');
      for (const b of allBtns) {
        const label = b.getAttribute('aria-label') || '';
        if (label.includes('スライド画像を作成') || label.includes('画像作成サポート')) {
          const rect = b.getBoundingClientRect();
          return { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 };
        }
      }
      return null;
    });
    
    if (btnBox) {
      await page.mouse.click(btnBox.x, btnBox.y);
      await sleep(2500);
    } else {
      console.warn('  ⚠ 画像作成サポートボタンが見つかりません');
    }
  }
}

/**
 * 「スライド」タブが選択されていることを確認
 * タブクリックが効かない場合はパネルを閉じてツールバーから再オープン
 */
async function ensureSlideTab(page, frame) {
  const isSlideTab = await frame.evaluate(() => {
    const tabs = document.querySelectorAll('[role="tab"]');
    for (const tab of tabs) {
      if (tab.textContent?.includes('スライド') && tab.getAttribute('aria-selected') === 'true') return true;
    }
    return false;
  });
  if (isSlideTab) return;

  // まず座標ベースクリックを試す
  const tabBox = await frame.evaluate(() => {
    const tabs = document.querySelectorAll('[role="tab"]');
    for (const tab of tabs) {
      if (tab.textContent?.includes('スライド') && tab.getAttribute('aria-selected') !== 'true') {
        const rect = tab.getBoundingClientRect();
        if (rect.width > 0 && rect.height > 0) {
          return { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 };
        }
      }
    }
    return null;
  });
  if (tabBox) {
    await page.mouse.click(tabBox.x, tabBox.y);
    await sleep(800);
    const switched = await frame.evaluate(() => {
      const tabs = document.querySelectorAll('[role="tab"]');
      for (const tab of tabs) {
        if (tab.textContent?.includes('スライド') && tab.getAttribute('aria-selected') === 'true') return true;
      }
      return false;
    });
    if (switched) return;
  }

  // クリックが効かない場合: パネルを閉じてツールバーから再オープン
  console.log('  タブ切替: パネルを閉じて再オープン...');
  const closeBox = await frame.evaluate(() => {
    const btns = document.querySelectorAll('button, [role="button"]');
    for (const btn of btns) {
      const label = btn.getAttribute('aria-label') || '';
      if (label === '閉じる') {
        const rect = btn.getBoundingClientRect();
        if (rect.x > 400 && rect.y < 120 && rect.height > 0) {
          return { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 };
        }
      }
    }
    return null;
  });
  if (closeBox) {
    await page.mouse.click(closeBox.x, closeBox.y);
    await sleep(2000);
  }
  // ツールバーの「スライド画像を作成する」ボタンで再オープン
  const toolbarBtn = await frame.evaluate(() => {
    const btns = document.querySelectorAll('[role="button"]');
    for (const btn of btns) {
      const label = btn.getAttribute('aria-label') || '';
      if (label === 'スライド画像を作成する') {
        const rect = btn.getBoundingClientRect();
        if (rect.height > 0) return { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 };
      }
    }
    return null;
  });
  if (toolbarBtn) {
    await page.mouse.click(toolbarBtn.x, toolbarBtn.y);
    await sleep(3000);
  }
}

/**
 * 「作成」ボタンの有効状態を確認
 * aside 内部 → グローバル の順で検索
 */
async function isCreateBtnEnabled(frame) {
  return frame.evaluate(() => {
    // 検索対象: aside内 → image-synthesis-creation-button → 全ボタン
    const aside = document.querySelector('aside[aria-label="画像作成サポート"]');
    const searchRoots = aside ? [aside, document] : [document];
    for (const root of searchRoots) {
      const buttons = root.querySelectorAll('button, [role="button"]');
      for (const btn of buttons) {
        const label = btn.getAttribute('aria-label') || '';
        const text = btn.textContent?.trim() || '';
        const classes = btn.className?.toString() || '';
        // 「作成」ボタン: aria-label="作成" or image-synthesis-creation-button
        if (((label === '作成' || text === '作成') && !classes.includes('作成しています'))
            || classes.includes('image-synthesis-creation-button')) {
          if (!btn.disabled) {
            const rect = btn.getBoundingClientRect();
            if (rect.height > 0) return true;
          }
        }
      }
    }
    return false;
  });
}

/**
 * テキストエリアをクリアしてフォーカス
 */
async function clearTextarea(page, x, y) {
  await page.mouse.click(x, y);
  await sleep(200);
  await page.keyboard.down('Meta');
  await page.keyboard.press('a');
  await page.keyboard.up('Meta');
  await sleep(100);
  await page.keyboard.press('Backspace');
  await sleep(200);
}

/**
 * 画像作成サポートパネルをリセット（閉じて再度開く）
 */
async function resetImagePanel(page, frame) {
  console.log('  パネルをリセット...');
  // パネルの閉じるボタンを探す
  const closeBox = await frame.evaluate(() => {
    const aside = document.querySelector('aside[aria-label="画像作成サポート"]');
    if (!aside) return null;
    const btns = aside.querySelectorAll('button, [role="button"]');
    for (const btn of btns) {
      const label = btn.getAttribute('aria-label') || '';
      if (label === '閉じる' || label === 'Close') {
        const rect = btn.getBoundingClientRect();
        if (rect.height > 0) return { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 };
      }
    }
    return null;
  });
  if (closeBox) {
    await page.mouse.click(closeBox.x, closeBox.y);
    await sleep(1500);
  }
  await ensureImagePanel(page, frame);
  // await ensureSlideTab(page, frame); // Skip - works with Image tab too
  await sleep(500);
}

/**
 * テキストエリアを検出してフォーカスする
 */
async function findAndFocusTextarea(page, frame) {
  const info = await frame.evaluate(() => {
    // 画像作成サポートパネル内のtextareaを優先
    const aside = document.querySelector('aside[aria-label="画像作成サポート"]');
    if (aside) {
      const textareas = aside.querySelectorAll('textarea');
      for (const ta of textareas) {
        if (ta.offsetHeight > 0 && ta.offsetWidth > 0) {
          const rect = ta.getBoundingClientRect();
          return { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2, found: true };
        }
      }
    }
    // フォールバック: ページ上のtextarea
    const textareas = document.querySelectorAll('textarea');
    for (const ta of textareas) {
      if (ta.offsetHeight > 0 && ta.offsetWidth > 0) {
        const rect = ta.getBoundingClientRect();
        return { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2, found: true };
      }
    }
    return { found: false };
  });
  if (info.found) {
    // トリプルクリックで全テキスト選択
    await page.mouse.click(info.x, info.y, { clickCount: 3 });
    await sleep(200);
  }
  return info;
}

/**
 * プロンプトを入力して送信
 */
async function submitPrompt(page, frame, prompt) {
  let textareaInfo = await findAndFocusTextarea(page, frame);
  if (!textareaInfo.found) {
    throw new Error('テキストエリアが見つかりません');
  }

  // Method 1: execCommand('insertText') — ブラウザネイティブの入力シミュレーション
  await clearTextarea(page, textareaInfo.x, textareaInfo.y);
  await frame.evaluate((text) => {
    const aside = document.querySelector('aside[aria-label="画像作成サポート"]');
    const textareas = (aside || document).querySelectorAll('textarea');
    for (const ta of textareas) {
      if (ta.offsetHeight > 0 && ta.offsetWidth > 0) {
        ta.focus();
        ta.select();
        document.execCommand('insertText', false, text);
        return;
      }
    }
  }, prompt);
  await sleep(800);

  // テキストエリアの内容を確認
  const taValue = await frame.evaluate(() => {
    const aside = document.querySelector('aside[aria-label="画像作成サポート"]');
    const textareas = (aside || document).querySelectorAll('textarea');
    for (const ta of textareas) {
      if (ta.offsetHeight > 0 && ta.offsetWidth > 0) return ta.value?.substring(0, 50) || '(empty)';
    }
    return '(not found)';
  });

  // 「作成」ボタン状態をデバッグ（aside内 → グローバル）
  const btnDebug = await frame.evaluate(() => {
    const aside = document.querySelector('aside[aria-label="画像作成サポート"]');
    const root = aside || document;
    const buttons = root.querySelectorAll('button, [role="button"]');
    const btnList = [];
    for (const btn of buttons) {
      const label = btn.getAttribute('aria-label') || '';
      const text = btn.textContent?.trim().substring(0, 20) || '';
      const rect = btn.getBoundingClientRect();
      if (label.includes('作成') || text.includes('作成')) {
        btnList.push({
          label, text,
          disabled: btn.disabled,
          visible: rect.height > 0,
          tag: btn.tagName,
        });
      }
    }
    return { panel: true, createBtns: btnList };
  });
  console.log(`  textarea: "${taValue}" | 作成ボタン: ${JSON.stringify(btnDebug.createBtns || [])}`);

  let btnEnabled = await isCreateBtnEnabled(frame);

  // Method 2: keyboard.type — 1文字ずつ打鍵（確実だが遅い。短縮版）
  if (!btnEnabled) {
    console.log('  Method 2: keyboard.type...');
    await clearTextarea(page, textareaInfo.x, textareaInfo.y);
    await page.keyboard.type(prompt.substring(0, 200), { delay: 5 });
    await sleep(500);
    btnEnabled = await isCreateBtnEnabled(frame);
  }

  // Method 3: CDP Input.insertText
  if (!btnEnabled) {
    console.log('  Method 3: CDP insertText...');
    await clearTextarea(page, textareaInfo.x, textareaInfo.y);
    const client = await page.target().createCDPSession();
    await client.send('Input.insertText', { text: prompt });
    await client.detach();
    await sleep(500);
    btnEnabled = await isCreateBtnEnabled(frame);
  }

  // Method 4: React native setter + input/change events
  if (!btnEnabled) {
    console.log('  Method 4: React native setter...');
    await clearTextarea(page, textareaInfo.x, textareaInfo.y);
    await frame.evaluate((text) => {
      const textareas = document.querySelectorAll('textarea');
      for (const ta of textareas) {
        if (ta.offsetHeight > 0 && ta.offsetWidth > 0) {
          const nativeSetter = Object.getOwnPropertyDescriptor(
            window.HTMLTextAreaElement.prototype, 'value'
          ).set;
          nativeSetter.call(ta, text);
          ta.dispatchEvent(new Event('input', { bubbles: true }));
          ta.dispatchEvent(new Event('change', { bubbles: true }));
          return;
        }
      }
    }, prompt);
    await sleep(500);
    btnEnabled = await isCreateBtnEnabled(frame);
  }

  // Method 5: パネルリセット後に execCommand + keyboard.type
  if (!btnEnabled) {
    console.log('  Method 5: パネルリセット後に再試行...');
    await resetImagePanel(page, frame);
    await sleep(1500);
    textareaInfo = await findAndFocusTextarea(page, frame);
    if (textareaInfo.found) {
      // まず execCommand
      await clearTextarea(page, textareaInfo.x, textareaInfo.y);
      await frame.evaluate((text) => {
        const aside = document.querySelector('aside[aria-label="画像作成サポート"]');
        const textareas = (aside || document).querySelectorAll('textarea');
        for (const ta of textareas) {
          if (ta.offsetHeight > 0 && ta.offsetWidth > 0) {
            ta.focus();
            ta.select();
            document.execCommand('insertText', false, text);
            return;
          }
        }
      }, prompt);
      await sleep(800);
      btnEnabled = await isCreateBtnEnabled(frame);
      // ダメならkeyboard.type
      if (!btnEnabled) {
        await clearTextarea(page, textareaInfo.x, textareaInfo.y);
        await page.keyboard.type(prompt.substring(0, 200), { delay: 8 });
        await sleep(500);
        btnEnabled = await isCreateBtnEnabled(frame);
      }
    }
  }

  // 「作成」ボタンを座標ベースでクリック（aside内 → グローバル で検索）
  const createBtnBox = await frame.evaluate(() => {
    // 検索関数: 指定されたルート内で「作成」ボタンを見つける
    function findCreateBtn(root) {
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
    }
    // aside内で優先検索 → グローバルにフォールバック
    const aside = document.querySelector('aside[aria-label="画像作成サポート"]');
    if (aside) {
      const found = findCreateBtn(aside);
      if (found) return found;
    }
    return findCreateBtn(document);
  });

  if (createBtnBox) {
    await page.mouse.click(createBtnBox.x, createBtnBox.y);
  } else {
    throw new Error('「作成」ボタンが有効になりません');
  }

  return true;
}

/**
 * 生成完了を待つ
 */
/**
 * パネル内の結果menuitem数を取得
 */
async function getResultCount(frame) {
  return frame.evaluate(() => {
    const aside = document.querySelector('aside[aria-label="画像作成サポート"]');
    if (!aside) return 0;
    const menuItems = aside.querySelectorAll('[role="menuitem"]');
    let count = 0;
    for (const item of menuItems) {
      const text = item.textContent?.trim() || '';
      if (text.includes('プレビュー') || text.includes('生成')) count++;
    }
    return count;
  });
}

async function waitForGeneration(frame, timeoutMs, prevResultCount = 0) {
  const start = Date.now();
  process.stdout.write('  生成待ち');

  while (Date.now() - start < timeoutMs) {
    const status = await frame.evaluate((prevCount) => {
      // 1. プレビューダイアログチェック（display:none は前回のスタレダイアログなのでスキップ）
      const dialogs = document.querySelectorAll('[role="dialog"]');
      for (const dialog of dialogs) {
        const style = window.getComputedStyle(dialog);
        // display:none のダイアログは前回の古いダイアログ — 完全にスキップ
        if (style.display === 'none') continue;
        const btns = dialog.querySelectorAll('button, [role="button"]');
        let hasVisibleInsertBtn = false;
        let hasGenerating = false;
        for (const b of btns) {
          const t = b.textContent?.trim() || b.getAttribute('aria-label') || '';
          const rect = b.getBoundingClientRect();
          const visible = rect.height > 0 && rect.width > 0;
          // 「再作成しています」「作成しています」を最優先チェック
          if (t.includes('再作成しています') || t.includes('作成しています')) hasGenerating = true;
          // 「挿入」ボタンは visible で、かつ「新しいスライドとして」を含まないものだけ
          if (visible && t === '挿入') hasVisibleInsertBtn = true;
          // 「その他のオプション」ボタンが visible ならプレビュー準備完了
          if (visible && (t.includes('その他のオプション') || t.includes('新しいスライドとして挿入'))) hasVisibleInsertBtn = true;
        }
        // 生成中なら先に返す（挿入ボタンより優先）
        if (hasGenerating) return 'generating';
        // 挿入可能なボタンが表示されていれば準備完了
        if (hasVisibleInsertBtn) return 'ready';
        const text = dialog.textContent || '';
        if (text.includes('プレビュー') && !text.includes('作成しています')) return 'preview';
      }

      // 2. パネル内の結果サムネイル確認（aside内 → グローバル の順で検索）
      const aside = document.querySelector('aside[aria-label="画像作成サポート"]');
      const searchRoots = aside ? [aside, document] : [document];
      for (const root of searchRoots) {
        // 生成結果のmenuitemがあるか
        const menuItems = root.querySelectorAll('[role="menuitem"]');
        let hasPreview = false;
        let currentCount = 0;
        for (const item of menuItems) {
          const text = item.textContent?.trim() || '';
          if (text.includes('プレビュー')) hasPreview = true;
          if (text.includes('プレビュー') || text.includes('生成')) currentCount++;
        }
        if (hasPreview && currentCount > prevCount) return 'thumbnail-ready';

        // 「作成しています」ボタンがあるか
        const btns = root.querySelectorAll('button, [role="button"]');
        for (const btn of btns) {
          const label = btn.getAttribute('aria-label') || btn.textContent?.trim() || '';
          if (label.includes('作成しています')) return 'generating';
        }
        // root が aside で結果が見つからなかった場合、document でリトライ
      }

      return 'unknown';
    }, prevResultCount);

    if (status === 'ready' || status === 'preview' || status === 'thumbnail-ready') {
      const elapsed = ((Date.now() - start) / 1000).toFixed(1);
      console.log(` 完了 (${elapsed}秒)`);
      return status;
    }

    process.stdout.write('.');
    await sleep(3000);
  }

  throw new Error(`生成タイムアウト (${timeoutMs / 1000}秒)`);
}

/**
 * 生成された画像を現在のスライドに挿入
 *
 * 重要: サムネイルクリック後、プレビューダイアログは最初 display:none で
 * プレビューレンダリング中（「スライドを再作成しています」）。
 * レンダリング完了後に display が変わりボタンが操作可能になる。
 * getComputedStyle().display で可視性を判定する。
 */
async function insertImageToSlide(page, frame) {
  // 常に既存ダイアログを閉じてから、サムネイルクリックで新鮮なプレビューダイアログを開く
  await closeExistingDialog(page, frame);
  await sleep(500);

  // パネル内の最新サムネイルをスクロール→クリックしてプレビューダイアログを開く
  console.log('  サムネイルをクリックしてプレビューダイアログを開きます...');
  // 重要: サムネイルがパネル内でスクロール外に出ている場合があるため、
  // scrollIntoView で表示してからビューポート座標を取得→mouse.click()する
  const thumbBox = await frame.evaluate(() => {
    const aside = document.querySelector('aside[aria-label="画像作成サポート"]');
    if (!aside) return null;
    const menuItems = aside.querySelectorAll('[role="menuitem"]');
    // 最新（最後）のプレビュー可能なサムネイルを使う
    let lastThumb = null;
    for (const item of menuItems) {
      const text = item.textContent?.trim() || '';
      if (text.includes('プレビュー')) {
        lastThumb = item;
      }
    }
    if (!lastThumb) return null;

    // スクロールして表示
    lastThumb.scrollIntoView({ behavior: 'instant', block: 'center' });
    return true;
  });

  if (!thumbBox) {
    console.warn('  ⚠ サムネイルが見つかりません');
    return;
  }

  await sleep(500); // scrollIntoView 安定化

  // スクロール後にビューポート座標を取得してクリック
  const thumbCoords = await frame.evaluate(() => {
    const aside = document.querySelector('aside[aria-label="画像作成サポート"]');
    if (!aside) return null;
    const menuItems = aside.querySelectorAll('[role="menuitem"]');
    let lastThumb = null;
    for (const item of menuItems) {
      const text = item.textContent?.trim() || '';
      if (text.includes('プレビュー')) lastThumb = item;
    }
    if (!lastThumb) return null;
    const rect = lastThumb.getBoundingClientRect();
    return { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2, inViewport: rect.y >= 0 && rect.y < window.innerHeight };
  });

  if (!thumbCoords || !thumbCoords.inViewport) {
    console.warn('  ⚠ サムネイルがビューポート内に表示されません');
    return;
  }

  await page.mouse.click(thumbCoords.x, thumbCoords.y);
  await sleep(2000);

  // プレビューダイアログが表示されるまで待つ
  // 重要: ダイアログは最初 display:none でDOMに存在する。
  // プレビューレンダリングが完了すると display が変わる。
  // getComputedStyle(dialog).display !== 'none' で判定する。
  let dialogReady = false;
  process.stdout.write('  ダイアログ待ち');
  for (let attempt = 0; attempt < 60; attempt++) {  // 最大60秒待つ
    const check = await frame.evaluate(() => {
      const dialogs = document.querySelectorAll('[role="dialog"]');
      for (const dialog of dialogs) {
        const style = window.getComputedStyle(dialog);
        // display:none のダイアログはまだプレビュー中
        if (style.display === 'none') continue;
        const dialogRect = dialog.getBoundingClientRect();
        if (dialogRect.height === 0) continue;
        // ダイアログが visible になった — ボタンを確認
        const btns = dialog.querySelectorAll('button, [role="button"]');
        for (const btn of btns) {
          const rect = btn.getBoundingClientRect();
          const label = btn.getAttribute('aria-label') || btn.textContent?.trim() || '';
          if (rect.height > 0 && (label.includes('その他のオプション') || label.includes('新しいスライドとして挿入'))) {
            return 'ready';
          }
        }
        // ダイアログは visible だがボタンがまだ → もう少し待つ
        return 'visible-no-buttons';
      }
      // ダイアログがすべて display:none → プレビュー中
      const anyDialog = document.querySelector('[role="dialog"]');
      if (anyDialog) {
        const text = anyDialog.textContent || '';
        if (text.includes('再作成しています') || text.includes('作成しています')) return 'rendering';
      }
      return 'no-dialog';
    });

    if (check === 'ready') {
      dialogReady = true;
      console.log(' 表示完了');
      break;
    }
    if (check === 'visible-no-buttons') {
      // ダイアログは表示されたがボタンがまだロード中 — 短いウェイト
      process.stdout.write('+');
      await sleep(500);
      continue;
    }
    process.stdout.write('.');
    await sleep(1000);
  }

  if (!dialogReady) {
    console.log('');
    console.warn('  ⚠ プレビューダイアログが表示されません（60秒タイムアウト）');
    const debugDialogs = await frame.evaluate(() => {
      const dialogs = document.querySelectorAll('[role="dialog"]');
      return Array.from(dialogs).map(d => {
        const style = window.getComputedStyle(d);
        const rect = d.getBoundingClientRect();
        return {
          display: style.display,
          visible: rect.height > 0,
          size: `${Math.round(rect.width)}x${Math.round(rect.height)}`,
          text: d.textContent?.substring(0, 120)?.trim()
        };
      });
    });
    console.log(`  ダイアログ一覧: ${JSON.stringify(debugDialogs)}`);

    // display:none のままなら、もう一度サムネイルをスクロール→ダブルクリックで試す
    console.log('  再試行: サムネイルをスクロール→ダブルクリック...');
    // 再度スクロールして座標を取得
    const retryCoords = await frame.evaluate(() => {
      const aside = document.querySelector('aside[aria-label="画像作成サポート"]');
      if (!aside) return null;
      const menuItems = aside.querySelectorAll('[role="menuitem"]');
      let lastThumb = null;
      for (const item of menuItems) {
        const text = item.textContent?.trim() || '';
        if (text.includes('プレビュー')) lastThumb = item;
      }
      if (!lastThumb) return null;
      lastThumb.scrollIntoView({ behavior: 'instant', block: 'center' });
      return new Promise(resolve => setTimeout(() => {
        const rect = lastThumb.getBoundingClientRect();
        resolve({ x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 });
      }, 300));
    });
    if (retryCoords) {
      await page.mouse.click(retryCoords.x, retryCoords.y, { clickCount: 2 });
    }
    await sleep(3000);

    // 再チェック（15秒）
    for (let retry = 0; retry < 15; retry++) {
      const recheck = await frame.evaluate(() => {
        const dialogs = document.querySelectorAll('[role="dialog"]');
        for (const dialog of dialogs) {
          const style = window.getComputedStyle(dialog);
          if (style.display === 'none') continue;
          const rect = dialog.getBoundingClientRect();
          if (rect.height > 0) return true;
        }
        return false;
      });
      if (recheck) { dialogReady = true; console.log('  再試行: ダイアログ表示確認'); break; }
      await sleep(1000);
    }

    if (!dialogReady) {
      console.warn('  ⚠ プレビューダイアログの表示に失敗 — スキップ');
      return;
    }
  }

  await sleep(500); // ダイアログ表示後の安定化待ち

  // メインアクションボタンをクリック
  // コンテキストにより表示が変わる:
  //   「置き換える」— 現在のスライドを直接置き換え（既にコンテンツがある場合）
  //   「新しいスライドとして挿入します」— 新しいスライドとして追加
  const mainBtnBox = await frame.evaluate(() => {
    const dialogs = document.querySelectorAll('[role="dialog"]');
    for (const dialog of dialogs) {
      const style = window.getComputedStyle(dialog);
      if (style.display === 'none') continue;
      const btns = dialog.querySelectorAll('button, [role="button"]');
      for (const btn of btns) {
        const text = btn.textContent?.trim() || '';
        const label = btn.getAttribute('aria-label') || '';
        // 「置き換える」「新しいスライドとして挿入します」のどちらか
        if (text.includes('置き換える') || text.includes('新しいスライドとして挿入') ||
            label.includes('置き換える') || label.includes('新しいスライドとして挿入')) {
          const rect = btn.getBoundingClientRect();
          if (rect.height > 0) return { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2, text };
        }
      }
    }
    return null;
  });

  if (mainBtnBox) {
    await page.mouse.click(mainBtnBox.x, mainBtnBox.y);
    const action = mainBtnBox.text.includes('置き換える') ? 'replaced' : 'inserted-as-new-slide';
    console.log(`  「${mainBtnBox.text}」をクリック`);
    await sleep(3000);
    return action;
  }

  console.warn('  ⚠ アクションボタンが見つかりません');
  return null;
}

/**
 * 画像を背景に設定
 */
async function setAsBackground(page, frame) {
  // スライドエディタ領域の座標を取得
  const slideArea = await frame.evaluate(() => {
    const container = document.querySelector('.punch-viewer-svgpage-svgcontainer')
      || document.querySelector('.punch-viewer-content');
    if (container) {
      const rect = container.getBoundingClientRect();
      return { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2, w: rect.width, h: rect.height };
    }
    return { x: window.innerWidth * 0.45, y: window.innerHeight * 0.5, w: 800, h: 600 };
  });

  // 挿入直後: まずダイアログが残っていれば閉じる
  await closeExistingDialog(page, frame);
  await sleep(500);

  // スライドエリアをクリックしてフォーカスを確保
  await page.mouse.click(slideArea.x, slideArea.y);
  await sleep(500);

  // === 方法1: 右クリック→「画像を背景に設定」 ===
  let bgSet = false;

  // 画像を選択: Tabキーでオブジェクトを選択
  await page.keyboard.press('Tab');
  await sleep(500);

  // 右クリック
  await page.mouse.click(slideArea.x, slideArea.y, { button: 'right' });
  await sleep(1500);

  // コンテキストメニュー（メニューバーを除外）から「画像を背景に設定」を探す
  const bgBox = await frame.evaluate(() => {
    // ポップアップメニュー（.goog-menu や position:absolute のメニュー）を探す
    const popupMenus = document.querySelectorAll('.goog-menu, [role="menu"]:not([role="menubar"] [role="menu"])');
    for (const menu of popupMenus) {
      const rect = menu.getBoundingClientRect();
      if (rect.height === 0) continue;
      // このメニューがメニューバーの子でないことを確認
      if (menu.closest('[role="menubar"]')) continue;
      const items = menu.querySelectorAll('[role="menuitem"], .goog-menuitem');
      for (const item of items) {
        const text = item.textContent?.trim() || '';
        if (text.includes('背景に設定') || text.includes('背景として設定')) {
          const r = item.getBoundingClientRect();
          if (r.height > 0) return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
        }
      }
    }
    // フォールバック: 全menuitemから探す（メニューバー除外）
    const allItems = document.querySelectorAll('[role="menuitem"], .goog-menuitem');
    for (const item of allItems) {
      if (item.closest('[role="menubar"]')) continue;
      const text = item.textContent?.trim() || '';
      if (text.includes('背景に設定') || text.includes('背景として設定')) {
        const r = item.getBoundingClientRect();
        if (r.height > 0) return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
      }
    }
    return null;
  });

  if (bgBox) {
    await page.mouse.click(bgBox.x, bgBox.y);
    console.log('  「画像を背景に設定」をクリック');
    bgSet = true;
    await sleep(1000);
    // 前面の画像を削除
    await page.mouse.click(slideArea.x, slideArea.y);
    await sleep(300);
    await page.keyboard.press('Tab');
    await sleep(300);
    await page.keyboard.press('Delete');
    await sleep(500);
    return true;
  }

  await page.keyboard.press('Escape');
  await sleep(300);

  // === 方法2: 「配置」→「順序」→「最背面へ」メニューで背面に送る ===
  console.log('  方法2: メニュー「配置」→「順序」→「最背面へ」...');

  // 画像オブジェクトを選択
  await page.mouse.click(slideArea.x, slideArea.y);
  await sleep(300);
  await page.keyboard.press('Tab');
  await sleep(500);

  // メニューバーの「配置」をクリック
  const arrangeMenuBox = await frame.evaluate(() => {
    const menuItems = document.querySelectorAll('[role="menubar"] [role="menuitem"]');
    for (const item of menuItems) {
      const text = item.textContent?.trim() || '';
      if (text === '配置' || text === 'Arrange') {
        const rect = item.getBoundingClientRect();
        if (rect.height > 0) return { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 };
      }
    }
    return null;
  });

  if (arrangeMenuBox) {
    await page.mouse.click(arrangeMenuBox.x, arrangeMenuBox.y);
    await sleep(1000);

    // 「順序」サブメニューを探す
    const orderBox = await frame.evaluate(() => {
      const items = document.querySelectorAll('[role="menuitem"], .goog-menuitem');
      for (const item of items) {
        if (item.closest('[role="menubar"]')) continue;
        const text = item.textContent?.trim() || '';
        if (text.includes('順序') || text === 'Order') {
          const rect = item.getBoundingClientRect();
          if (rect.height > 0) return { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 };
        }
      }
      return null;
    });

    if (orderBox) {
      await page.mouse.click(orderBox.x, orderBox.y);
      await sleep(1000);

      // 「最背面へ」を探す
      const sendToBackBox = await frame.evaluate(() => {
        const items = document.querySelectorAll('[role="menuitem"], .goog-menuitem');
        for (const item of items) {
          if (item.closest('[role="menubar"]')) continue;
          const text = item.textContent?.trim() || '';
          if (text.includes('最背面') || text.includes('Send to back')) {
            const rect = item.getBoundingClientRect();
            if (rect.height > 0) return { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 };
          }
        }
        return null;
      });

      if (sendToBackBox) {
        await page.mouse.click(sendToBackBox.x, sendToBackBox.y);
        console.log('  「最背面へ」で画像を背面に送りました');
        bgSet = true;
        await sleep(500);
      }
    }

    if (!bgSet) {
      await page.keyboard.press('Escape');
      await sleep(200);
      await page.keyboard.press('Escape');
      await sleep(200);
    }
  }

  if (!bgSet) {
    // 方法3: 画像は挿入済みだがレイヤー操作できず。部分成功として続行
    console.warn('  ⚠ 背景設定/最背面移動できず（画像は挿入済み）');
    await page.keyboard.press('Escape');
    return false;
  }

  return true;
}

/**
 * 既存のプレビューダイアログを閉じる
 */
async function closeExistingDialog(page, frame) {
  // display:none でない可視ダイアログの「閉じる」ボタンを探す
  const closeBox = await frame.evaluate(() => {
    const dialogs = document.querySelectorAll('[role="dialog"]');
    for (const dialog of dialogs) {
      const style = window.getComputedStyle(dialog);
      if (style.display === 'none') continue;
      const rect = dialog.getBoundingClientRect();
      if (rect.height === 0) continue;
      const allClickable = dialog.querySelectorAll('button, [role="button"]');
      for (const el of allClickable) {
        const label = el.getAttribute('aria-label') || el.textContent?.trim() || '';
        if (label === '閉じる' || label === 'Close' || label === '✕' || label === '×') {
          const r = el.getBoundingClientRect();
          if (r.height > 0) return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
        }
      }
    }
    return null;
  });
  if (closeBox) {
    await page.mouse.click(closeBox.x, closeBox.y);
    await sleep(500);
  }
}

/**
 * スライドの品質を検証（スクリーンショット＋ピクセル分析）
 * ① 画像がスライドに貼られているか（空白でないか）
 * ② 複数の画像が重なっていないか
 * ③ デザインが適用されているか
 */
async function verifySlideQuality(page, frame, slideNum) {
  // スライド領域の座標を取得（複数セレクタ対応）
  const slideRect = await frame.evaluate(() => {
    const selectors = [
      '.punch-viewer-svgpage-svgcontainer',
      '.punch-viewer-content',
      '.punch-viewer-svgpage',
      '.punch-viewer-container',
      '[class*="slide-container"]',
      '[class*="viewer"]'
    ];
    for (const sel of selectors) {
      const el = document.querySelector(sel);
      if (el) {
        const rect = el.getBoundingClientRect();
        if (rect.width > 100 && rect.height > 100) {
          return {
            x: Math.max(0, Math.round(rect.x)),
            y: Math.max(0, Math.round(rect.y)),
            width: Math.round(rect.width),
            height: Math.round(rect.height)
          };
        }
      }
    }
    // フォールバック: ビューポートの中央領域
    return {
      x: Math.round(window.innerWidth * 0.15),
      y: Math.round(window.innerHeight * 0.08),
      width: Math.round(window.innerWidth * 0.55),
      height: Math.round(window.innerHeight * 0.85)
    };
  });

  if (!slideRect || slideRect.width === 0 || slideRect.height === 0) {
    return { passed: false, reason: 'スライド領域が見つかりません' };
  }

  // スクリーンショットディレクトリ
  const screenshotDir = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..', 'screenshots');
  if (!fs.existsSync(screenshotDir)) fs.mkdirSync(screenshotDir, { recursive: true });

  // スクリーンショット撮影・保存
  const screenshotPath = path.join(screenshotDir, `slide_${slideNum}.png`);
  const screenshotBuffer = await page.screenshot({ clip: slideRect });
  fs.writeFileSync(screenshotPath, screenshotBuffer);
  const fileSize = screenshotBuffer.length;
  console.log(`  スクリーンショット: slide_${slideNum}.png (${(fileSize / 1024).toFixed(1)}KB)`);

  // チェック1: ファイルサイズ（空白スライドはPNG圧縮で小さくなる）
  if (fileSize < 20000) {
    return { passed: false, reason: `空白の可能性 (${(fileSize / 1024).toFixed(1)}KB < 20KB)` };
  }

  // チェック2: CDPでピクセルサンプリング（色の多様性チェック）
  try {
    const cdpSession = await page.target().createCDPSession();
    const { data: b64 } = await cdpSession.send('Page.captureScreenshot', {
      clip: { ...slideRect, scale: 0.25 },
      format: 'png'
    });
    await cdpSession.detach();

    const pixelAnalysis = await page.evaluate(async (base64Data) => {
      return new Promise((resolve) => {
        const img = new Image();
        img.onload = () => {
          const canvas = document.createElement('canvas');
          canvas.width = img.width;
          canvas.height = img.height;
          const ctx = canvas.getContext('2d');
          ctx.drawImage(img, 0, 0);

          let colorfulPixels = 0;
          const totalSamples = 300;
          for (let s = 0; s < totalSamples; s++) {
            const x = Math.floor(Math.random() * canvas.width);
            const y = Math.floor(Math.random() * canvas.height);
            const pixel = ctx.getImageData(x, y, 1, 1).data;
            if (pixel[0] < 230 || pixel[1] < 230 || pixel[2] < 230) {
              colorfulPixels++;
            }
          }

          resolve({ colorfulRatio: colorfulPixels / totalSamples });
        };
        img.src = 'data:image/png;base64,' + base64Data;
      });
    }, b64);

    console.log(`  ピクセル分析: 色付き ${(pixelAnalysis.colorfulRatio * 100).toFixed(1)}%`);

    if (pixelAnalysis.colorfulRatio < 0.10) {
      return { passed: false, reason: `デザイン未適用 (色付き${(pixelAnalysis.colorfulRatio * 100).toFixed(1)}% < 10%)` };
    }
  } catch (pixelErr) {
    console.warn(`  ピクセル分析スキップ: ${pixelErr.message}`);
  }

  return { passed: true, fileSize };
}

/**
 * Slides APIを使って、新スライドの画像を元スライドの背景に設定し、新スライドを削除
 * node scripts/slide_image_generator.mjs が呼び出す
 */
async function transferNewSlideToBackground(presId, targetSlideIndex) {
  // Python スクリプトを同期的に実行
  const { execSync } = await import('child_process');
  const cmd = `python3 scripts/transfer_new_slide.py ${presId} ${targetSlideIndex}`;
  try {
    const output = execSync(cmd, { cwd: process.cwd(), timeout: 30000, encoding: 'utf-8' });
    console.log(`  API: ${output.trim()}`);
    return true;
  } catch (e) {
    console.warn(`  ⚠ API転送失敗: ${e.message}`);
    return false;
  }
}

// --- メイン ---
async function main() {
  console.log('=== Google Slides 画像作成サポート 自動化 ===');
  if (specificSlides.length > 0) {
    console.log(`指定スライド: ${specificSlides.join(', ')}`);
  } else {
    console.log(`スライド範囲: ${fromSlide}〜${toSlide === -1 ? '最終' : toSlide}`);
  }
  if (cooldownMs > 0) console.log(`レート制限対策クールダウン: ${cooldownMs / 1000}秒`);
  if (dryRun) console.log('⚡ DRY RUN モード');

  // プロンプト読み込み
  let prompts = {};
  if (promptsFile && fs.existsSync(promptsFile)) {
    prompts = JSON.parse(fs.readFileSync(promptsFile, 'utf-8'));
    console.log(`プロンプト: ${Object.keys(prompts).length}件読み込み`);
  }

  // CDP接続
  console.log('\nブラウザ接続中...');
  const browser = await puppeteer.connect({
    browserURL: `http://127.0.0.1:${cdpPort}`,
    defaultViewport: null,
    protocolTimeout: 120000,
  });

  const pages = await browser.pages();
  let page = pages.find(p => p.url().includes('docs.google.com/presentation'));
  if (!page) {
    page = pages[0] || await browser.newPage();
    await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });
    await sleep(3000);
  }

  const frame = getSlideFrame(page);
  const totalSlides = await getSlideCount(frame);
  console.log(`スライド数: ${totalSlides}`);

  if (toSlide === -1) toSlide = totalSlides;

  // --slides オプションが指定されていればそれを使う
  const slideList = specificSlides.length > 0
    ? specificSlides.filter(n => n >= 1 && n <= totalSlides)
    : Array.from({ length: toSlide - fromSlide + 1 }, (_, k) => fromSlide + k);
  console.log(`処理: ${slideList.join(', ')} (${slideList.length}枚)\n`);

  // パネル準備
  await ensureImagePanel(page, frame);
  // await ensureSlideTab(page, frame); // Skip - works with Image tab too
  await closeExistingDialog(page, frame);

  const results = [];
  const startTime = Date.now();

  for (let si = 0; si < slideList.length; si++) {
    const i = slideList[si];
    const maxRetries = 3;
    let slideSuccess = false;

    for (let attempt = 1; attempt <= maxRetries && !slideSuccess; attempt++) {
    const slideStart = Date.now();
    console.log(`[${si + 1}/${slideList.length}] スライド${i}${attempt > 1 ? ` (リトライ${attempt}/${maxRetries})` : ''}`);

    try {
      // 1. スライド移動
      await navigateToSlide(page, frame, i);
      console.log('  移動完了');

      // 2. パネル確認
      await ensureImagePanel(page, frame);
      // await ensureSlideTab(page, frame); // Skip - works with Image tab too

      // 3. プロンプト
      let prompt = prompts[String(i)];
      if (!prompt) {
        // デフォルトプロンプト（スライド内容に基づく）
        prompt = `このスライドをプロフェッショナルなAI講座のスライドにリデザインしてください。モダンで洗練されたデザイン、テクノロジー感のある配色。テキストは白で読みやすく。`;
      }
      console.log(`  プロンプト: ${prompt.substring(0, 50)}...`);

      if (dryRun) {
        results.push({ slide: i, prompt, status: 'dry-run' });
        slideSuccess = true;
        break;
      }

      // 3. 既存ダイアログを閉じて結果数を記録
      await closeExistingDialog(page, frame);
      const prevCount = await getResultCount(frame);
      
      // 4. プロンプト送信
      await submitPrompt(page, frame, prompt);
      console.log('  送信完了');

      // 5. 生成待ち
      await waitForGeneration(frame, genTimeout, prevCount);

      // 5. 挿入（「置き換える」ボタンで現スライドを直接置き換え）
      const insertResult = await insertImageToSlide(page, frame);
      console.log(`  挿入結果: ${insertResult}`);

      // 「inserted-as-new-slide」の場合はAPIで転送
      if (insertResult === 'inserted-as-new-slide') {
        const presMatch = url.match(/\/d\/([a-zA-Z0-9_-]+)/);
        if (presMatch) {
          await transferNewSlideToBackground(presMatch[1], i - 1);
          await sleep(2000);
          // API操作後、別スライドに移動してから戻ることでDOM状態を同期
          await page.keyboard.press('Home');
          await sleep(1000);
          currentSlideNum = 1;
          await navigateToSlide(page, frame, i);
          await sleep(1000);
        }
      }

      // 6. 品質検証
      await sleep(3000); // スライド更新完了を待つ
      await closeExistingDialog(page, frame);
      await sleep(1000);

      // スライドにフォーカスを戻す
      await page.mouse.click(700, 400);
      await sleep(500);

      const quality = await verifySlideQuality(page, frame, i);

      if (!quality.passed) {
        console.log(`  ✗ 品質チェック失敗: ${quality.reason}`);
        if (attempt < maxRetries) {
          console.log(`  次のリトライまで待機中...`);
          await sleep(5000);
          continue;
        }
        results.push({ slide: i, status: 'failed', reason: quality.reason, attempt });
      } else {
        slideSuccess = true;
        const elapsed = ((Date.now() - slideStart) / 1000).toFixed(1);
        console.log(`  ✓ 品質チェック合格 (${elapsed}秒)\n`);
        results.push({ slide: i, status: 'success', time: elapsed, attempt });
      }

    } catch (err) {
      console.error(`  ✗ エラー: ${err.message}`);
      if (attempt >= maxRetries) {
        results.push({ slide: i, status: 'error', error: err.message, attempt });
      }
      await closeExistingDialog(page, frame);
      try {
        await resetImagePanel(page, frame);
      } catch (resetErr) {
        console.warn(`  パネルリセット失敗: ${resetErr.message}`);
      }
      if (attempt < maxRetries) await sleep(5000);
    }
    } // end retry loop

    // クールダウン（レート制限対策: cooldownMs が指定されていれば追加待機）
    if (si < slideList.length - 1) {
      const totalCooldown = Math.max(delayMs, 5000) + cooldownMs;
      if (cooldownMs > 0) {
        console.log(`  レート制限対策クールダウン: ${totalCooldown / 1000}秒待機...`);
      } else {
        console.log('  クールダウン中...');
      }
      await sleep(totalCooldown);
    }
  }

  // サマリー
  const totalTime = ((Date.now() - startTime) / 1000).toFixed(0);
  const success = results.filter(r => r.status === 'success').length;
  const failed = results.filter(r => r.status === 'failed').length;
  const errors = results.filter(r => r.status === 'error').length;

  console.log('=== 結果 ===');
  console.log(`成功: ${success} / 失敗: ${failed} / エラー: ${errors} / 合計: ${results.length}`);
  console.log(`所要時間: ${totalTime}秒`);

  if (errors > 0) {
    console.log('\nエラー詳細:');
    results.filter(r => r.status === 'error').forEach(r => console.log(`  スライド${r.slide}: ${r.error}`));
  }

  // 結果保存
  const outPath = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..', 'slide_generation_results.json');
  fs.writeFileSync(outPath, JSON.stringify({ timestamp: new Date().toISOString(), results }, null, 2));
  console.log(`\n結果保存: ${outPath}`);

  browser.disconnect();
}

main().catch(err => {
  console.error('Fatal:', err);
  process.exit(1);
});
