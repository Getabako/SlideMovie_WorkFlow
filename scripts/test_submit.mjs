import puppeteer from 'puppeteer-core';

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

const browser = await puppeteer.connect({ browserURL: 'http://127.0.0.1:18800' });
const pages = await browser.pages();
const slidesPage = pages.find(p => p.url().includes('presentation'));
if (slidesPage == null) { console.log('Page not found'); process.exit(1); }

const frame = slidesPage.frames().find(f => f.url().includes('slide=')) || slidesPage.mainFrame();

// Type prompt
const textareaInfo = await frame.evaluate(() => {
  const textareas = document.querySelectorAll('textarea');
  for (const ta of textareas) {
    if (ta.offsetHeight > 0) {
      const rect = ta.getBoundingClientRect();
      return { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 };
    }
  }
  return null;
});

if (textareaInfo) {
  // Clear and type
  await slidesPage.mouse.click(textareaInfo.x, textareaInfo.y, { clickCount: 3 });
  await sleep(200);
  await slidesPage.keyboard.down('Meta');
  await slidesPage.keyboard.press('a');
  await slidesPage.keyboard.up('Meta');
  await slidesPage.keyboard.press('Backspace');
  await sleep(300);
  await slidesPage.keyboard.type('Dark blue background with orange warning graph', { delay: 10 });
  await sleep(1000);

  // Screenshot before clicking
  await slidesPage.screenshot({ path: 'before_click.png' });
  console.log('Before click screenshot saved');

  // Find and click the "作成" button at the known position
  const btnInfo = await frame.evaluate(() => {
    const allBtns = document.querySelectorAll('button');
    for (const btn of allBtns) {
      const label = btn.getAttribute('aria-label') || '';
      if (label === '作成' && btn.offsetHeight > 0) {
        const rect = btn.getBoundingClientRect();
        return { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2, disabled: btn.disabled, classes: btn.className.substring(0, 100) };
      }
    }
    return null;
  });

  console.log('Button info:', JSON.stringify(btnInfo));

  if (btnInfo) {
    await slidesPage.mouse.click(btnInfo.x, btnInfo.y);
    console.log('Clicked button');

    // Wait and take screenshots
    for (let i = 0; i < 6; i++) {
      await sleep(5000);
      await slidesPage.screenshot({ path: `after_click_${i+1}.png` });
      console.log(`Screenshot ${i+1} saved (${(i+1)*5}s)`);

      // Check for generation indicators
      const status = await frame.evaluate(() => {
        const aside = document.querySelector('aside[aria-label="画像作成サポート"]');
        const allBtns = document.querySelectorAll('button, [role="button"]');
        const generating = [];
        for (const btn of allBtns) {
          const label = btn.getAttribute('aria-label') || '';
          const text = (btn.textContent || '').trim();
          if (text.includes('作成しています') || label.includes('作成しています') || text.includes('生成中')) {
            generating.push({ label, text: text.substring(0, 50) });
          }
        }

        // Check dialogs
        const dialogs = document.querySelectorAll('[role="dialog"]');
        const dialogInfo = [];
        for (const d of dialogs) {
          const style = window.getComputedStyle(d);
          if (style.display !== 'none') {
            dialogInfo.push({ display: style.display, text: (d.textContent || '').substring(0, 100) });
          }
        }

        // Check for any loading spinners
        const spinners = document.querySelectorAll('[role="progressbar"], .progress-indicator, [class*="spinner"], [class*="loading"]');

        return { generating, dialogs: dialogInfo, spinnerCount: spinners.length };
      });
      console.log('Status:', JSON.stringify(status));
    }
  }
}

browser.disconnect();
