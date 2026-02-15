#!/usr/bin/env node
/**
 * 画像作成サポートのダイアログ状態をデバッグするスクリプト
 *
 * OpenClawブラウザに接続して、Google Slidesの画像作成サポートの
 * UI状態を詳細に調査する。
 *
 * 使い方:
 *   node scripts/debug_dialog.mjs <URL> [--slide N]
 */

import puppeteer from 'puppeteer-core';

const args = process.argv.slice(2);
let url = '', slideNum = 1, cdpPort = 18800;
for (let i = 0; i < args.length; i++) {
  if (args[i] === '--slide') slideNum = parseInt(args[++i]);
  else if (args[i] === '--cdp-port') cdpPort = parseInt(args[++i]);
  else if (!args[i].startsWith('--')) url = args[i];
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function main() {
  console.log('=== ダイアログデバッグ ===');

  const browser = await puppeteer.connect({
    browserURL: `http://127.0.0.1:${cdpPort}`,
    defaultViewport: null,
    protocolTimeout: 120000,
  });

  const pages = await browser.pages();
  let page = pages.find(p => p.url().includes('docs.google.com/presentation'));
  if (!page) {
    console.error('Google Slidesのタブが見つかりません');
    process.exit(1);
  }

  // フレーム情報
  console.log(`\nフレーム数: ${page.frames().length}`);
  for (const f of page.frames()) {
    console.log(`  ${f.url().substring(0, 80)}`);
  }

  const frame = page.frames().find(f => f.url().includes('slide=')) || page.mainFrame();
  console.log(`\n使用フレーム: ${frame.url().substring(0, 80)}`);

  // 画像作成サポートパネルの状態
  console.log('\n--- パネル状態 ---');
  const panelInfo = await frame.evaluate(() => {
    const aside = document.querySelector('aside[aria-label="画像作成サポート"]');
    if (!aside) return { found: false };
    const rect = aside.getBoundingClientRect();

    // textarea
    const textareas = aside.querySelectorAll('textarea');
    const taList = Array.from(textareas).map(ta => ({
      visible: ta.offsetHeight > 0,
      size: `${ta.offsetWidth}x${ta.offsetHeight}`,
    }));

    // buttons
    const buttons = aside.querySelectorAll('button, [role="button"]');
    const btnList = Array.from(buttons).map(b => ({
      label: b.getAttribute('aria-label') || b.textContent?.trim().substring(0, 30),
      disabled: b.disabled,
      visible: b.getBoundingClientRect().height > 0,
    }));

    // tabs
    const tabs = aside.querySelectorAll('[role="tab"]');
    const tabList = Array.from(tabs).map(t => ({
      text: t.textContent?.trim(),
      selected: t.getAttribute('aria-selected'),
    }));

    // menuitems (thumbnails)
    const menuItems = aside.querySelectorAll('[role="menuitem"]');
    const miList = Array.from(menuItems).map(m => ({
      text: m.textContent?.trim().substring(0, 30),
      visible: m.getBoundingClientRect().height > 0,
    }));

    return {
      found: true,
      size: `${Math.round(rect.width)}x${Math.round(rect.height)}`,
      textareas: taList,
      buttons: btnList.slice(0, 10),
      tabs: tabList,
      menuItems: miList,
    };
  });
  console.log(JSON.stringify(panelInfo, null, 2));

  // ダイアログ状態（全フレームで検索）
  console.log('\n--- ダイアログ状態（全フレーム） ---');
  for (const f of page.frames()) {
    const dialogs = await f.evaluate(() => {
      const ds = document.querySelectorAll('[role="dialog"]');
      if (ds.length === 0) return null;
      return Array.from(ds).map(d => {
        const rect = d.getBoundingClientRect();
        const style = window.getComputedStyle(d);
        const btns = d.querySelectorAll('button, [role="button"]');
        return {
          visible: rect.height > 0,
          size: `${Math.round(rect.width)}x${Math.round(rect.height)}`,
          display: style.display,
          visibility: style.visibility,
          opacity: style.opacity,
          overflow: style.overflow,
          position: style.position,
          zIndex: style.zIndex,
          text: d.textContent?.substring(0, 100),
          buttons: Array.from(btns).map(b => ({
            label: b.getAttribute('aria-label') || b.textContent?.trim().substring(0, 30),
            rect: (() => { const r = b.getBoundingClientRect(); return `${Math.round(r.x)},${Math.round(r.y)} ${Math.round(r.width)}x${Math.round(r.height)}`; })(),
          })),
        };
      });
    });
    if (dialogs) {
      console.log(`フレーム: ${f.url().substring(0, 60)}`);
      console.log(JSON.stringify(dialogs, null, 2));
    }
  }

  // page.evaluate でも確認
  console.log('\n--- page.evaluate でダイアログ確認 ---');
  const pageDialogs = await page.evaluate(() => {
    const ds = document.querySelectorAll('[role="dialog"]');
    return Array.from(ds).map(d => {
      const rect = d.getBoundingClientRect();
      return {
        visible: rect.height > 0,
        size: `${Math.round(rect.width)}x${Math.round(rect.height)}`,
        text: d.textContent?.substring(0, 80),
      };
    });
  });
  console.log(JSON.stringify(pageDialogs, null, 2));

  browser.disconnect();
}

main().catch(err => { console.error(err); process.exit(1); });
