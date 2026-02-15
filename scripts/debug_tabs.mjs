import puppeteer from 'puppeteer-core';

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

const browser = await puppeteer.connect({ browserURL: 'http://127.0.0.1:18800' });
const pages = await browser.pages();
const slidesPage = pages.find(p => p.url().includes('presentation'));
if (slidesPage == null) { console.log('Page not found'); process.exit(1); }

const frame = slidesPage.frames().find(f => f.url().includes('slide=')) || slidesPage.mainFrame();

// Search for elements with text "スライド", "画像", "インフォグラ"
const tabInfo = await frame.evaluate(() => {
  // Method 1: role="tab"
  const roleTabs = document.querySelectorAll('[role="tab"]');
  const roleTabList = [];
  for (const tab of roleTabs) {
    const rect = tab.getBoundingClientRect();
    const text = (tab.textContent || '').trim();
    if (rect.x > 380 && rect.height > 0) {
      roleTabList.push({
        text, selected: tab.getAttribute('aria-selected'),
        x: Math.round(rect.x), y: Math.round(rect.y),
        w: Math.round(rect.width), h: Math.round(rect.height),
        role: tab.getAttribute('role'),
        tag: tab.tagName,
      });
    }
  }

  // Method 2: Search by text content for tab-like elements
  const allElements = document.querySelectorAll('*');
  const tabTexts = ['スライド', '画像', 'インフォグラ'];
  const foundTabs = [];
  for (const el of allElements) {
    const text = (el.textContent || '').trim();
    const directText = Array.from(el.childNodes).filter(n => n.nodeType === 3).map(n => n.textContent.trim()).join('');
    for (const tabText of tabTexts) {
      if (directText === tabText || (text === tabText && el.children.length <= 2)) {
        const rect = el.getBoundingClientRect();
        if (rect.x > 380 && rect.height > 0 && rect.width > 0 && rect.width < 200) {
          foundTabs.push({
            matchedText: tabText,
            text: text.substring(0, 30),
            directText,
            tag: el.tagName,
            role: el.getAttribute('role') || '',
            ariaSelected: el.getAttribute('aria-selected') || '',
            classes: (el.className || '').toString().substring(0, 100),
            x: Math.round(rect.x), y: Math.round(rect.y),
            w: Math.round(rect.width), h: Math.round(rect.height),
            clickable: typeof el.click === 'function',
          });
        }
      }
    }
  }

  return { roleTabs: roleTabList, foundTabs };
});

console.log('Role tabs:', JSON.stringify(tabInfo.roleTabs, null, 2));
console.log('\nFound tab-like elements:', JSON.stringify(tabInfo.foundTabs, null, 2));

browser.disconnect();
