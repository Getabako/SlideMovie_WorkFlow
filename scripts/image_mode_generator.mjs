#!/usr/bin/env node
/**
 * 「画像」モードで背景画像を生成するスクリプト
 * 「スライド」モードがレート制限された時のフォールバック
 *
 * 使い方:
 *   node scripts/image_mode_generator.mjs <URL> --slides 7,19,20,21,22,23,24 --prompts prompts.json
 */

import puppeteer from 'puppeteer-core';
import fs from 'fs';
import path from 'path';

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
  console.error('Usage: node scripts/image_mode_generator.mjs <URL> --slides N,N,N --prompts prompts.json');
  process.exit(1);
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

let prompts = {};
if (promptsFile && fs.existsSync(promptsFile)) {
  prompts = JSON.parse(fs.readFileSync(promptsFile, 'utf-8'));
}

let currentSlideNum = 1;

async function navigateToSlide(page, n) {
  await page.mouse.click(700, 400);
  await sleep(200);

  if (n === 1) {
    await page.keyboard.press('Home');
    await sleep(500);
    currentSlideNum = 1;
    return;
  }

  // Always go from Home to ensure accuracy
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
  // Try closing via X button first
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

async function ensureImageModePanel(page, frame) {
  // First close any existing panel to start fresh
  await closePanel(page);
  await sleep(500);

  let currentFrame = page.mainFrame();
  let panelOpened = false;

  // Retry up to 10 times with increasing waits
  for (let retry = 0; retry < 10; retry++) {
    currentFrame = page.mainFrame();
    const hasTextarea = await currentFrame.evaluate(() => {
      const textareas = document.querySelectorAll('textarea');
      return Array.from(textareas).some(t => t.offsetHeight > 0);
    });

    if (hasTextarea) { panelOpened = true; break; }

    if (retry > 0) console.log(`  パネルを開いています... (${retry + 1}/10)`);

    // Click slide area first to ensure focus
    await page.mouse.click(400, 300);
    await sleep(500);

    // Try clicking panel button on the right toolbar
    const panelBtn = await currentFrame.evaluate(() => {
      const btns = document.querySelectorAll('[role="button"], button');
      for (const btn of btns) {
        const label = btn.getAttribute('aria-label') || '';
        if (label === '画像作成サポート' || label === 'スライド画像を作成する') {
          const rect = btn.getBoundingClientRect();
          if (rect.height > 0) return { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2, label };
        }
      }
      return null;
    });

    if (panelBtn) {
      await page.mouse.click(panelBtn.x, panelBtn.y);
    }
    const waitTime = retry < 3 ? 5000 : 8000;
    await sleep(waitTime);
  }

  if (!panelOpened) {
    throw new Error('パネルを開けませんでした（テキストエリアが見つかりません）');
  }

  // Ensure 画像 tab is selected
  currentFrame = page.mainFrame();
  const imageTabBox = await currentFrame.evaluate(() => {
    const tabs = document.querySelectorAll('[role="tab"]');
    for (const tab of tabs) {
      const text = (tab.textContent || '').trim();
      const rect = tab.getBoundingClientRect();
      if (text === '画像' && rect.height > 0 && tab.getAttribute('aria-selected') !== 'true') {
        return { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 };
      }
    }
    return null;
  });
  if (imageTabBox) {
    await page.mouse.click(imageTabBox.x, imageTabBox.y);
    await sleep(1000);
  }
}

async function typePrompt(page, frame, prompt) {
  const currentFrame = page.mainFrame();
  const taInfo = await currentFrame.evaluate(() => {
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

  // Clear and type
  await page.mouse.click(taInfo.x, taInfo.y);
  await sleep(200);
  await page.keyboard.down('Meta');
  await page.keyboard.press('a');
  await page.keyboard.up('Meta');
  await page.keyboard.press('Backspace');
  await sleep(300);

  // Try execCommand first
  await currentFrame.evaluate((text) => {
    const textareas = document.querySelectorAll('textarea');
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

  // Check if button is enabled
  let enabled = await findCreateButton(currentFrame);
  if (!enabled) {
    // Fallback: keyboard.type
    await page.mouse.click(taInfo.x, taInfo.y);
    await sleep(200);
    await page.keyboard.down('Meta');
    await page.keyboard.press('a');
    await page.keyboard.up('Meta');
    await page.keyboard.press('Backspace');
    await sleep(300);
    await page.keyboard.type(prompt.substring(0, 200), { delay: 8 });
    await sleep(800);
  }
}

async function findCreateButton(frame) {
  // Find the VISIBLE, ENABLED creation button (not the hidden disabled one)
  return frame.evaluate(() => {
    const btns = document.querySelectorAll('.image-synthesis-creation-button');
    for (const btn of btns) {
      const rect = btn.getBoundingClientRect();
      if (rect.height > 0 && !btn.disabled) {
        return { x: Math.round(rect.x + rect.width / 2), y: Math.round(rect.y + rect.height / 2) };
      }
    }
    // Fallback: elementFromPoint scan
    for (let x = 650; x < 710; x += 5) {
      for (let y = 470; y < 520; y += 5) {
        const el = document.elementFromPoint(x, y);
        if (el && el.tagName === 'BUTTON' && !el.disabled &&
            (el.getAttribute('aria-label') === '作成' || el.className?.toString()?.includes('image-synthesis-creation'))) {
          return { x, y };
        }
      }
    }
    return null;
  });
}

async function clickCreateAndWait(page, frame, timeoutMs) {
  const f = page.mainFrame();
  const btnPos = await findCreateButton(f);
  if (!btnPos) throw new Error('作成ボタンが見つかりません');

  await page.mouse.click(btnPos.x, btnPos.y);
  process.stdout.write('  生成待ち');

  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    await sleep(3000);
    const status = await f.evaluate(() => {
      const btns = document.querySelectorAll('button, [role="button"]');
      for (const btn of btns) {
        const text = btn.getAttribute('aria-label') || btn.textContent?.trim() || '';
        if (text.includes('作成しています')) return 'generating';
      }
      const menuItems = document.querySelectorAll('[role="menuitem"]');
      for (const item of menuItems) {
        if ((item.textContent || '').includes('プレビュー')) return 'ready';
      }
      return 'waiting';
    });

    if (status === 'ready') {
      console.log(' 完了');
      return true;
    }
    process.stdout.write(status === 'generating' ? '>' : '.');
  }
  throw new Error(`生成タイムアウト (${timeoutMs / 1000}秒)`);
}

async function insertGeneratedImage(page, frame) {
  const f = page.mainFrame();
  // Find the latest thumbnail/menuitem and click it
  const thumbCoords = await f.evaluate(() => {
    const menuItems = document.querySelectorAll('[role="menuitem"]');
    let lastThumb = null;
    for (const item of menuItems) {
      if ((item.textContent || '').includes('プレビュー')) {
        lastThumb = item;
      }
    }
    if (!lastThumb) return null;
    lastThumb.scrollIntoView({ behavior: 'instant', block: 'center' });
    return true;
  });

  if (!thumbCoords) throw new Error('サムネイルが見つかりません');
  await sleep(500);

  // Get coordinates after scroll
  const coords = await f.evaluate(() => {
    const menuItems = document.querySelectorAll('[role="menuitem"]');
    let lastThumb = null;
    for (const item of menuItems) {
      if ((item.textContent || '').includes('プレビュー')) lastThumb = item;
    }
    if (!lastThumb) return null;
    const rect = lastThumb.getBoundingClientRect();
    return { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 };
  });

  if (!coords) throw new Error('サムネイル座標が取得できません');

  await page.mouse.click(coords.x, coords.y);
  await sleep(2000);

  // Wait for dialog to appear
  process.stdout.write('  ダイアログ待ち');
  let dialogReady = false;
  for (let i = 0; i < 30; i++) {
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
          if (r.height > 0 && (text.includes('挿入') || text.includes('その他のオプション'))) {
            return 'ready';
          }
        }
        return 'visible-no-buttons';
      }
      return 'waiting';
    });

    if (check === 'ready') {
      dialogReady = true;
      console.log(' OK');
      break;
    }
    process.stdout.write('.');
    await sleep(1000);
  }

  if (!dialogReady) throw new Error('ダイアログが表示されません');

  // Click "挿入" button in the dialog
  const insertBtnBox = await f.evaluate(() => {
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
        const r = btn.getBoundingClientRect();
        if (r.height > 0 && (text === '挿入' || label === '挿入')) {
          return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
        }
      }
    }
    return null;
  });

  if (insertBtnBox) {
    await page.mouse.click(insertBtnBox.x, insertBtnBox.y);
    console.log('  「挿入」をクリック');
    await sleep(3000);
    return true;
  }

  throw new Error('挿入ボタンが見つかりません');
}

