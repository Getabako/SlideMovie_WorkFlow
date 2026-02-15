import puppeteer from 'puppeteer-core';
const sleep = ms => new Promise(r => setTimeout(r, ms));

const browser = await puppeteer.connect({ browserURL: 'http://127.0.0.1:18800' });
const pages = await browser.pages();
const page = pages.find(p => p.url().includes('presentation'));
const frame = page.mainFrame();

// Step 1: Take screenshot before
await page.screenshot({ path: 'step1_before.png' });
console.log('Step 1: Screenshot before click');

// Step 2: Find button
const btn = await frame.evaluate(() => {
  const btns = document.querySelectorAll('[role="button"]');
  for (const b of btns) {
    const label = b.getAttribute('aria-label') || '';
    if (label === '画像作成サポート') {
      const rect = b.getBoundingClientRect();
      return { x: Math.round(rect.x + rect.width / 2), y: Math.round(rect.y + rect.height / 2), visible: rect.height > 0 };
    }
  }
  return null;
});
console.log('Button:', JSON.stringify(btn));

// Step 3: Click it
if (btn && btn.visible) {
  console.log('Clicking at', btn.x, btn.y);
  await page.mouse.click(btn.x, btn.y);
  await sleep(5000);

  // Step 4: Check state
  const state = await frame.evaluate(() => {
    const textareas = document.querySelectorAll('textarea');
    const visibleTa = Array.from(textareas).find(t => t.offsetHeight > 0);
    const aside = document.querySelector('aside[aria-label="画像作成サポート"]');
    return {
      textareaFound: visibleTa ? true : false,
      asideFound: aside ? true : false,
      totalTextareas: textareas.length,
      viewportWidth: window.innerWidth,
      viewportHeight: window.innerHeight
    };
  });
  console.log('State after click:', JSON.stringify(state));

  // Step 5: Screenshot
  await page.screenshot({ path: 'step2_after_click.png' });
  console.log('Step 2: Screenshot after click');

  // Step 6: If textarea not found, try clicking slide area first, then button
  if (!state.textareaFound) {
    console.log('Textarea not found. Trying: click slide area first, then button...');
    await page.mouse.click(400, 300);
    await sleep(500);
    await page.mouse.click(btn.x, btn.y);
    await sleep(5000);

    const state2 = await frame.evaluate(() => {
      const textareas = document.querySelectorAll('textarea');
      return { textareaFound: Array.from(textareas).some(t => t.offsetHeight > 0) };
    });
    console.log('State after retry:', JSON.stringify(state2));
    await page.screenshot({ path: 'step3_retry.png' });
  }
}

browser.disconnect();
