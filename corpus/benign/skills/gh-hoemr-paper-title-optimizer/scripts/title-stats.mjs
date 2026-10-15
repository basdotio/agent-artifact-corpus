#!/usr/bin/env node
// title-stats.mjs — 顶会录用标题的「数字用法」统计分析
//
// 数据源：papercopilot/paperlists 的 <venue><year>.json（顶层 JSON 数组，元素含
// title；可选 status / award / gs_citation 字段）。
//   https://github.com/papercopilot/paperlists
//
// 回答两个问题：
//   1. 什么时候带数字 —— 录用标题里带数字的占比；oral/spotlight/award 档 vs
//      poster 档；带数字 vs 不带数字的引用数差异（gs_citation 可用时）。
//   2. 怎么带 —— 形式（×/％/+N/points/拼写数词/嵌入型号）、位置（冒号前/后）、
//      精度（整数 vs 小数位）。48.6% 这类小数在标题里常不常见，用数据说话。
//
// 口径（重要）：with_number 区分两档——
//   embedded  = 数字嵌在型号/标识符里（3D、LLaMA-2、Qwen3-4B），不是量化 claim
//   claim     = 标题里真的出现量化数字（倍数/百分比/增量/计数/规模/拼写数词）
//
// 用法：
//   node title-stats.mjs /path/to/iclr2025.json [nips2024.json ...]
//   node title-stats.mjs --json --out stats.json *.json
//   node title-stats.mjs --all-status iclr2025.json   # 不剔除 Reject/Withdraw
//
// 退出码：0 成功；1 参数/文件错误

import { readFileSync, writeFileSync } from "node:fs";
import { basename } from "node:path";

const argv = process.argv.slice(2);
if (argv.length === 0 || argv.includes("--help")) {
  console.log(`顶会标题数字用法分析

  node title-stats.mjs [options] <file.json> [<file.json> ...]

输入
  papercopilot/paperlists 的 <venue><year>.json。元素有 title 即可跑；
  有 status（Oral/Spotlight/Poster/Reject/...）、award、gs_citation 时自动启用
  质量分层与引用对比。

选项
  --json            输出机器可读 JSON
  --out <file>      写 JSON 到文件
  --examples <n>    每种形式最多列几个示例标题，默认 4
  --all-status      默认会剔除 status 含 Reject/Withdraw 的条目（paperlists 的
                    ICLR 文件混有未录用稿）；此开关关闭剔除`);
  process.exit(argv.length === 0 ? 1 : 0);
}

const opt = { json: false, out: null, examples: 4, allStatus: false };
const files = [];
for (let i = 0; i < argv.length; i++) {
  const a = argv[i];
  if (a === "--json") opt.json = true;
  else if (a === "--out") opt.out = argv[++i];
  else if (a === "--examples") opt.examples = Number(argv[++i]);
  else if (a === "--all-status") opt.allStatus = true;
  else files.push(a);
}
if (files.length === 0) { console.error("至少给一个 paperlists JSON 文件"); process.exit(1); }

// ---- 形式识别 --------------------------------------------------------------
const RX = {
  multiplier:  /(\d+(?:\.\d+)?)\s*[x×]\b/i,                // 2×, 1.4x
  percent:     /(\d+(?:\.\d+)?)\s*%/,                       // 30%, 48.6%
  plusDelta:   /[+＋]\s*\d/,                                 // +23, +3.5
  points:      /\b\d+(?:\.\d+)?\s*(?:points?|pts?|pp)\b/i,  // 9.6 points
  topK:        /\btop[-\s]?\d+\b/i,                          // top-5
  shot:        /\b\d+\s*-?\s*shot\b/i,                       // 2-shot
  spelled:     /\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\b/i,
  magnitude:   /\b\d+(?:\.\d+)?\s*[bmk]\b(?![a-z])/i,        // 7B, 1M（模型/数据规模）
};

function classify(title) {
  const forms = new Set();
  for (const [name, rx] of Object.entries(RX)) if (rx.test(title)) forms.add(name);
  const stripped = title
    .replace(RX.multiplier, " ").replace(RX.percent, " ").replace(RX.plusDelta, " ")
    .replace(RX.points, " ").replace(RX.topK, " ").replace(RX.shot, " ")
    .replace(RX.magnitude, " ");
  if (/(?:^|[\s([{])[-+]?[\d,]+(?:\.\d+)?(?=$|[\s)\]},:;.!?])/.test(stripped)) forms.add("count");
  if (/\d/.test(title) && /\d[a-z]|[a-z]{2}\d/i.test(title)) forms.add("embedded");
  return { forms, hasClaim: [...forms].some((f) => f !== "embedded"), hasDigit: /\d/.test(title) };
}

function colonSplit(title) {
  const i = title.search(/[:：]/);
  if (i < 0) return null;
  return { before: title.slice(0, i), after: title.slice(i + 1) };
}

function tierOf(paper) {
  if (paper.award === true) return "award";
  const s = String(paper.status ?? "").toLowerCase();
  if (s.includes("oral")) return "oral";
  if (s.includes("spotlight")) return "spotlight";
  if (s.includes("poster")) return "poster";
  if (s) return "other";
  return "unknown";
}

