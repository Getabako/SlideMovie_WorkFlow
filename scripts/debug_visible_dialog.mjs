#!/usr/bin/env node
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

// Click last thumbnail with scrollIntoView
await frame.evaluate(() => {
  const aside = document.querySelector('aside[aria-label="画像作成サポート"]');
  if (!aside) return;
  const menuItems = aside.querySelectorAll('[role="menuitem"]');
  const last = menuItems[menuItems.length - 1];
  if (last) last.scrollIntoView({ behavior: 'instant', block: 'center' });
});
await sleep(500);

const thumbCoords = await frame.evaluate(() => {
  const aside = document.querySelector('aside[aria-label="画像作成サポート"]');
  const menuItems = aside.querySelectorAll('[role="menuitem"]');
  const last = menuItems[menuItems.length - 1];
  if (!last) return null;
  const rect = last.getBoundingClientRect();
  return { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 };
});

if (thumbCoords) {
  await page.mouse.click(thumbCoords.x, thumbCoords.y);
  await sleep(3000);
}

// Now check all dialogs' buttons
const dialogInfo = await frame.evaluate(() => {
  const dialogs = document.querySelectorAll('[role="dialog"]');
  return Array.from(dialogs).map(d => {
    const style = window.getComputedStyle(d);
    const rect = d.getBoundingClientRect();
    const btns = d.querySelectorAll('button, [role="button"]');
    return {
      display: style.display,
      visible: rect.height > 0,
      size: `${Math.round(rect.width)}x${Math.round(rect.height)}`,
      buttons: Array.from(btns).map(btn => {
        const r = btn.getBoundingClientRect();
        return {
          text: btn.textContent?.trim().substring(0, 50),
          label: btn.getAttribute('aria-label')?.substring(0, 50),
          visible: r.height > 0 && r.width > 0,
          size: `${Math.round(r.width)}x${Math.round(r.height)}`,
          tag: btn.tagName,
          disabled: btn.disabled,
        };
      }),
    };
  });
});

console.log(JSON.stringify(dialogInfo, null, 2));

browser.disconnect();
