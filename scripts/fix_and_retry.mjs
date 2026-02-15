import puppeteer from 'puppeteer-core';

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

const browser = await puppeteer.connect({ browserURL: 'http://127.0.0.1:18800' });
const pages = await browser.pages();
const slidesPage = pages.find(p => p.url().includes('presentation'));
if (slidesPage == null) { console.log('Page not found'); process.exit(1); }

// Navigate to the presentation URL with slide=1
const presUrl = 'https://docs.google.com/presentation/d/1_hNmyanUhPnvLhrb-qzAFjcB8ZYttIGHf9bWL5Ity6A/edit#slide=id.slide_000';
console.log('Navigating to:', presUrl);
await slidesPage.goto(presUrl, { waitUntil: 'networkidle2', timeout: 60000 });
await sleep(5000);

const frame = slidesPage.frames().find(f => f.url().includes('slide=')) || slidesPage.mainFrame();
console.log('Frame URL:', frame.url().substring(0, 120));

// Count slides
const thumbnails = await frame.evaluate(() => document.querySelectorAll('g.punch-filmstrip-thumbnail').length);
console.log('Thumbnails:', thumbnails);

// Try to click on the main editing area first
await slidesPage.mouse.click(700, 500);
await sleep(1000);

// Check panel button
const state = await frame.evaluate(() => {
  // Look for all buttons with aria-labels
  const allBtns = document.querySelectorAll('[role="button"]');
  const interesting = [];
  for (const btn of allBtns) {
    const label = btn.getAttribute('aria-label') || '';
    if (label.includes('画像') || label.includes('サポート') || label.includes('Gemini') || label.includes('スライド画像')) {
      const rect = btn.getBoundingClientRect();
      interesting.push({ label, x: rect.x + rect.width / 2, y: rect.y + rect.height / 2, w: rect.width, h: rect.height });
    }
  }
  return interesting;
});
console.log('Buttons with 画像/Gemini:', JSON.stringify(state, null, 2));

if (state.length > 0) {
  console.log('Clicking:', state[0].label);
  await slidesPage.mouse.click(state[0].x, state[0].y);
  await sleep(5000);

  const afterClick = await frame.evaluate(() => {
    const textareas = document.querySelectorAll('textarea');
    const visibleTAs = Array.from(textareas).filter(t => t.offsetHeight > 0).length;
    const aside = document.querySelector('aside[aria-label="画像作成サポート"]');
    const allAsides = document.querySelectorAll('aside');
    const asideInfo = [];
    for (const a of allAsides) {
      const label = a.getAttribute('aria-label') || '(no label)';
      const rect = a.getBoundingClientRect();
      asideInfo.push({ label, w: rect.width, h: rect.height });
    }
    return { visibleTAs, hasPanel: (aside != null), asides: asideInfo };
  });
  console.log('After click:', JSON.stringify(afterClick, null, 2));
}

browser.disconnect();
