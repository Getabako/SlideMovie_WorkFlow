import puppeteer from 'puppeteer-core';

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

const browser = await puppeteer.connect({ browserURL: 'http://127.0.0.1:18800' });
const pages = await browser.pages();
const slidesPage = pages.find(p => p.url().includes('presentation'));
if (slidesPage == null) { console.log('Page not found'); process.exit(1); }

const frame = slidesPage.frames().find(f => f.url().includes('slide=')) || slidesPage.mainFrame();

// 1. Navigate to slide 20
await slidesPage.mouse.click(700, 400);
await sleep(300);
await slidesPage.keyboard.press('Home');
await sleep(500);
for (let i = 0; i < 19; i++) {
  await slidesPage.keyboard.press('PageDown');
  await sleep(200);
}
await sleep(500);
console.log('Navigated to slide 20');

// 2. Ensure slide tab is selected
const tabState = await frame.evaluate(() => {
  const tabs = document.querySelectorAll('[role="tab"]');
  const result = [];
  for (const tab of tabs) {
    const rect = tab.getBoundingClientRect();
    if (rect.x > 380 && rect.height > 0) {
      result.push({ text: (tab.textContent || '').trim(), selected: tab.getAttribute('aria-selected') });
    }
  }
  return result;
});
console.log('Tab state:', JSON.stringify(tabState));

// 3. Find textarea and type
const taInfo = await frame.evaluate(() => {
  const textareas = document.querySelectorAll('textarea');
  for (const ta of textareas) {
    if (ta.offsetHeight > 0) {
      const rect = ta.getBoundingClientRect();
      return { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2, placeholder: ta.placeholder.substring(0, 50) };
    }
  }
  return null;
});
console.log('Textarea:', JSON.stringify(taInfo));

if (taInfo) {
  await slidesPage.mouse.click(taInfo.x, taInfo.y, { clickCount: 3 });
  await sleep(200);
  await slidesPage.keyboard.down('Meta');
  await slidesPage.keyboard.press('a');
  await slidesPage.keyboard.up('Meta');
  await slidesPage.keyboard.press('Backspace');
  await sleep(300);
  await slidesPage.keyboard.type('Green gradient background with 5 ascending steps and checkmarks', { delay: 10 });
  await sleep(1000);
}

// 4. Screenshot before submit
await slidesPage.screenshot({ path: 'before_submit.png' });
console.log('Before submit screenshot saved');

// 5. Find all "作成" buttons and their states
const btns = await frame.evaluate(() => {
  const allBtns = document.querySelectorAll('button');
  const result = [];
  for (const btn of allBtns) {
    const label = btn.getAttribute('aria-label') || '';
    const classes = btn.className?.toString() || '';
    if (label.includes('作成') || classes.includes('image-synthesis')) {
      const rect = btn.getBoundingClientRect();
      result.push({
        label, classes: classes.substring(0, 100),
        disabled: btn.disabled, visible: rect.height > 0,
        x: Math.round(rect.x + rect.width / 2), y: Math.round(rect.y + rect.height / 2),
      });
    }
  }
  return result;
});
console.log('Create buttons:', JSON.stringify(btns, null, 2));

// 6. Click the enabled visible button
const targetBtn = btns.find(b => b.visible && (b.label === '作成' || b.classes.includes('image-synthesis-creation-button')));
if (targetBtn) {
  console.log('Clicking button at', targetBtn.x, targetBtn.y, '(disabled:', targetBtn.disabled, ')');
  await slidesPage.mouse.click(targetBtn.x, targetBtn.y);

  // 7. Monitor for 60 seconds
  for (let i = 0; i < 12; i++) {
    await sleep(5000);
    await slidesPage.screenshot({ path: `gen_${i+1}.png` });

    const status = await frame.evaluate(() => {
      // Check ALL buttons for generation status
      const allBtns = document.querySelectorAll('button, [role="button"]');
      const genBtns = [];
      for (const btn of allBtns) {
        const label = btn.getAttribute('aria-label') || '';
        const text = (btn.textContent || '').trim();
        if (label.includes('作成') || text.includes('作成') || label.includes('挿入') || text.includes('挿入')) {
          const rect = btn.getBoundingClientRect();
          if (rect.height > 0) {
            genBtns.push({ label: label.substring(0, 30), text: text.substring(0, 30), disabled: btn.disabled });
          }
        }
      }
      // Check for dialogs
      const dialogs = document.querySelectorAll('[role="dialog"]');
      const visibleDialogs = [];
      for (const d of dialogs) {
        const style = window.getComputedStyle(d);
        if (style.display !== 'none') {
          visibleDialogs.push((d.textContent || '').substring(0, 80));
        }
      }
      // Check for menuitem (thumbnails)
      const menuItems = document.querySelectorAll('[role="menuitem"]');
      let menuCount = 0;
      for (const item of menuItems) {
        if ((item.textContent || '').includes('プレビュー')) menuCount++;
      }
      return { genBtns, dialogs: visibleDialogs, previewMenuItems: menuCount };
    });
    console.log(`${(i+1)*5}s:`, JSON.stringify(status));
  }
}

browser.disconnect();
