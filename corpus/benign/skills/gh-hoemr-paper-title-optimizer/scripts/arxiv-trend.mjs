#!/usr/bin/env node
// arxiv-trend.mjs — 分年短语计数探针
//
// 用途：给 paper-title-optimizer 的第三层（热度对齐）提供实时数据。
// 当 references/term-pool.csv 不存在或过期时，回落到这个脚本现场取数。
//
// 数据源：arXiv API 全文短语检索 (all:"term")，按 submittedDate 区间切年。
// 测的是「发表量趋势」，不是搜索量。对论文场景这是更合适的指标——
// 引用你的是研究者，研究者翻的是文献库，不是搜索引擎。
//
// 用法：
//   node arxiv-trend.mjs "term one" "term two" [...]
//   node arxiv-trend.mjs --years 2022,2023,2024,2025,2026 --json "LLM agents"
//   node arxiv-trend.mjs --pool ../references/term-pool.csv
//
// 退出码：0 成功；1 参数错误；2 网络/API 错误

import { writeFileSync, readFileSync, existsSync } from "node:fs";

const BASE = "https://export.arxiv.org/api/query";
const UA = { "User-Agent": "paper-title-optimizer/0.1 (arXiv trend probe; contact: local)" };
const POLITE_MS = 3200; // arXiv 建议请求间隔
const TIMEOUT_MS = 60000; // arXiv 偶发慢，45s 会误杀
const MAX_RETRY = 2;

// ---- 参数解析 ------------------------------------------------------------
const argv = process.argv.slice(2);
if (argv.includes("--help") || argv.length === 0) {
  console.log(`arXiv 分年趋势探针

  node arxiv-trend.mjs [options] <term> [<term> ...]

选项
  --years 2022,2023,2024      覆盖默认年份列表
  --json                     输出 JSON（供下游 skill 消费）
  --pool <file.csv>          从词池 CSV 读取 term 列，跳过现网查询
  --out <file.json>          写结果到文件
  --min-vol 30               rising 状态所需的最小年化量
  --hot-vol 1000             background 状态的量级门槛

状态判定（阈值是启发式，见 SKILL.md「未决」节，需真实数据校准）
  background  高频 + 低增速，入场券而非钩子
  rising      有体量 + 同比 >=2x，真正的钩子
  peaked      曾经高频但已过峰，禁止使用
  stale       过气，禁止 retro-fit`);
  process.exit(argv.includes("--help") ? 0 : 1);
}

const opt = { terms: [], years: null, json: false, pool: null, out: null, minVol: 30, hotVol: 1000 };
for (let i = 0; i < argv.length; i++) {
  const a = argv[i];
  if (a === "--years") {
    const v = argv[++i];
    if (v == null || v.startsWith("--")) { console.error("--years 需要一个值，如 --years 2022,2023,2024"); process.exit(1); }
    opt.years = v.split(",").map(Number).filter((n) => Number.isFinite(n));
    if (opt.years.length === 0) { console.error("--years 没解析出有效年份"); process.exit(1); }
  }
  else if (a === "--json") opt.json = true;
  else if (a === "--pool") opt.pool = argv[++i];
  else if (a === "--min-vol") opt.minVol = Number(argv[++i]);
  else if (a === "--hot-vol") opt.hotVol = Number(argv[++i]);
  else if (a === "--out") opt.out = argv[++i];
  else if (a.startsWith("--")) { console.error(`未知选项: ${a}`); process.exit(1); }
  else opt.terms.push(a);
}

const now = new Date();
const defaultYears = [now.getFullYear() - 4, now.getFullYear() - 3, now.getFullYear() - 2, now.getFullYear() - 1, now.getFullYear()];
const years = opt.years ?? defaultYears;

// 跨年比较必须归一化到同一时间跨度，否则今年必然"看起来在跌"。
// 注意：当年折算比例过低（1–2 月）时年化值噪声极大，输出里会带低置信标注。
const yearFraction = (y) => (y === now.getFullYear()
  ? (now.getMonth() * 30.44 + now.getDate()) / 365
  : 1);
const LOW_CONFIDENCE_FRACTION = 0.25;

if (opt.pool && existsSync(opt.pool)) {
  const csv = readFileSync(opt.pool, "utf8").trim().split("\n").slice(1);
  for (const line of csv) {
    const t = line.split(",")[0]?.trim();
    if (t) opt.terms.push(t);
  }
  if (opt.terms.length === 0) { console.error(`词池 ${opt.pool} 里没读到 term 列`); process.exit(1); }
}

if (opt.terms.length === 0) { console.error("至少给一个 term"); process.exit(1); }

