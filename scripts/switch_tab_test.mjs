import puppeteer from 'puppeteer-core';

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

const browser = await puppeteer.connect({ browserURL: 'http://127.0.0.1:18800' });
const pages = await browser.pages();
const slidesPage = pages.find(p => p.url().includes('presentation'));
if (slidesPage == null) { console.log('Page not found'); process.exit(1); }

const frame = slidesPage.frames().find(f => f.url().includes('slide=')) || slidesPage.mainFrame();

// Find and click "スライド" tab
const tabBox = await frame.evaluate(() => {
  const tabs = document.querySelectorAll('[role="tab"]');
  for (const tab of tabs) {
    const text = (tab.textContent || '').trim();
    if (text.includes('スライド') && tab.getAttribute('aria-selected') !== 'true') {
      const rect = tab.getBoundingClientRect();
      return { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2, text };
    }
  }
  return null;
});

if (tabBox) {
  console.log('Clicking tab:', tabBox.text, 'at', tabBox.x, tabBox.y);
  await slidesPage.mouse.click(tabBox.x, tabBox.y);
  await sleep(2000);

  // Take screenshot
  await slidesPage.screenshot({ path: 'after_tab_switch.png' });
  console.log('Screenshot saved');

  // Verify tab state
  const tabState = await frame.evaluate(() => {
    const tabs = document.querySelectorAll('[role="tab"]');
    const result = [];
    for (const tab of tabs) {
      const text = (tab.textContent || '').trim();
      const rect = tab.getBoundingClientRect();
      if (rect.x > 380 && rect.height > 0) {
        result.push({ text, selected: tab.getAttribute('aria-selected') });
      }
    }
    return result;
  });
  console.log('Tab states:', JSON.stringify(tabState));
} else {
  console.log('スライド tab already selected or not found');
}

browser.disconnect();
