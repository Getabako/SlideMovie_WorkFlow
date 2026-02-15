import puppeteer from 'puppeteer-core';

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

const browser = await puppeteer.connect({ browserURL: 'http://127.0.0.1:18800' });
const pages = await browser.pages();
const slidesPage = pages.find(p => p.url().includes('presentation'));
if (slidesPage == null) { console.log('Page not found'); process.exit(1); }

// Step 1: Navigate away
console.log('Step 1: Navigate away...');
await slidesPage.goto('https://docs.google.com/presentation/', { waitUntil: 'networkidle2', timeout: 60000 });
await sleep(3000);

// Step 2: Navigate back to presentation
console.log('Step 2: Navigate back to presentation...');
await slidesPage.goto('https://docs.google.com/presentation/d/1_hNmyanUhPnvLhrb-qzAFjcB8ZYttIGHf9bWL5Ity6A/edit', {
  waitUntil: 'networkidle2',
  timeout: 60000
});
await sleep(8000);

// Step 3: Find frame and check slide count
const frame = slidesPage.frames().find(f => f.url().includes('slide=')) || slidesPage.mainFrame();
console.log('Frame URL:', frame.url().substring(0, 120));

const thumbnails = await frame.evaluate(() => document.querySelectorAll('g.punch-filmstrip-thumbnail').length);
console.log('Thumbnails:', thumbnails);

// Step 4: Click on slide area to focus
await slidesPage.mouse.click(700, 500);
await sleep(1000);

// Step 5: Try to open the panel
const panelBtn = await frame.evaluate(() => {
  const allBtns = document.querySelectorAll('[role="button"]');
  for (const btn of allBtns) {
    const label = btn.getAttribute('aria-label') || '';
    if (label === 'スライド画像を作成する' || label === '画像作成サポート') {
      const rect = btn.getBoundingClientRect();
      if (rect.width > 0 && rect.height > 0) {
        return { label, x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 };
      }
    }
  }
  return null;
});

if (panelBtn) {
  console.log('Step 5: Clicking', panelBtn.label);
  await slidesPage.mouse.click(panelBtn.x, panelBtn.y);
  await sleep(8000);

  // Check panel
  const panelState = await frame.evaluate(() => {
    const aside = document.querySelector('aside[aria-label="画像作成サポート"]');
    if (aside == null) return { found: false };
    const childCount = aside.children.length;
    const textareas = aside.querySelectorAll('textarea');
    const visibleTAs = Array.from(textareas).filter(t => t.offsetHeight > 0);
    const html = aside.innerHTML.substring(0, 500);
    return { found: true, childCount, textareas: textareas.length, visibleTAs: visibleTAs.length, html };
  });
  console.log('Panel state:', JSON.stringify(panelState, null, 2));

  if (panelState.visibleTAs > 0) {
    console.log('SUCCESS: Textarea found, panel is ready');
  } else if (panelState.childCount === 0) {
    console.log('FAIL: Panel is empty. Feature may be rate-limited or unavailable.');

    // Try waiting more
    console.log('Waiting 30s and rechecking...');
    await sleep(30000);
    const recheck = await frame.evaluate(() => {
      const aside = document.querySelector('aside[aria-label="画像作成サポート"]');
      if (aside == null) return { found: false };
      return { found: true, childCount: aside.children.length, html: aside.innerHTML.substring(0, 300) };
    });
    console.log('Recheck:', JSON.stringify(recheck));
  }
}

browser.disconnect();
