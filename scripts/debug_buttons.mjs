import puppeteer from 'puppeteer-core';

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

const browser = await puppeteer.connect({ browserURL: 'http://127.0.0.1:18800' });
const pages = await browser.pages();
const slidesPage = pages.find(p => p.url().includes('presentation'));
if (slidesPage == null) { console.log('Page not found'); process.exit(1); }

const frame = slidesPage.frames().find(f => f.url().includes('slide=')) || slidesPage.mainFrame();

// First, type some text into the textarea
const textareaInfo = await frame.evaluate(() => {
  const textareas = document.querySelectorAll('textarea');
  for (const ta of textareas) {
    if (ta.offsetHeight > 0 && ta.offsetWidth > 0) {
      const rect = ta.getBoundingClientRect();
      return { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2, found: true };
    }
  }
  return { found: false };
});

if (textareaInfo.found) {
  // Click and type
  await slidesPage.mouse.click(textareaInfo.x, textareaInfo.y, { clickCount: 3 });
  await sleep(200);
  await slidesPage.keyboard.type('test prompt for button detection', { delay: 5 });
  await sleep(1000);
}

// Now find ALL buttons near the panel area (right side of the screen)
const allButtons = await frame.evaluate(() => {
  const allBtns = document.querySelectorAll('button, [role="button"]');
  const result = [];
  for (const btn of allBtns) {
    const rect = btn.getBoundingClientRect();
    // Only look at buttons in the panel area (right side, x > 400)
    if (rect.x > 380 && rect.height > 0 && rect.width > 0) {
      const label = btn.getAttribute('aria-label') || '';
      const text = (btn.textContent || '').trim().substring(0, 50);
      const dataTooltip = btn.getAttribute('data-tooltip') || '';
      const classes = (btn.className || '').toString().substring(0, 100);
      result.push({
        label, text, dataTooltip,
        disabled: btn.disabled,
        x: Math.round(rect.x), y: Math.round(rect.y),
        w: Math.round(rect.width), h: Math.round(rect.height),
        tag: btn.tagName,
        classes: classes.substring(0, 80),
      });
    }
  }
  return result;
});

console.log('All buttons in panel area:');
for (const btn of allButtons) {
  console.log(`  [${btn.x},${btn.y}] ${btn.w}x${btn.h} | label="${btn.label}" text="${btn.text}" disabled=${btn.disabled} | ${btn.classes}`);
}

// Also check for SVG icons / clickable elements near the send area
const iconArea = await frame.evaluate(() => {
  const elements = document.querySelectorAll('*');
  const result = [];
  for (const el of elements) {
    const rect = el.getBoundingClientRect();
    // Look at the bottom-right of the panel area (around x:650-700, y:470-520 based on screenshot)
    if (rect.x > 600 && rect.y > 440 && rect.y < 540 && rect.height > 5 && rect.width > 5 && rect.height < 100) {
      const label = el.getAttribute('aria-label') || '';
      const role = el.getAttribute('role') || '';
      const tag = el.tagName;
      const text = (el.textContent || '').trim().substring(0, 30);
      if (label || role === 'button' || tag === 'BUTTON' || tag === 'SVG' || tag === 'svg') {
        result.push({
          tag, label, role, text,
          x: Math.round(rect.x), y: Math.round(rect.y),
          w: Math.round(rect.width), h: Math.round(rect.height),
        });
      }
    }
  }
  return result;
});

console.log('\nElements near send area:');
for (const el of iconArea) {
  console.log(`  [${el.x},${el.y}] ${el.w}x${el.h} | tag=${el.tag} label="${el.label}" role="${el.role}" text="${el.text}"`);
}

browser.disconnect();
