import puppeteer from 'puppeteer-core';

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

const browser = await puppeteer.connect({ browserURL: 'http://127.0.0.1:18800' });
const pages = await browser.pages();
const slidesPage = pages.find(p => p.url().includes('presentation'));
if (slidesPage == null) { console.log('Page not found'); process.exit(1); }

const frame = slidesPage.frames().find(f => f.url().includes('slide=')) || slidesPage.mainFrame();

// Check panel content
const panelInfo = await frame.evaluate(() => {
  const aside = document.querySelector('aside[aria-label="画像作成サポート"]');
  if (aside == null) return { found: false };

  // Get all input elements
  const inputs = aside.querySelectorAll('input, textarea, [contenteditable]');
  const inputList = [];
  for (const inp of inputs) {
    const rect = inp.getBoundingClientRect();
    inputList.push({
      tag: inp.tagName,
      type: inp.type || '',
      contentEditable: inp.contentEditable,
      visible: rect.height > 0,
      w: rect.width,
      h: rect.height,
    });
  }

  // Get all buttons
  const btns = aside.querySelectorAll('button, [role="button"]');
  const btnList = [];
  for (const btn of btns) {
    const label = btn.getAttribute('aria-label') || '';
    const text = (btn.textContent || '').trim().substring(0, 30);
    const rect = btn.getBoundingClientRect();
    btnList.push({ label, text, visible: rect.height > 0, disabled: btn.disabled });
  }

  // Get tabs
  const tabs = aside.querySelectorAll('[role="tab"]');
  const tabList = [];
  for (const tab of tabs) {
    const text = (tab.textContent || '').trim();
    const selected = tab.getAttribute('aria-selected');
    tabList.push({ text, selected });
  }

  // Get text content
  const text = (aside.textContent || '').substring(0, 500);

  return { found: true, inputs: inputList, buttons: btnList, tabs: tabList, text };
});

console.log(JSON.stringify(panelInfo, null, 2));

browser.disconnect();