async function setImageAsBackground(page, frame, slideIndex) {
  // Slides API経由で画像を背景に設定
  // 注: presentations().get()は背景を返さないが、実際には設定される
  const presMatch = url.match(/\/d\/([a-zA-Z0-9_-]+)/);
  if (!presMatch) {
    console.warn('  ⚠ プレゼンテーションIDが取得できません');
    return false;
  }

  const { execSync } = await import('child_process');
  const cmd = `python3 scripts/set_image_as_background.py ${presMatch[1]} ${slideIndex}`;
  try {
    const output = execSync(cmd, { cwd: process.cwd(), timeout: 30000, encoding: 'utf-8' });
    console.log(`  API: ${output.trim()}`);
    return true;
  } catch (e) {
    console.warn(`  ⚠ API背景設定失敗: ${e.message}`);
    return false;
  }
}

async function verifySlideQuality(page, frame, slideNum) {
  const f = page.mainFrame();
  const slideRect = await f.evaluate(() => {
    const selectors = ['.punch-viewer-svgpage-svgcontainer', '.punch-viewer-content', '.punch-viewer-svgpage'];
    for (const sel of selectors) {
      const el = document.querySelector(sel);
      if (el) {
        const rect = el.getBoundingClientRect();
        if (rect.width > 100 && rect.height > 100) {
          return { x: Math.max(0, Math.round(rect.x)), y: Math.max(0, Math.round(rect.y)), width: Math.round(rect.width), height: Math.round(rect.height) };
        }
      }
    }
    return { x: Math.round(window.innerWidth * 0.15), y: Math.round(window.innerHeight * 0.08), width: Math.round(window.innerWidth * 0.55), height: Math.round(window.innerHeight * 0.85) };
  });

  const screenshotDir = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..', 'screenshots');
  if (!fs.existsSync(screenshotDir)) fs.mkdirSync(screenshotDir, { recursive: true });

  const screenshotPath = path.join(screenshotDir, `slide_${slideNum}.png`);
  const buf = await page.screenshot({ clip: slideRect });
  fs.writeFileSync(screenshotPath, buf);
  const fileSize = buf.length;
  console.log(`  スクリーンショット: slide_${slideNum}.png (${(fileSize / 1024).toFixed(1)}KB)`);

  if (fileSize < 20000) {
    return { passed: false, reason: `空白の可能性 (${(fileSize / 1024).toFixed(1)}KB)` };
  }

  try {
    const cdpSession = await page.target().createCDPSession();
    const { data: b64 } = await cdpSession.send('Page.captureScreenshot', {
      clip: { ...slideRect, scale: 0.25 }, format: 'png'
    });
    await cdpSession.detach();

    const pixelAnalysis = await page.evaluate(async (base64Data) => {
      return new Promise(resolve => {
        const img = new Image();
        img.onload = () => {
          const canvas = document.createElement('canvas');
          canvas.width = img.width; canvas.height = img.height;
          const ctx = canvas.getContext('2d');
          ctx.drawImage(img, 0, 0);
          let colorfulPixels = 0;
          const totalSamples = 300;
          for (let s = 0; s < totalSamples; s++) {
            const x = Math.floor(Math.random() * canvas.width);
            const y = Math.floor(Math.random() * canvas.height);
            const pixel = ctx.getImageData(x, y, 1, 1).data;
            if (pixel[0] < 230 || pixel[1] < 230 || pixel[2] < 230) colorfulPixels++;
          }
          resolve({ colorfulRatio: colorfulPixels / totalSamples });
        };
        img.src = 'data:image/png;base64,' + base64Data;
      });
    }, b64);

    console.log(`  ピクセル分析: 色付き ${(pixelAnalysis.colorfulRatio * 100).toFixed(1)}%`);
    if (pixelAnalysis.colorfulRatio < 0.10) {
      return { passed: false, reason: `色付き ${(pixelAnalysis.colorfulRatio * 100).toFixed(1)}% < 10%` };
    }
  } catch (e) {
    console.warn(`  ピクセル分析スキップ: ${e.message}`);
  }

  return { passed: true, fileSize };
}

