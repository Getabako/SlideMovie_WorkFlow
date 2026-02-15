import puppeteer from 'puppeteer-core';

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

const browser = await puppeteer.connect({ browserURL: 'http://127.0.0.1:18800' });
const pages = await browser.pages();
const slidesPage = pages.find(p => p.url().includes('presentation'));
if (slidesPage == null) { console.log('Page not found'); process.exit(1); }

const frame = slidesPage.frames().find(f => f.url().includes('slide=')) || slidesPage.mainFrame();

// Wait and check panel
for (let i = 0; i < 5; i++) {
  console.log(`\n--- Check ${i+1} ---`);
  const info = await frame.evaluate(() => {
    const aside = document.querySelector('aside[aria-label="画像作成サポート"]');
    if (aside == null) return { found: false };

    const html = aside.innerHTML.substring(0, 1000);
    const childCount = aside.children.length;
    const shadowRoot = aside.shadowRoot;

    // Check for iframes inside aside
    const iframes = aside.querySelectorAll('iframe');
    const iframeList = [];
    for (const iframe of iframes) {
      iframeList.push({ src: iframe.src || '', w: iframe.offsetWidth, h: iframe.offsetHeight });
    }

    // Walk all descendants
    const allElements = aside.querySelectorAll('*');

    return {
      found: true,
      childCount,
      totalDescendants: allElements.length,
      hasShadow: (shadowRoot != null),
      html: html,
      iframes: iframeList,
    };
  });
  console.log(JSON.stringify(info, null, 2));

  if (i < 4) await sleep(3000);
}

// Also check for the panel in other frames
const allFrames = slidesPage.frames();
console.log('\n--- Checking all frames for panel ---');
for (let i = 0; i < allFrames.length; i++) {
  try {
    const hasPanel = await allFrames[i].evaluate(() => {
      const aside = document.querySelector('aside');
      const textareas = document.querySelectorAll('textarea');
      const visibleTAs = Array.from(textareas).filter(t => t.offsetHeight > 0);
      return {
        hasAside: (aside != null),
        asideLabel: aside ? aside.getAttribute('aria-label') : null,
        visibleTextareas: visibleTAs.length,
        totalTextareas: textareas.length,
      };
    });
    if (hasPanel.hasAside || hasPanel.totalTextareas > 0) {
      console.log(`Frame ${i} (${allFrames[i].url().substring(0, 80)}):`, JSON.stringify(hasPanel));
    }
  } catch (e) {
    // skip
  }
}

browser.disconnect();