const EXCLUDED = /reject|withdraw/i;
const citations = (p) => {
  const v = Number(p.gs_citation);
  return Number.isFinite(v) && v >= 0 ? v : null;
};
const median = (arr) => {
  const s = arr.filter((x) => x != null).sort((a, b) => a - b);
  return s.length ? s[Math.floor(s.length / 2)] : null;
};

// ---- 主流程 -----------------------------------------------------------------
const report = { generated_at: new Date().toISOString(), source: "papercopilot/paperlists", files: {} };

for (const f of files) {
  let papers;
  try { papers = JSON.parse(readFileSync(f, "utf8")); }
  catch (e) { report.files[basename(f)] = { error: String(e.message ?? e) }; continue; }
  if (!Array.isArray(papers)) { report.files[basename(f)] = { error: "顶层不是数组" }; continue; }

  if (!opt.allStatus) papers = papers.filter((p) => !EXCLUDED.test(String(p.status ?? "")));
  const n = papers.filter((p) => p.title).length;

  const acc = {
    withDigit: 0, withClaim: 0, forms: {}, examples: {},
    percentInteger: 0, percentDec1: 0, percentDec2: 0,
    colon: 0, numBefore: 0, numAfter: 0, numBoth: 0,
    lenClaim: [], lenNoClaim: [],
    tiers: {},
    citeClaim: [], citeNoClaim: [], citeEmbedded: [], citeClean: [],
  };
  const pushEx = (k, t) => {
    acc.examples[k] ??= [];
    if (acc.examples[k].length < opt.examples && t.length < 110) acc.examples[k].push(t);
  };

  for (const p of papers) {
    const title = String(p.title ?? "").replace(/\s+/g, " ").trim();
    if (!title) continue;
    const { forms, hasClaim, hasDigit } = classify(title);
    const words = title.split(" ").length;
    const cit = citations(p);

    if (hasDigit) acc.withDigit++;
    if (hasClaim) { acc.withClaim++; acc.lenClaim.push(words); } else acc.lenNoClaim.push(words);
    for (const k of forms) { acc.forms[k] = (acc.forms[k] ?? 0) + 1; pushEx(k, title); }

    for (const m of title.match(/(\d+(?:\.\d+)?)\s*%/g) ?? []) {
      const v = m.match(/(\d+(?:\.\d+)?)/)[1];
      if (!v.includes(".")) acc.percentInteger++;
      else if (/\.\d$/.test(v)) acc.percentDec1++;
      else acc.percentDec2++;
    }

    const cs = colonSplit(title);
    if (cs) {
      acc.colon++;
      const b = /\d/.test(cs.before) || classify(cs.before).forms.has("spelled");
      const a = /\d/.test(cs.after) || classify(cs.after).forms.has("spelled");
      if (b && a) acc.numBoth++;
      else if (b) acc.numBefore++;
      else if (a) acc.numAfter++;
    }

    const tier = tierOf(p);
    acc.tiers[tier] ??= { n: 0, withClaim: 0 };
    acc.tiers[tier].n++;
    if (hasClaim) acc.tiers[tier].withClaim++;

    if (cit != null) {
      if (hasClaim) acc.citeClaim.push(cit);
      else if (hasDigit) acc.citeEmbedded.push(cit);
      else acc.citeClean.push(cit);
    }
  }

  const pct = (a, b) => (b ? +(100 * a / b).toFixed(1) : null);
  const tierOut = Object.fromEntries(Object.entries(acc.tiers).map(([k, v]) => [k, {
    n: v.n, with_claim: v.withClaim, with_claim_pct: pct(v.withClaim, v.n),
  }]));
  report.files[basename(f)] = {
    n_titles: n,
    has_digit_pct: pct(acc.withDigit, n),
    claim_number_pct: pct(acc.withClaim, n),
    forms: Object.fromEntries(Object.entries(acc.forms).sort((a, b) => b[1] - a[1]).map(([k, v]) => [k, { n: v, pct: pct(v, n) }])),
    percent_precision: { integer: acc.percentInteger, one_decimal: acc.percentDec1, two_plus_decimal: acc.percentDec2 },
    colon: { n_colon: acc.colon, colon_pct: pct(acc.colon, n), number_before: acc.numBefore, number_after: acc.numAfter, number_both: acc.numBoth },
    median_words: { claim: median(acc.lenClaim), no_claim: median(acc.lenNoClaim) },
    tiers: tierOut,
    citations: {
      metric: "gs_citation 中位数",
      claim_number: median(acc.citeClaim),
      embedded_only: median(acc.citeEmbedded),
      no_number: median(acc.citeClean),
      n_claim: acc.citeClaim.length, n_embedded: acc.citeEmbedded.length, n_clean: acc.citeClean.length,
    },
    examples: acc.examples,
  };
  const r = report.files[basename(f)];
  process.stderr.write(
    `${basename(f)}: ${n} 篇 ｜ 含型号数字 ${r.has_digit_pct}% ｜ 定量数字 ${r.claim_number_pct}% ｜ 引用中位数: 定量 ${r.citations.claim_number} vs 无数字 ${r.citations.no_number}\n`);
}

if (opt.out) { writeFileSync(opt.out, JSON.stringify(report, null, 2)); process.stderr.write(`已写入 ${opt.out}\n`); }
console.log(JSON.stringify(report, null, 2));