// --- Main ---
async function main() {
  console.log('=== 画像モード バックグラウンド生成 ===');
  console.log(`対象スライド: ${specificSlides.join(', ')}`);
  console.log(`プロンプト: ${Object.keys(prompts).length}件`);

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

  // ウィンドウが最小化されている場合は復元
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

  const frame = page.mainFrame();
  const results = [];
  const startTime = Date.now();

  for (let si = 0; si < specificSlides.length; si++) {
    const slideNum = specificSlides[si];
    const maxRetries = 3;
    let success = false;

    for (let attempt = 1; attempt <= maxRetries && !success; attempt++) {
      console.log(`\n[${si + 1}/${specificSlides.length}] スライド${slideNum}${attempt > 1 ? ` (リトライ${attempt})` : ''}`);

      try {
        // 1. Navigate
        await navigateToSlide(page, slideNum);
        console.log('  移動完了');

        // 2. Ensure panel in 画像 mode
        await ensureImageModePanel(page, frame);

        // 3. Use English prompts for image mode (Japanese may not be supported)
        const englishPrompts = {
          '6': 'Warm brown to orange gradient background. House silhouette with door being knocked. Home visit nursing concept. Supportive and safe atmosphere. Professional presentation background. 16:9.',
          '7': 'Teal blue background with house silhouette and family support arrows diagram. Warm green accents. Professional presentation slide background.',
          '16': 'Dark blue to purple gradient background. Vinyl record spinning, speech bubbles repeating same message. Calm repetition concept (broken record technique). Professional presentation background. 16:9.',
          '17': 'Dark teal gradient background. ABC analysis flowchart arrows (Antecedent, Behavior, Consequence). Data observation sheet and pen icons. Clean analytical design. Professional presentation background. 16:9.',
          '18': 'Dark blue to gold gradient background. 5 ascending stairs/steps going from bottom-left to top-right. Numbers on each step. Growth and small progress theme. Professional presentation background. 16:9.',
          '19': 'Teal blue background with vinyl record spinning repeatedly. Parent-child conversation speech bubbles. Calm peaceful atmosphere. Presentation background.',
          '20': 'Green gradient background with 5 ascending steps/stairs going upward. Checkmark on each step. Achievement and progress theme. Presentation background.',
          '21': 'Pink to purple warm gradient background. Hands gently holding a glowing heart. Self-care and nurturing theme for parents. Soft warm lighting. Professional presentation background. 16:9.',
          '22': 'Dark navy to gold gradient background. Checklist with 3 checkmarks. Summary and review concept. Achievement feeling. Notebook and pen icons. Professional presentation background. 16:9.',
          '23': 'Teal to blue gradient background. Hands reaching out to each other in support. Community help and professional support theme. Warm welcoming design. Professional presentation background. 16:9.',
          '24': 'Green and blue gradient with warm light. Hands reaching out in support. Hope and community support theme. Welcoming and warm design. Presentation background.',
        };
        let promptText = englishPrompts[String(slideNum)] || `Professional presentation slide background design for slide ${slideNum}. Modern gradient with relevant icons.`;
        console.log(`  プロンプト: ${promptText.substring(0, 60)}...`);

        // 4. Type prompt
        await typePrompt(page, frame, promptText);

        // 5. Click create and wait
        await clickCreateAndWait(page, frame, genTimeout);

        // 6. Insert the generated image
        await insertGeneratedImage(page, frame);

        // 7. Set as background via Slides API (slideIndex = slideNum - 1)
        await sleep(2000);
        const bgResult = await setImageAsBackground(page, frame, slideNum - 1);

        // 8. 背景設定後、パネルを閉じる
        if (bgResult) {
          console.log('  パネルをリセット中...');
          await closePanel(page);
          await sleep(1000);
          success = true;
          console.log(`  ✓ 背景設定成功`);
          results.push({ slide: slideNum, status: 'success', attempt });
        } else {
          console.log(`  ⚠ 背景設定失敗、リトライへ`);
          // Escape to close any menus
          await page.keyboard.press('Escape');
          await sleep(500);
          if (attempt >= maxRetries) {
            results.push({ slide: slideNum, status: 'failed', reason: '背景設定失敗', attempt });
          }
        }

      } catch (err) {
        console.error(`  ✗ エラー: ${err.message}`);
        if (attempt >= maxRetries) {
          results.push({ slide: slideNum, status: 'error', error: err.message, attempt });
        }
        // Try to recover
        try {
          await page.keyboard.press('Escape');
          await sleep(500);
          await page.keyboard.press('Escape');
          await sleep(500);
        } catch (e) {}
      }
    }

    // Cooldown between slides
    if (si < specificSlides.length - 1) {
      console.log(`  クールダウン: ${delayMs / 1000}秒...`);
      await sleep(delayMs);
    }
  }

  // Summary
  const totalTime = ((Date.now() - startTime) / 1000).toFixed(0);
  const successCount = results.filter(r => r.status === 'success').length;
  console.log('\n=== 結果 ===');
  console.log(`成功: ${successCount} / ${results.length}`);
  console.log(`所要時間: ${totalTime}秒`);
  for (const r of results) {
    console.log(`  スライド${r.slide}: ${r.status}${r.reason ? ` (${r.reason})` : ''}${r.error ? ` (${r.error})` : ''}`);
  }

  const outPath = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..', 'image_mode_results.json');
  fs.writeFileSync(outPath, JSON.stringify({ timestamp: new Date().toISOString(), results }, null, 2));

  browser.disconnect();
}

main().catch(err => { console.error('Fatal:', err); process.exit(1); });
