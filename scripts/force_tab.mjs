import puppeteer from 'puppeteer-core';

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

const browser = await puppeteer.connect({ browserURL: 'http://127.0.0.1:18800' });
const pages = await browser.pages();
const slidesPage = pages.find(p => p.url().includes('presentation'));
if (slidesPage == null) { console.log('Page not found'); process.exit(1); }

const frame = slidesPage.frames().find(f => f.url().includes('slide=')) || slidesPage.mainFrame();

// Method 1: Try multiple click approaches
const tabInfo = await frame.evaluate(() => {
  const tabs = document.querySelectorAll('[role="tab"]');
  for (const tab of tabs) {
    const text = (tab.textContent || '').trim();
    if (text === 'スライド') {
      const rect = tab.getBoundingClientRect();
      return { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2, w: rect.width, h: rect.height, selected: tab.getAttribute('aria-selected') };
    }
  }
  return null;
});
console.log('Tab info:', JSON.stringify(tabInfo));

// Method 1: Try various synthetic events
console.log('\nMethod 1: DOM events...');
const result1 = await frame.evaluate(() => {
  const tabs = document.querySelectorAll('[role="tab"]');
  for (const tab of tabs) {
    const text = (tab.textContent || '').trim();
    if (text === 'スライド') {
      // Try various events
      tab.click();
      tab.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
      tab.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
      tab.dispatchEvent(new MouseEvent('click', { bubbles: true }));
      tab.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true }));
      tab.dispatchEvent(new PointerEvent('pointerup', { bubbles: true }));
      return 'events dispatched';
    }
  }
  return 'tab not found';
});
console.log(result1);
await sleep(1000);

// Check result
let selectedTab = await frame.evaluate(() => {
  const tabs = document.querySelectorAll('[role="tab"]');
  for (const tab of tabs) {
    if (tab.getAttribute('aria-selected') === 'true') return (tab.textContent || '').trim();
  }
  return 'none';
});
console.log('Selected after Method 1:', selectedTab);

if (selectedTab !== 'スライド') {
  // Method 2: Click on the label child element
  console.log('\nMethod 2: Click on label child...');
  const labelInfo = await frame.evaluate(() => {
    const labels = document.querySelectorAll('.appsDocsAiGenerativeaiImageCssConversationalSidebarTabLabel');
    for (const label of labels) {
      if ((label.textContent || '').trim() === 'スライド') {
        const rect = label.getBoundingClientRect();
        return { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 };
      }
    }
    return null;
  });
  if (labelInfo) {
    console.log('Label at:', labelInfo);
    await slidesPage.mouse.click(labelInfo.x, labelInfo.y);
    await sleep(1000);
    selectedTab = await frame.evaluate(() => {
      const tabs = document.querySelectorAll('[role="tab"]');
      for (const tab of tabs) {
        if (tab.getAttribute('aria-selected') === 'true') return (tab.textContent || '').trim();
      }
      return 'none';
    });
    console.log('Selected after Method 2:', selectedTab);
  }
}

if (selectedTab !== 'スライド') {
  // Method 3: Focus the tab first, then click with mousedown/mouseup
  console.log('\nMethod 3: Focus then mouse events...');
  if (tabInfo) {
    await slidesPage.mouse.move(tabInfo.x, tabInfo.y);
    await sleep(100);
    await slidesPage.mouse.down();
    await sleep(100);
    await slidesPage.mouse.up();
    await sleep(1000);
    selectedTab = await frame.evaluate(() => {
      const tabs = document.querySelectorAll('[role="tab"]');
      for (const tab of tabs) {
        if (tab.getAttribute('aria-selected') === 'true') return (tab.textContent || '').trim();
      }
      return 'none';
    });
    console.log('Selected after Method 3:', selectedTab);
  }
}

if (selectedTab !== 'スライド') {
  // Method 4: Check if there's an element above the tab intercepting clicks
  console.log('\nMethod 4: Check what element is at the tab position...');
  const elementAtPoint = await frame.evaluate((x, y) => {
    const el = document.elementFromPoint(x, y);
    if (el == null) return { found: false };
    return {
      found: true,
      tag: el.tagName,
      role: el.getAttribute('role') || '',
      classes: (el.className || '').toString().substring(0, 150),
      text: (el.textContent || '').trim().substring(0, 50),
      ariaSelected: el.getAttribute('aria-selected') || '',
    };
  }, tabInfo.x, tabInfo.y);
  console.log('Element at tab position:', JSON.stringify(elementAtPoint, null, 2));
}

// Take final screenshot
await slidesPage.screenshot({ path: 'after_force_tab.png' });
console.log('\nFinal screenshot saved');

browser.disconnect();
