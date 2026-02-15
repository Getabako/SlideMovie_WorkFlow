import puppeteer from 'puppeteer-core';

const browser = await puppeteer.connect({ browserURL: 'http://127.0.0.1:18800' });
const pages = await browser.pages();
const slidesPage = pages.find(p => p.url().includes('presentation'));
if (slidesPage == null) { console.log('Page not found'); process.exit(1); }

const frame = slidesPage.frames().find(f => f.url().includes('slide=')) || slidesPage.mainFrame();
console.log('Frame URL:', frame.url().substring(0, 120));

const state = await frame.evaluate(() => {
  const thumbnails = document.querySelectorAll('g.punch-filmstrip-thumbnail');
  const textareas = document.querySelectorAll('textarea');
  const aside = document.querySelector('aside[aria-label="画像作成サポート"]');
  const panelBtn = document.querySelector('[aria-label="画像作成サポート"][role="button"]');
  let panelBtnInfo = null;
  if (panelBtn) {
    const rect = panelBtn.getBoundingClientRect();
    panelBtnInfo = { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2, w: rect.width, h: rect.height };
  }
  return {
    thumbnails: thumbnails.length,
    textareas: textareas.length,
    hasPanel: (aside != null),
    panelBtn: panelBtnInfo,
  };
});
console.log('State:', JSON.stringify(state, null, 2));

if (state.panelBtn && state.panelBtn.w > 0) {
  console.log('Clicking panel button...');
  await slidesPage.mouse.click(state.panelBtn.x, state.panelBtn.y);
  await new Promise(r => setTimeout(r, 5000));

  const afterClick = await frame.evaluate(() => {
    const textareas = document.querySelectorAll('textarea');
    const visibleTAs = [];
    for (const ta of textareas) {
      if (ta.offsetHeight > 0) visibleTAs.push({ w: ta.offsetWidth, h: ta.offsetHeight });
    }
    const aside = document.querySelector('aside[aria-label="画像作成サポート"]');
    const allAsides = document.querySelectorAll('aside');
    const labels = Array.from(allAsides).map(a => a.getAttribute('aria-label'));
    const tabs = document.querySelectorAll('[role="tab"]');
    const tabLabels = Array.from(tabs).map(t => (t.textContent || '').trim());
    let panelContent = '';
    if (aside) {
      panelContent = aside.textContent.substring(0, 300);
    }
    return { visibleTAs: visibleTAs.length, hasPanel: (aside != null), asideLabels: labels, tabLabels, panelContent };
  });
  console.log('After click:', JSON.stringify(afterClick, null, 2));
} else {
  console.log('Panel button not found or not visible');
}

browser.disconnect();
