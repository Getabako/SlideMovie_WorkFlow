import puppeteer from 'puppeteer-core';

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

const browser = await puppeteer.connect({ browserURL: 'http://127.0.0.1:18800' });
const pages = await browser.pages();
const slidesPage = pages.find(p => p.url().includes('presentation'));
if (slidesPage == null) { console.log('Page not found'); process.exit(1); }

const frame = slidesPage.frames().find(f => f.url().includes('slide=')) || slidesPage.mainFrame();

// Search for all input-like elements
const results = await frame.evaluate(() => {
  // 1. All textareas
  const textareas = document.querySelectorAll('textarea');
  const taList = [];
  for (const ta of textareas) {
    const rect = ta.getBoundingClientRect();
    taList.push({ tag: 'textarea', visible: rect.height > 0, w: rect.width, h: rect.height, placeholder: ta.placeholder || '' });
  }

  // 2. All contenteditable elements
  const editables = document.querySelectorAll('[contenteditable="true"]');
  const edList = [];
  for (const el of editables) {
    const rect = el.getBoundingClientRect();
    if (rect.height > 5 && rect.width > 5) {
      edList.push({
        tag: el.tagName,
        role: el.getAttribute('role') || '',
        ariaLabel: el.getAttribute('aria-label') || '',
        w: rect.width, h: rect.height,
        x: rect.x, y: rect.y,
        text: (el.textContent || '').substring(0, 100),
        classes: el.className.substring(0, 100),
      });
    }
  }

  // 3. All elements with "アイデア" or placeholder text
  const allElements = document.querySelectorAll('*');
  const ideaElements = [];
  for (const el of allElements) {
    const text = (el.textContent || '').trim();
    const placeholder = el.getAttribute('placeholder') || '';
    const ariaLabel = el.getAttribute('aria-label') || '';
    if (text.includes('アイデアを記述') || placeholder.includes('アイデア') || ariaLabel.includes('アイデア')) {
      const rect = el.getBoundingClientRect();
      if (rect.height > 0 && rect.width > 0) {
        ideaElements.push({
          tag: el.tagName,
          role: el.getAttribute('role') || '',
          contentEditable: el.contentEditable,
          w: rect.width, h: rect.height,
          x: rect.x, y: rect.y,
          text: text.substring(0, 100),
          children: el.children.length,
        });
      }
    }
  }

  // 4. Elements near the bottom-right area of the panel (around 400-700 x, 400-550 y based on screenshot)
  const inputArea = [];
  for (const el of allElements) {
    const rect = el.getBoundingClientRect();
    if (rect.x > 380 && rect.x < 720 && rect.y > 300 && rect.y < 560 && rect.height > 20 && rect.height < 200) {
      const tag = el.tagName;
      if (tag === 'TEXTAREA' || tag === 'INPUT' || el.contentEditable === 'true' || el.getAttribute('role') === 'textbox') {
        inputArea.push({
          tag, role: el.getAttribute('role') || '',
          contentEditable: el.contentEditable,
          ariaLabel: el.getAttribute('aria-label') || '',
          x: rect.x, y: rect.y, w: rect.width, h: rect.height,
          text: (el.textContent || '').substring(0, 80),
        });
      }
    }
  }

  return { textareas: taList, editables: edList, ideaElements: ideaElements.slice(0, 10), inputArea };
});

console.log('Textareas:', JSON.stringify(results.textareas, null, 2));
console.log('\nContenteditable:', JSON.stringify(results.editables, null, 2));
console.log('\nIdea elements:', JSON.stringify(results.ideaElements, null, 2));
console.log('\nInput area elements:', JSON.stringify(results.inputArea, null, 2));

browser.disconnect();
