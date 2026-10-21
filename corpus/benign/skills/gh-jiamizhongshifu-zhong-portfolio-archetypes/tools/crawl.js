// 抓取站点：桌面首屏 / 第二屏 / 移动首屏截图 + DOM 层技术栈与风格特征
// 用法: node tools/crawl.js tools [--only=1,2,3] [--concurrency=6]（需先 npm i playwright && npx playwright install chromium）
const fs = require('fs');
const path = require('path');
const os = require('os');
const { chromium } = require('playwright');

const ROOT = path.resolve(process.argv[2]);
const args = Object.fromEntries(process.argv.slice(3).map(a => a.replace(/^--/, '').split('=')));
const CONCURRENCY = Number(args.concurrency || 6);
const ONLY = args.only ? new Set(args.only.split(',').map(Number)) : null;
const RAW = path.join(ROOT, 'data/sites_raw.tsv');
const OUT_DIR = path.join(ROOT, 'data/crawl');
const SHOT_DIR = path.join(ROOT, 'screenshots');
// 默认用 Playwright 自带的 Chromium；可用 CHROME_PATH 指定其他 Chromium / Chrome 可执行文件
const CHROME = process.env.CHROME_PATH || undefined;
const UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36';

fs.mkdirSync(OUT_DIR, { recursive: true });
fs.mkdirSync(SHOT_DIR, { recursive: true });

const sites = fs.readFileSync(RAW, 'utf8').trim().split('\n').map(l => {
  const [id, name, url] = l.split('\t');
  return { id: Number(id), name, url };
}).filter(s => !ONLY || ONLY.has(s.id));

// 记录页面创建了哪些 canvas context（webgl / 2d），在页面脚本之前注入
const INIT = () => {
  window.__ctx = {};
  const orig = HTMLCanvasElement.prototype.getContext;
  HTMLCanvasElement.prototype.getContext = function (type, ...rest) {
    window.__ctx[type] = (window.__ctx[type] || 0) + 1;
    return orig.call(this, type, ...rest);
  };
};

