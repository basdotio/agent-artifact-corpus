#!/usr/bin/env node
/**
 * 搜索角色图片 - 使用 Tavily API 的 include_images 参数
 * 直接返回图片 URL 列表
 */

function usage() {
  console.error(`Usage: search-images-tavily.mjs "角色名" [options]`);
  console.error(`Options:`);
  console.error(`  -n <count>      最大图片数 (default: 10, max: 20)`);
  console.error(`  --json          输出 JSON 格式`);
  console.error(`  --download      直接下载到 assets/photos/`);
  process.exit(2);
}

const args = process.argv.slice(2);
if (args.length === 0 || args[0] === "-h" || args[0] === "--help") usage();

const query = args[0];
let maxImages = 10;
let jsonOutput = false;
let shouldDownload = false;

for (let i = 1; i < args.length; i++) {
  const a = args[i];
  if (a === "-n") {
    maxImages = Number.parseInt(args[i + 1] ?? "10", 10);
    i++;
    continue;
  }
  if (a === "--json") {
    jsonOutput = true;
    continue;
  }
  if (a === "--download") {
    shouldDownload = true;
    continue;
  }
}

const [REDACTED_SECRET] ?? "").trim();
if (!apiKey) {
  console.error("❌ Missing TAVILY_API_KEY. Get one at https://tavily.com");
  process.exit(1);
}

// 中国可访问的图片域名（白名单）
const accessibleDomains = [
  // 大陆网站
  'sinaimg.cn', 'weibo.com', 'weibo.cn',
  'bcebos.com', 'baidu.com', 'bdimg.com', 'bstatic.com',
  'qq.com', 'qpic.cn', 'qlogo.cn',
  'douyin.com', 'douyinpic.com',
  'xiaohongshu.com', 'xhscdn.com',
  'hdslb.com', 'bilibili.com',
  'zhihu.com', 'zhimg.com',
  'sohu.com', 'sina.com.cn',
  'toutiao.com', 'bytedance.com',
  'selfimg.com.cn', 'voguecms',
  'xingxiaoculture.com',
  'myloveidol.com',
  'itc.cn',      // 搜狐图片
  // 韩国/日本
  'kpoppann.com',
  'ntruss.com',  // 韩国 CDN
  // 台湾媒体（通常可访问）
  'worldjournal.com', 'udn.com.tw',
  'tvbs.com.tw',
  'ltn.com.tw',  // 自由时报
  'chinatimes.com',
  // 维基百科
  'wikimedia.org', 'wikipedia.org',
];

// 被墙的域名（黑名单）
const blockedDomains = [
  'instagram.com', 'lookaside.instagram.com',
  'reddit.com', 'i.redd.it', 'preview.redd.it',
  'youtube.com', 'i.ytimg.com', 'ytimg.com',
  'twitter.com', 'x.com', 'twimg.com',
  'facebook.com', 'fbsbx.com',
  'googleusercontent.com', 'ggpht.com',
  'pinterest.com', 'pinimg.com',
];

function filterAccessibleImages(images) {
  const result = [];
  
  for (const img of images) {
    // 检查是否在黑名单
    const isBlocked = blockedDomains.some(domain => img.includes(domain));
    if (isBlocked) continue;
    
    // 检查是否在白名单
    const isAccessible = accessibleDomains.some(domain => img.includes(domain));
    if (isAccessible) {
      result.unshift(img);  // 白名单优先，插到前面
    } else {
      result.push(img);  // 其他放在后面
    }
  }
  
  return result;
}

// 调用 Tavily API 搜索图片
const body = {
  [REDACTED_SECRET],
  query: `${query} 照片 图片 portrait`,
  search_depth: "basic",
  topic: "general",
  max_results: 20,
  include_answer: false,
  include_raw_content: false,
  include_images: true,  // 关键参数！
};

const resp = await fetch("https://api.tavily.com/search", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

if (!resp.ok) {
  const text = await resp.text().catch(() => "");
  throw new Error(`Tavily Search failed (${resp.status}): ${text}`);
}

const data = await resp.json();
let images = data.images || [];

// 过滤图片
images = filterAccessibleImages(images);

// 限制数量
images = images.slice(0, maxImages);

// JSON 输出
if (jsonOutput) {
  console.log(JSON.stringify({ query, images, count: images.length }, null, 2));
  process.exit(0);
}

// 普通输出
console.log(`## 搜索: "${query}"`);
console.log(`找到 ${images.length} 张图片:\n`);

images.forEach((img, i) => {
  console.log(`${i + 1}. ${img}`);
});

// 下载模式
if (shouldDownload && images.length > 0) {
  const fs = await import('fs');
  const path = await import('path');
  const { execSync } = await import('child_process');
  
  const photoDir = path.join(process.env.HOME, '.openclaw/workspace/skills/partner-creator/assets/photos');
  
  // 创建目录
  if (!fs.existsSync(photoDir)) {
    fs.mkdirSync(photoDir, { recursive: true });
  }
  
  // 清理旧照片
  const oldFiles = fs.readdirSync(photoDir).filter(f => /\.(jpg|png|webp)$/i.test(f));
  oldFiles.forEach(f => fs.unlinkSync(path.join(photoDir, f)));
  
  console.log(`\n## 下载图片到: ${photoDir}\n`);
  
  let success = 0;
  for (let i = 0; i < images.length; i++) {
    const url = images[i];
    const outputPath = path.join(photoDir, `photo_${i + 1}.jpg`);
    
    try {
      console.log(`[${i + 1}/${images.length}] 下载: ${url}`);
      execSync(`curl -sL -o "${outputPath}" "${url}"`, { stdio: 'pipe' });
      
      // 检查文件
      const stats = fs.statSync(outputPath);
      if (stats.size > 1000) {
        console.log(`  ✓ 已保存: photo_${i + 1}.jpg (${stats.size} bytes)`);
        success++;
      } else {
        console.log(`  ✗ 文件太小`);
        fs.unlinkSync(outputPath);
      }
    } catch (err) {
      console.log(`  ✗ 下载失败: ${err.message}`);
    }
  }
  
  console.log(`\n下载完成: ${success}/${images.length}`);
}