// ---- 取数 ----------------------------------------------------------------
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function countForYear(term, year, attempt = 0) {
  const q = `all:"${term}" AND submittedDate:[${year}01010000 TO ${year}12312359]`;
  const url = `${BASE}?${new URLSearchParams({ search_query: q, start: 0, max_results: 1 })}`;
  try {
    const res = await fetch(url, { headers: UA, signal: AbortSignal.timeout(TIMEOUT_MS) });
    if (!res.ok) {
      // 429/503 是 arXiv 常态，退避后重试比直接放弃划算
      if ([429, 500, 502, 503, 504].includes(res.status) && attempt < 2) {
        await sleep(POLITE_MS * (attempt + 2));
        return countForYear(term, year, attempt + 1);
      }
      return { error: `HTTP ${res.status}` };
    }
    const body = await res.text();
    const m = body.match(/opensearch:totalResults[^>]*>(\d+)</);
    if (!m) return { error: "totalResults not found" };
    const n = Number(m[1]);
    return { raw: n, annualized: Math.round(n / yearFraction(year)) };
  } catch (e) {
    // 超时/网络抖动：重试两次后记为错误，保留已取到的其他年份数据。
    // 不让一个失败请求毁掉整轮取数是这个脚本最基本的要求。
    if (attempt < 2) {
      await sleep(POLITE_MS * (attempt + 2));
      return countForYear(term, year, attempt + 1);
    }
    return { error: String(e.name ?? e.message ?? e) };
  }
}

// ---- 状态判定 ------------------------------------------------------------
function classify(series, { minVol, hotVol }) {
  const pts = series.filter((p) => p.value != null);
  if (pts.length < 3) return { status: "insufficient", reason: "少于 3 年数据" };
  const last = pts[pts.length - 1].value;
  const prev = pts[pts.length - 2].value;
  const prev2 = pts[pts.length - 3].value;
  const base = Math.max((prev + prev2) / 2, 1);
  const growth = last / base;
  const peak = Math.max(...pts.map((p) => p.value));

  // 顺序有讲究：先判 rising，否则高量词会被 background 的阈值先吃掉。
  // 实跑教训：CoT 增长 1.6x，早先按 "background 需 growth<1.5" 判会漏进 flat。
  if (growth >= 2 && last >= minVol) return { status: "rising", growth: +growth.toFixed(2), reason: "有体量且同比翻倍以上" };
  if (last >= hotVol) return { status: "background", growth: +growth.toFixed(2), reason: "高频，增速不足以称为钩子，作入场券用" };
  if (last < prev && prev < prev2 && peak >= minVol) return { status: "stale", growth: +growth.toFixed(2), reason: "连续两年下滑" };
  return { status: "flat", growth: +growth.toFixed(2), reason: "量级与增速均不显著" };
}

// ---- 主流程 --------------------------------------------------------------
const results = [];
let failed = 0;

for (const term of opt.terms) {
  const series = [];
  for (const y of years) {
    const r = await countForYear(term, y);
    series.push({ year: y, raw: r.raw ?? null, value: r.annualized ?? null, error: r.error });
    if (r.error) failed++;
    await sleep(POLITE_MS);
  }
  const verdict = classify(series, opt);
  results.push({ term, series, ...verdict, measured_at: new Date().toISOString() });
  process.stderr.write(`  ${term}: ${verdict.status} (growth ${verdict.growth ?? "n/a"})\n`);
}

const thisYearFraction = yearFraction(now.getFullYear());
const annualNote = thisYearFraction < LOW_CONFIDENCE_FRACTION
  ? `low（当年只过了 ${(thisYearFraction * 100).toFixed(0)}%，年化值噪声大，跨年比较不可靠）`
  : "ok";

const report = { measured_at: new Date().toISOString(), years, annualization_confidence: annualNote, thresholds: { minVol: opt.minVol, hotVol: opt.hotVol }, results };
if (annualNote !== "ok") process.stderr.write(`⚠ 年化置信度: ${annualNote}\n`);

if (opt.out) {
  writeFileSync(opt.out, JSON.stringify(report, null, 2));
  process.stderr.write(`已写入 ${opt.out}\n`);
}

if (opt.json) {
  console.log(JSON.stringify(report, null, 2));
} else {
  const head = ["term", ...years.map((y) => `${y}*`)].join("\t");
  console.log(head);
  for (const r of results) {
    console.log([r.term, ...r.series.map((s) => (s.value == null ? "ERR" : s.value))].join("\t"));
  }
  console.log("\n* 年化值（当年按已过天数折算）");
  for (const r of results) {
    const g = r.growth == null ? "n/a" : `${r.growth}x`;
    console.log(`  ${r.status.padEnd(9)} ${r.term}  growth=${g}  ${r.reason}`);
  }
  console.log("\n注意：status 是启发式判定，阈值需校准。rising 才有资格进摘要。");
}

process.exit(failed > 0 && results.every((r) => r.series.every((s) => s.error)) ? 2 : 0);
