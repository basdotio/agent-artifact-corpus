const fs = require('fs');
const path = require('path');
let chromium;
try {
  ({ chromium } = require('playwright'));
} catch (_) {
  process.stdout.write(`DOUYIN_CAPTURE_JSON=${JSON.stringify({
    ok: false,
    error: 'Playwright package 不存在，请在项目目录运行 npm install',
  })}\n`);
  process.exit(2);
}

const sourceUrl = process.env.DOUYIN_CAPTURE_URL || '';
const audioPath = process.env.DOUYIN_AUDIO_PATH || '';
const downloadAudio = process.env.DOUYIN_DOWNLOAD_AUDIO === '1';

function result(value) {
  process.stdout.write(`DOUYIN_CAPTURE_JSON=${JSON.stringify(value)}\n`);
}

function videoId(text) {
  const match = String(text || '').match(/(?:\/video\/|modal_id=|aweme_id=|item_ids=)(\d{16,22})/)
    || String(text || '').match(/\b(\d{16,22})\b/);
  return match ? match[1] : '';
}

function contentRangeTotal(headers) {
  const match = String(headers['content-range'] || '').match(/\/(\d+)$/);
  return match ? Number(match[1]) : 0;
}

async function downloadByRanges(request, url, destination) {
  fs.mkdirSync(path.dirname(destination), { recursive: true });
  const chunkSize = 4 * 1024 * 1024;
  let start = 0;
  let total = 0;
  const handle = fs.openSync(destination, 'w');
  try {
    while (!total || start < total) {
      const end = total ? Math.min(start + chunkSize - 1, total - 1) : start + chunkSize - 1;
      const response = await request.get(url, {
        headers: { Range: `bytes=${start}-${end}`, Referer: 'https://www.douyin.com/' },
        timeout: 60000,
      });
      if (!response.ok() && response.status() !== 206) {
        throw new Error(`音频请求失败：HTTP ${response.status()}`);
      }
      const headers = response.headers();
      const body = await response.body();
      const range = String(headers['content-range'] || '').match(/bytes\s+(\d+)-(\d+)\/(\d+)/i);
      if (response.status() === 200) {
        fs.writeSync(handle, body, 0, body.length, 0);
        return body.length;
      }
      if (!range) {
        throw new Error('分段音频响应缺少 Content-Range');
      }
      const responseStart = Number(range[1]);
      const responseEnd = Number(range[2]);
      total = Number(range[3]);
      if (responseStart !== start || body.length !== responseEnd - responseStart + 1) {
        throw new Error(`音频分段范围异常：${range[0]} (${body.length} bytes)`);
      }
      fs.writeSync(handle, body, 0, body.length, responseStart);
      start = responseEnd + 1;
    }
  } finally {
    fs.closeSync(handle);
  }
  const size = fs.statSync(destination).size;
  if (total && size !== total) {
    throw new Error(`音频大小不完整：预期 ${total}，实际 ${size}`);
  }
  return size;
}

async function launchBrowser() {
  const attempts = [
    { name: 'Chrome', options: { channel: 'chrome', headless: true } },
    { name: 'Edge', options: { channel: 'msedge', headless: true } },
    { name: 'Playwright Chromium', options: { headless: true } },
  ];
  const errors = [];
  for (const attempt of attempts) {
    try {
      return { browser: await chromium.launch(attempt.options), browser_name: attempt.name };
    } catch (error) {
      errors.push(`${attempt.name}: ${error.message}`);
    }
  }
  throw new Error(`未检测到可用的 Chrome/Edge，且 Playwright Chromium 未安装。请安装 Chrome 或 Edge。${errors.join(' | ')}`);
}

(async () => {
  if (!sourceUrl) {
    result({ ok: false, error: 'DOUYIN_CAPTURE_URL is empty' });
    process.exitCode = 2;
    return;
  }

  let launched;
  try {
    launched = await launchBrowser();
    const browser = launched.browser;
    const context = await browser.newContext({
      locale: 'zh-CN',
      userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36',
      viewport: { width: 1440, height: 1000 },
    });
    const page = await context.newPage();
    const candidates = [];

    page.on('response', async (response) => {
      try {
        const headers = response.headers();
        const type = String(headers['content-type'] || '').toLowerCase();
        const url = response.url();
        if (type.startsWith('audio/') || /media-audio|\.m4a(?:\?|$)|\.mp3(?:\?|$)/i.test(url)) {
          candidates.push({ url, total: contentRangeTotal(headers), type });
        }
      } catch (_) {
        // One failed response inspection must not stop page capture.
      }
    });

    await page.goto(sourceUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(6000);
    await page.locator('video').first().evaluate((element) => {
      element.muted = true;
      return element.play().catch(() => undefined);
    }).catch(() => undefined);
    await page.waitForTimeout(7000);

    const pageData = await page.evaluate(() => {
      const meta = (property) => document.querySelector(`meta[property="${property}"]`)?.content || '';
      const title = (meta('og:title') || document.title || '').replace(/\s*[-_]\s*抖音.*$/i, '').trim();
      return {
        title,
        description: meta('og:description') || document.querySelector('meta[name="description"]')?.content || '',
        final_url: location.href,
      };
    });

    let audioBytes = 0;
    if (downloadAudio) {
      if (!audioPath) throw new Error('DOUYIN_AUDIO_PATH is empty');
      const unique = [...new Map(candidates.map((item) => [item.url, item])).values()]
        .sort((a, b) => b.total - a.total);
      if (!unique.length) throw new Error('没有捕获到音频媒体响应');
      let lastError;
      for (const candidate of unique) {
        try {
          audioBytes = await downloadByRanges(context.request, candidate.url, audioPath);
          if (audioBytes > 0) break;
        } catch (error) {
          lastError = error;
        }
      }
      if (!audioBytes) throw lastError || new Error('音频抓取失败');
    }

    result({
      ok: true,
      ...pageData,
      video_id: videoId(pageData.final_url) || videoId(sourceUrl),
      browser: launched.browser_name,
      media_candidates: candidates.length,
      audio_bytes: audioBytes,
    });
  } catch (error) {
    result({ ok: false, error: String(error && error.message ? error.message : error) });
    process.exitCode = 2;
  } finally {
    if (launched && launched.browser) await launched.browser.close();
  }
})();