// 在页面里执行的特征提取
function extract() {
  const $ = s => document.querySelector(s);
  const $$ = s => Array.from(document.querySelectorAll(s));
  const scripts = $$('script[src]').map(s => s.src);
  const links = $$('link[href]').map(l => l.href);
  const html = document.documentElement.outerHTML.slice(0, 600000);
  const has = re => re.test(html);
  const srcHas = re => scripts.some(s => re.test(s)) || links.some(s => re.test(s));
  const meta = n => ($(`meta[name="${n}"]`) || $(`meta[property="${n}"]`))?.content || null;
  const generator = meta('generator');

  const tech = {
    framer: !!(window.__framer_importFromPackage || /framer/i.test(generator || '') || srcHas(/framerusercontent|framer\.com\/m\//)),
    webflow: !!(document.documentElement.dataset.wfSite || srcHas(/webflow|website-files\.com/)),
    readymag: has(/readymag/i) && srcHas(/readymag|rmcdn/),
    tilda: srcHas(/tildacdn|tilda\.ws/),
    wordpress: srcHas(/wp-content|wp-includes/),
    squarespace: srcHas(/squarespace|sqspcdn/),
    wix: srcHas(/wixstatic|parastorage/),
    cargo: srcHas(/cargo\.site|cargocollective/),
    shopify: srcHas(/cdn\.shopify/),
    next: !!(window.__NEXT_DATA__ || window.next || srcHas(/\/_next\//)),
    nuxt: !!(window.__NUXT__ || window.$nuxt || srcHas(/\/_nuxt\//)),
    astro: !!($('astro-island') || srcHas(/\/_astro\//)),
    gatsby: !!($('#___gatsby')),
    sveltekit: !!($('[data-sveltekit-preload-data]') || srcHas(/\/_app\/immutable\//) || window.__sveltekit_dev),
    remix: !!window.__remixContext,
    react: !!(window.React || $('[data-reactroot]') ||
      $$('body > div, #root, #__next, #app').some(el => Object.keys(el).some(k => k.startsWith('__react')))),
    vue: !!(window.Vue || $$('*').slice(0, 300).some(el => el.__vue_app__ || el.__vue__)),
    svelte: $$('[class*="svelte-"]').length > 0,
    gsap: !!(window.gsap || window.TweenMax || srcHas(/gsap|greensock/)),
    scrollTrigger: !!(window.ScrollTrigger || srcHas(/ScrollTrigger/i)),
    three: !!(window.THREE || window.__THREE__ || srcHas(/three(\.module)?(\.min)?\.js/)),
    lenis: !!(window.Lenis || window.lenis || document.documentElement.classList.contains('lenis') || srcHas(/lenis/)),
    locomotive: !!($('[data-scroll-container]') || document.documentElement.classList.contains('has-scroll-smooth')),
    barba: !!($('[data-barba]') || window.barba),
    swup: !!($('#swup') || window.swup),
    lottie: !!($('lottie-player, dotlottie-player') || window.lottie || window.bodymovin || srcHas(/lottie/)),
    spline: !!($('spline-viewer') || has(/prod\.spline\.design|splinetool/)),
    rive: !!(window.rive || srcHas(/rive/) || has(/\.riv["']/)),
    pixi: !!(window.PIXI || srcHas(/pixi/)),
    ogl: srcHas(/\/ogl/),
    p5: !!(window.p5),
    matter: !!(window.Matter),
    tailwind: $$('[class]').slice(0, 800).filter(el =>
      /(^|\s)(flex|grid|px-\d|py-\d|text-(xs|sm|lg|xl)|rounded-|bg-\[|w-\[|md:|lg:)/.test(el.className?.baseVal ?? el.className)).length > 30,
    vercel: srcHas(/_vercel/),
  };

  // 可见文本元素：找首屏最大字号的文字
  const vw = innerWidth, vh = innerHeight;
  const textEls = $$('h1,h2,h3,h4,p,a,span,div,li,button').filter(el => {
    const t = Array.from(el.childNodes).filter(n => n.nodeType === 3).map(n => n.textContent).join('').trim();
    if (!t) return false;
    const r = el.getBoundingClientRect();
    if (!(r.width > 2 && r.height > 2 && r.top < vh && r.bottom > 0 && r.left < vw && r.right > 0)) return false;
    const cs = getComputedStyle(el);
    return cs.visibility !== 'hidden' && parseFloat(cs.opacity) > 0.05 && !/rect\(0|inset\(50%/.test(cs.clip + cs.clipPath);
  });
  const fontStats = {};
  let heroText = null, heroSize = 0;
  for (const el of textEls) {
    const cs = getComputedStyle(el);
    const fam = cs.fontFamily.split(',')[0].replace(/["']/g, '').trim();
    const size = parseFloat(cs.fontSize);
    const len = el.textContent.trim().length;
    fontStats[fam] = (fontStats[fam] || 0) + len;
    if (size > heroSize && len > 1) {
      heroSize = size;
      heroText = { text: el.textContent.trim().replace(/\s+/g, ' ').slice(0, 160), fontFamily: fam, fontSize: size,
        fontWeight: cs.fontWeight, letterSpacing: cs.letterSpacing, textTransform: cs.textTransform,
        lineHeight: cs.lineHeight, color: cs.color };
    }
  }
  const fonts = Object.entries(fontStats).sort((a, b) => b[1] - a[1]).slice(0, 5).map(([f]) => f);
  const loadedFonts = [...new Set(Array.from(document.fonts || []).filter(f => f.status === 'loaded').map(f => f.family.replace(/["']/g, '')))].slice(0, 12);

  const bodyCs = getComputedStyle(document.body);
  const bg = [document.body, document.documentElement].map(el => getComputedStyle(el).backgroundColor)
    .find(c => c && c !== 'rgba(0, 0, 0, 0)' && c !== 'transparent') || null;

  const all = $$('body *');
  let sticky = 0, fixed = 0, blend = 0, backdrop = 0, customCursor = bodyCs.cursor === 'none';
  for (const el of all.slice(0, 4000)) {
    const cs = getComputedStyle(el);
    if (cs.position === 'sticky') sticky++;
    if (cs.position === 'fixed') fixed++;
    if (cs.mixBlendMode !== 'normal') blend++;
    if (cs.backdropFilter && cs.backdropFilter !== 'none') backdrop++;
    if (cs.cursor === 'none') customCursor = true;
  }
  const cursorEl = $$('[class*="cursor" i], [id*="cursor" i]').filter(el => {
    const cs = getComputedStyle(el);
    return cs.position === 'fixed' || cs.position === 'absolute';
  }).length > 0;

  const hrefs = $$('a[href]').map(a => a.href);
  const social = {};
  for (const [k, re] of Object.entries({
    twitter: /(twitter|x)\.com\//, linkedin: /linkedin\.com/, dribbble: /dribbble\.com/, behance: /behance\.net/,
    instagram: /instagram\.com/, github: /github\.com/, readcv: /read\.cv|posts\.cv/, youtube: /youtube\.com/,
    medium: /medium\.com|substack\.com/, awwwards: /awwwards\.com/, email: /^mailto:/,
  })) social[k] = hrefs.some(h => re.test(h));

  const canvases = $$('canvas').map(c => { const r = c.getBoundingClientRect(); return Math.round(r.width * r.height); });
  const bigCanvas = canvases.some(a => a > vw * vh * 0.25);

  return {
    finalUrl: location.href,
    title: document.title,
    description: meta('description') || meta('og:description'),
    ogImage: meta('og:image'),
    generator,
    lang: document.documentElement.lang || null,
    tech,
    canvasContexts: window.__ctx || {},
    canvas: { count: canvases.length, fullscreen: bigCanvas },
    typography: { fonts, loadedFonts, hero: heroText, bodyFont: bodyCs.fontFamily.split(',')[0].replace(/["']/g, '').trim(), bodySize: bodyCs.fontSize },
    color: { background: bg, text: bodyCs.color },
    layout: {
      pageHeightScreens: +(document.documentElement.scrollHeight / vh).toFixed(1),
      sections: $$('section').length,
      images: $$('img').length, videos: $$('video').length, svgs: $$('svg').length,
      iframes: $$('iframe').map(f => f.src).filter(Boolean).slice(0, 5),
      links: hrefs.length, nav: !!$('nav, header'),
      sticky, fixed, mixBlend: blend, backdropBlur: backdrop,
      customCursor: customCursor || cursorEl,
      cssAnimations: (document.getAnimations?.() || []).length,
      wordCount: (document.body.innerText || '').split(/\s+/).filter(Boolean).length,
    },
    social,
  };
}

// 首屏是否还在加载：近乎纯色（JPEG 很小）或可见文字像 "93%" / loading
async function settle(page, maxMs = 20000, blankBytes = 10000) {
  const start = Date.now();
  let preloader = false, prev = 0;
  while (Date.now() - start < maxMs) {
    const buf = await page.screenshot({ type: 'jpeg', quality: 40 }).catch(() => null);
    const size = buf ? buf.length : 0;
    const loaderText = await page.evaluate(() => {
      const t = (document.body?.innerText || '').trim();
      return t.length < 400 && /(^|\s)\d{1,3}\s?%|loading|chargement/i.test(t);
    }).catch(() => false);
    const blank = size < blankBytes;
    const stable = prev && Math.abs(size - prev) / prev < 0.04;
    if (blank || loaderText) preloader = true;
    if (!blank && !loaderText && stable) break;
    prev = size;
    await page.waitForTimeout(1500);
  }
  return { preloader, settleMs: Date.now() - start };
}

// "Click to enter / Enter with sound" 进站门：存门页截图，优先点静音入口，再等站内内容
async function passGate(page, gateShot) {
  const target = await page.evaluate(() => {
    const vw = innerWidth, vh = innerHeight;
    const re = /\benter\b|click to (enter|start)|dive into/i;
    const cands = Array.from(document.querySelectorAll('button, a, [role=button], div, span, p'))
      .filter(el => {
        const txt = (el.innerText || '').trim();
        if (!txt || txt.length > 60 || !re.test(txt)) return false;
        const r = el.getBoundingClientRect(), cs = getComputedStyle(el);
        return r.width > 0 && r.height > 0 && r.top > vh * 0.1 && r.bottom < vh && r.left > vw * 0.1 && r.right < vw * 0.9
          && parseFloat(cs.opacity) > 0.05 && cs.visibility !== 'hidden';
      });
    cands.sort((a, b) => a.innerText.length - b.innerText.length);
    const pick = cands.find(el => /mute|without (audio|sound)|no sound/i.test(el.innerText)) || cands[cands.length - 1];
    if (!pick) {
      const t = document.body?.innerText || '';
      return /click anywhere|enter site/i.test(t) ? { x: vw / 2, y: vh / 2, label: (t.match(/click anywhere[^\n]*|enter site/i) || [''])[0].slice(0, 60) } : null;
    }
    const r = pick.getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2, label: pick.innerText.trim().slice(0, 60) };
  }).catch(() => null);
  if (!target) return null;
  await page.screenshot({ path: gateShot, type: 'jpeg', quality: 72, timeout: 60000 });
  await page.mouse.click(target.x, target.y);
  await page.waitForTimeout(5000);
  await settle(page, 15000);
  return target.label;
}

async function crawlOne(browser, site) {
  const id = String(site.id).padStart(3, '0');
  const outFile = path.join(OUT_DIR, `${id}.json`);
  const rec = { id: site.id, name: site.name, url: site.url, crawledAt: new Date().toISOString() };
  const t0 = Date.now();
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, userAgent: UA, locale: 'en-US', deviceScaleFactor: 1 });
  await ctx.addInitScript(INIT);
  const page = await ctx.newPage();
  const consoleErrors = [];
  page.on('pageerror', e => consoleErrors.push(String(e.message).slice(0, 200)));
  try {
    const resp = await page.goto(site.url, { waitUntil: 'domcontentloaded', timeout: 45000 });
    rec.status = resp?.status() ?? null;
    await page.waitForLoadState('load', { timeout: 20000 }).catch(() => {});
    await page.waitForTimeout(3000);
    Object.assign(rec, await settle(page)); // 等 preloader / 入场动画结束
    rec.enterGate = await passGate(page, path.join(SHOT_DIR, `${id}-gate.jpg`));
    rec.loadMs = Date.now() - t0;
    Object.assign(rec, await page.evaluate(extract));
    await page.screenshot({ path: path.join(SHOT_DIR, `${id}-desktop.jpg`), type: 'jpeg', quality: 72, timeout: 60000 });
    await page.mouse.wheel(0, 900);
    await page.waitForTimeout(1800);
    await page.screenshot({ path: path.join(SHOT_DIR, `${id}-desktop-2.jpg`), type: 'jpeg', quality: 72, timeout: 60000 });
    rec.ok = true;
  } catch (e) {
    rec.ok = false;
    rec.error = String(e.message).split('\n')[0].slice(0, 300);
    await page.screenshot({ path: path.join(SHOT_DIR, `${id}-desktop.jpg`), type: 'jpeg', quality: 72 }).catch(() => {});
  }
  rec.pageErrors = consoleErrors.slice(0, 5);
  await ctx.close();

  // 移动首屏
  const mctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true,
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1' });
  const mpage = await mctx.newPage();
  try {
    await mpage.goto(site.url, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await mpage.waitForLoadState('load', { timeout: 15000 }).catch(() => {});
    await mpage.waitForTimeout(2500);
    await settle(mpage, 15000, 5000);
    await mpage.screenshot({ path: path.join(SHOT_DIR, `${id}-mobile.jpg`), type: 'jpeg', quality: 65, scale: 'css' });
    rec.mobileOk = true;
  } catch (e) {
    rec.mobileOk = false;
  }
  await mctx.close();
  fs.writeFileSync(outFile, JSON.stringify(rec, null, 2));
  return rec;
}

(async () => {
  const browser = await chromium.launch({ executablePath: CHROME, headless: true,
    args: ['--enable-webgl', '--ignore-gpu-blocklist', '--use-angle=metal', '--autoplay-policy=no-user-gesture-required'] });
  const queue = [...sites];
  let done = 0;
  await Promise.all(Array.from({ length: CONCURRENCY }, async () => {
    while (queue.length) {
      const s = queue.shift();
      const r = await crawlOne(browser, s).catch(e => ({ id: s.id, ok: false, error: e.message }));
      done++;
      console.log(`[${done}/${sites.length}] #${s.id} ${r.ok ? 'ok' : 'FAIL ' + r.error} ${r.loadMs || ''}`);
    }
  }));
  await browser.close();
})();
