#!/usr/bin/env node
/**
 * サムネイルをスクロール→クリックしてダイアログが開くか確認
 */
import puppeteer from 'puppeteer-core';

const sleep = ms => new Promise(r => setTimeout(r, ms));

const browser = await puppeteer.connect({
  browserURL: 'http://127.0.0.1:18800',
  defaultViewport: null,
  protocolTimeout: 120000,
});
const pages = await browser.pages();
const page = pages.find(p => p.url().includes('docs.google.com/presentation'));
const frame = page.frames().find(f => f.url().includes('slide=')) || page.mainFrame();

console.log('=== 方法1: scrollIntoView + mouse click ===');

// 最後のサムネイルをスクロールして表示させる
const thumbInfo = await frame.evaluate(() => {
  const aside = document.querySelector('aside[aria-label="画像作成サポート"]');
  if (!aside) return null;
  const menuItems = aside.querySelectorAll('[role="menuitem"]');
  const last = menuItems[menuItems.length - 1];
  if (!last) return null;

  // スクロールして表示
  last.scrollIntoView({ behavior: 'instant', block: 'center' });

  // 少し待ってからrectを取得
  return new Promise(resolve => {
    setTimeout(() => {
      const rect = last.getBoundingClientRect();
      resolve({
        x: rect.x + rect.width / 2,
        y: rect.y + rect.height / 2,
        visible: rect.height > 0,
        text: last.textContent?.trim().substring(0, 40),
        inViewport: rect.y >= 0 && rect.y < window.innerHeight,
      });
    }, 500);
  });
});

console.log('サムネイル情報:', JSON.stringify(thumbInfo, null, 2));

if (thumbInfo && thumbInfo.inViewport) {
  console.log('クリック中...');
  await page.mouse.click(thumbInfo.x, thumbInfo.y);
  await sleep(3000);

  // ダイアログ状態確認
  const dialogState = await frame.evaluate(() => {
    const dialogs = document.querySelectorAll('[role="dialog"]');
    return Array.from(dialogs).map(d => {
      const style = window.getComputedStyle(d);
      return {
        display: style.display,
        visible: d.getBoundingClientRect().height > 0,
        text: d.textContent?.substring(0, 80),
      };
    });
  });
  console.log('mouse click後のダイアログ:', JSON.stringify(dialogState, null, 2));
}

// 閉じる
await sleep(1000);

console.log('\n=== 方法2: JavaScript element.click() ===');

// まずダイアログを閉じる
await frame.evaluate(() => {
  const dialogs = document.querySelectorAll('[role="dialog"]');
  for (const d of dialogs) {
    const btns = d.querySelectorAll('button, [role="button"]');
    for (const btn of btns) {
      const label = btn.getAttribute('aria-label') || btn.textContent?.trim() || '';
      if (label === '閉じる' || label === 'Close') {
        btn.click();
        return;
      }
    }
  }
});
await sleep(1000);

// JavaScript click
await frame.evaluate(() => {
  const aside = document.querySelector('aside[aria-label="画像作成サポート"]');
  if (!aside) return;
  const menuItems = aside.querySelectorAll('[role="menuitem"]');
  const last = menuItems[menuItems.length - 1];
  if (last) last.click();
});
await sleep(3000);

const dialogState2 = await frame.evaluate(() => {
  const dialogs = document.querySelectorAll('[role="dialog"]');
  return Array.from(dialogs).map(d => {
    const style = window.getComputedStyle(d);
    return {
      display: style.display,
      visible: d.getBoundingClientRect().height > 0,
      text: d.textContent?.substring(0, 80),
    };
  });
});
console.log('element.click()後のダイアログ:', JSON.stringify(dialogState2, null, 2));

// 方法3: dispatchEvent
await sleep(1000);
await frame.evaluate(() => {
  const dialogs = document.querySelectorAll('[role="dialog"]');
  for (const d of dialogs) {
    const btns = d.querySelectorAll('button, [role="button"]');
    for (const btn of btns) {
      const label = btn.getAttribute('aria-label') || btn.textContent?.trim() || '';
      if (label === '閉じる' || label === 'Close') {
        btn.click();
        return;
      }
    }
  }
});
await sleep(1000);

console.log('\n=== 方法3: dispatchEvent(MouseEvent) ===');
await frame.evaluate(() => {
  const aside = document.querySelector('aside[aria-label="画像作成サポート"]');
  if (!aside) return;
  const menuItems = aside.querySelectorAll('[role="menuitem"]');
  const last = menuItems[menuItems.length - 1];
  if (!last) return;
  last.scrollIntoView({ behavior: 'instant', block: 'center' });
  const rect = last.getBoundingClientRect();
  const opts = { bubbles: true, cancelable: true, clientX: rect.x + rect.width / 2, clientY: rect.y + rect.height / 2 };
  last.dispatchEvent(new MouseEvent('mousedown', opts));
  last.dispatchEvent(new MouseEvent('mouseup', opts));
  last.dispatchEvent(new MouseEvent('click', opts));
});
await sleep(3000);

const dialogState3 = await frame.evaluate(() => {
  const dialogs = document.querySelectorAll('[role="dialog"]');
  return Array.from(dialogs).map(d => {
    const style = window.getComputedStyle(d);
    return {
      display: style.display,
      visible: d.getBoundingClientRect().height > 0,
      text: d.textContent?.substring(0, 80),
    };
  });
});
console.log('dispatchEvent後のダイアログ:', JSON.stringify(dialogState3, null, 2));

// 10秒待ってもう一度確認
await sleep(10000);
const dialogState4 = await frame.evaluate(() => {
  const dialogs = document.querySelectorAll('[role="dialog"]');
  return Array.from(dialogs).map(d => {
    const style = window.getComputedStyle(d);
    return {
      display: style.display,
      visible: d.getBoundingClientRect().height > 0,
      styleAttr: d.getAttribute('style')?.substring(0, 120),
      text: d.textContent?.substring(0, 80),
    };
  });
});
console.log('13秒後のダイアログ:', JSON.stringify(dialogState4, null, 2));

browser.disconnect();
