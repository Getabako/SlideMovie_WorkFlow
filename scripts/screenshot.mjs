import puppeteer from 'puppeteer-core';

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

const browser = await puppeteer.connect({ browserURL: 'http://127.0.0.1:18800' });
const pages = await browser.pages();
const slidesPage = pages.find(p => p.url().includes('presentation'));
if (slidesPage == null) { console.log('Page not found'); process.exit(1); }

await slidesPage.screenshot({ path: 'debug_screenshot.png', fullPage: false });
console.log('Screenshot saved as debug_screenshot.png');

browser.disconnect();
