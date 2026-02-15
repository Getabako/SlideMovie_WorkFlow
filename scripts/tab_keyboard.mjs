import puppeteer from 'puppeteer-core';

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

const browser = await puppeteer.connect({ browserURL: 'http://127.0.0.1:18800' });
const pages = await browser.pages();
const slidesPage = pages.find(p => p.url().includes('presentation'));
if (slidesPage == null) { console.log('Page not found'); process.exit(1); }

const frame = slidesPage.frames().find(f => f.url().includes('slide=')) || slidesPage.mainFrame();

// Check current tab state
async function getSelectedTab() {
  return frame.evaluate(() => {
    const tabs = document.querySelectorAll('[role="tab"]');
    for (const tab of tabs) {
      if (tab.getAttribute('aria-selected') === 'true') return (tab.textContent || '').trim();
    }
    return 'none';
  });
}

console.log('Current tab:', await getSelectedTab());

// Method: Close panel, open fresh via different approach
console.log('\nClosing panel...');
const closeBtn = await frame.evaluate(() => {
  const btns = document.querySelectorAll('button, [role="button"]');
  for (const btn of btns) {
    const label = btn.getAttribute('aria-label') || '';
    if (label === '閉じる') {
      const rect = btn.getBoundingClientRect();
      if (rect.x > 400 && rect.y < 100 && rect.height > 0) {
        return { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 };
      }
    }
  }
  return null;
});

if (closeBtn) {
  await slidesPage.mouse.click(closeBtn.x, closeBtn.y);
  await sleep(2000);
  console.log('Panel closed');
}

// Now try opening via the toolbar "スライド画像を作成する" button
console.log('Opening panel via toolbar button...');
const toolbarBtn = await frame.evaluate(() => {
  const btns = document.querySelectorAll('[role="button"]');
  for (const btn of btns) {
    const label = btn.getAttribute('aria-label') || '';
    if (label === 'スライド画像を作成する') {
      const rect = btn.getBoundingClientRect();
      if (rect.height > 0) return { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 };
    }
  }
  return null;
});

if (toolbarBtn) {
  await slidesPage.mouse.click(toolbarBtn.x, toolbarBtn.y);
  await sleep(3000);
  console.log('Panel opened via toolbar');
  console.log('Current tab:', await getSelectedTab());
}

// If still on 画像 tab, try closing again and opening via sidebar
if (await getSelectedTab() !== 'スライド') {
  console.log('\nStill not on スライド tab. Trying sidebar button...');
  const closeBtn2 = await frame.evaluate(() => {
    const btns = document.querySelectorAll('button, [role="button"]');
    for (const btn of btns) {
      const label = btn.getAttribute('aria-label') || '';
      if (label === '閉じる') {
        const rect = btn.getBoundingClientRect();
        if (rect.x > 400 && rect.y < 100 && rect.height > 0) {
          return { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 };
        }
      }
    }
    return null;
  });
  if (closeBtn2) {
    await slidesPage.mouse.click(closeBtn2.x, closeBtn2.y);
    await sleep(2000);
  }

  const sidebarBtn = await frame.evaluate(() => {
    const btns = document.querySelectorAll('[role="button"]');
    for (const btn of btns) {
      const label = btn.getAttribute('aria-label') || '';
      if (label === '画像作成サポート') {
        const rect = btn.getBoundingClientRect();
        if (rect.height > 0) return { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 };
      }
    }
    return null;
  });

  if (sidebarBtn) {
    await slidesPage.mouse.click(sidebarBtn.x, sidebarBtn.y);
    await sleep(3000);
    console.log('Panel opened via sidebar');
    console.log('Current tab:', await getSelectedTab());
  }
}

// Method: Try keyboard navigation on tabs
if (await getSelectedTab() !== 'スライド') {
  console.log('\nTrying keyboard navigation...');
  // Focus the tab
  const tabPos = await frame.evaluate(() => {
    const tabs = document.querySelectorAll('[role="tab"]');
    for (const tab of tabs) {
      if (tab.getAttribute('aria-selected') === 'true') {
        const rect = tab.getBoundingClientRect();
        tab.focus();
        return { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 };
      }
    }
    return null;
  });

  if (tabPos) {
    await slidesPage.mouse.click(tabPos.x, tabPos.y);
    await sleep(200);
    // Try left arrow (to go from 画像 to スライド)
    await slidesPage.keyboard.press('ArrowLeft');
    await sleep(500);
    console.log('After ArrowLeft:', await getSelectedTab());

    // Try Enter to confirm
    await slidesPage.keyboard.press('Enter');
    await sleep(500);
    console.log('After Enter:', await getSelectedTab());
  }
}

// Take screenshot
await slidesPage.screenshot({ path: 'tab_final.png' });
console.log('\nFinal screenshot saved');

browser.disconnect();
