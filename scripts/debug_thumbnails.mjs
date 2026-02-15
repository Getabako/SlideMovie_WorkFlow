#!/usr/bin/env node
/**
 * サムネイルとダイアログのDOM構造を詳細調査
 */
import puppeteer from 'puppeteer-core';

const browser = await puppeteer.connect({
  browserURL: 'http://127.0.0.1:18800',
  defaultViewport: null,
  protocolTimeout: 120000,
});
const pages = await browser.pages();
const page = pages.find(p => p.url().includes('docs.google.com/presentation'));
const frame = page.frames().find(f => f.url().includes('slide=')) || page.mainFrame();

// パネル内のサムネイル（menuitem）を詳細に調査
const items = await frame.evaluate(() => {
  const aside = document.querySelector('aside[aria-label="画像作成サポート"]');
  if (!aside) return 'aside not found';
  const menuItems = aside.querySelectorAll('[role="menuitem"]');
  return Array.from(menuItems).map((item, idx) => {
    const rect = item.getBoundingClientRect();
    const text = item.textContent?.trim().substring(0, 60) || '';
    const imgs = item.querySelectorAll('img');
    return {
      idx,
      text,
      visible: rect.height > 0,
      size: Math.round(rect.width) + 'x' + Math.round(rect.height),
      pos: Math.round(rect.x) + ',' + Math.round(rect.y),
      hasImg: imgs.length > 0,
      tag: item.tagName,
      tabindex: item.getAttribute('tabindex'),
    };
  });
});
console.log('menuItems:', JSON.stringify(items, null, 2));

// ダイアログのDOM構造を調査
const dialogInfo = await frame.evaluate(() => {
  const dialogs = document.querySelectorAll('[role="dialog"]');
  return Array.from(dialogs).map(d => {
    const style = window.getComputedStyle(d);
    const parent = d.parentElement;
    const parentStyle = parent ? window.getComputedStyle(parent) : null;
    return {
      id: d.id,
      className: d.className?.substring(0, 80),
      display: style.display,
      parentTag: parent?.tagName,
      parentDisplay: parentStyle?.display,
      parentClass: parent?.className?.substring(0, 80),
      ariaHidden: d.getAttribute('aria-hidden'),
      styleAttr: d.getAttribute('style')?.substring(0, 120),
    };
  });
});
console.log('\ndialogs:', JSON.stringify(dialogInfo, null, 2));

// サムネイルクリックを試行して効果を確認
const lastThumb = await frame.evaluate(() => {
  const aside = document.querySelector('aside[aria-label="画像作成サポート"]');
  if (!aside) return null;
  const menuItems = aside.querySelectorAll('[role="menuitem"]');
  let last = null;
  for (const item of menuItems) {
    const rect = item.getBoundingClientRect();
    if (rect.height > 0) {
      last = { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 };
    }
  }
  return last;
});

if (lastThumb) {
  console.log('\nサムネイルクリック: ', lastThumb);
  await page.mouse.click(lastThumb.x, lastThumb.y);
  await new Promise(r => setTimeout(r, 3000));

  // クリック後のダイアログ状態
  const afterClick = await frame.evaluate(() => {
    const dialogs = document.querySelectorAll('[role="dialog"]');
    return Array.from(dialogs).map(d => {
      const style = window.getComputedStyle(d);
      return {
        display: style.display,
        visible: d.getBoundingClientRect().height > 0,
        text: d.textContent?.substring(0, 100),
      };
    });
  });
  console.log('\nクリック後のダイアログ:', JSON.stringify(afterClick, null, 2));

  // さらに5秒待つ
  await new Promise(r => setTimeout(r, 5000));
  const afterWait = await frame.evaluate(() => {
    const dialogs = document.querySelectorAll('[role="dialog"]');
    return Array.from(dialogs).map(d => {
      const style = window.getComputedStyle(d);
      return {
        display: style.display,
        visible: d.getBoundingClientRect().height > 0,
        text: d.textContent?.substring(0, 100),
      };
    });
  });
  console.log('\n5秒後のダイアログ:', JSON.stringify(afterWait, null, 2));
}

browser.disconnect();
