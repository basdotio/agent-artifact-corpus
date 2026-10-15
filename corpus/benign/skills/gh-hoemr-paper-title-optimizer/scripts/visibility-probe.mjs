#!/usr/bin/env node
// visibility-probe.mjs — 改写「前」跑一次，建立可见度基线
//
// 为什么需要：改完标题摘要如果没有基线，你无法判断到底变好还是变坏。
// 真实结果要 3-9 个月才观测得到，但基线必须在下笔之前就存下来。
//
// 三个后端，能测什么就测什么，不能测的显式标 skipped——绝不输出假的 0：
//
//   arxiv      无需任何 key。量「用这组 query 能不能在 arXiv 里捞到这篇论文」。
//              这是文献库层面的可发现性，也是研究者的主要检索路径。
//   openai     需要 OPENAI_API_KEY。量「ChatGPT 联网搜索会不会引用这篇论文」。
//              未在无 key 环境验证过，用前请先跑 --dry-run 确认请求体。
//   perplexity 需要 PERPLEXITY_API_KEY。同上。
//
// 用法：
//   node visibility-probe.mjs --queries q.json --title "Exact Paper Title" [--arxiv-id 2311.09735]
//   node visibility-probe.mjs --queries q.json --title "..." --engines arxiv,openai --out baseline.json
//   node visibility-probe.mjs --queries q.json --title "..." --engines openai --dry-run
//
// q.json 格式（推荐第二种，字段齐全）：
//   ["natural language question", ...]                                    ← 简写，只有 q
//   {"queries":[{"q":"自然语言问句","arxiv_query":"all:generative AND all:optimization"}]}
//
// 为什么必须分两个字段：AI 引擎吃自然语言问句，arXiv 吃的是字面短语匹配。
// 实跑教训——把 "how to optimize content for AI search engines" 这种问句直接
// 丢给 arXiv 的 all:"..."，返回恒为 0，因为论文摘要里不会出现这句话。
// 派生出 arxiv_query 需要判断力，所以由调用方（skill 里的 LLM）来写，脚本不做转换。

import { writeFileSync, readFileSync, existsSync } from "node:fs";

const argv = process.argv.slice(2);
if (argv.length === 0 || argv.includes("--help")) {
  console.log(`可见度基线探针

  node visibility-probe.mjs --queries <file.json> --title "<exact title>" [options]

必需
  --queries <file>     JSON 文件。推荐 [{"q":"自然语言问句","arxiv_query":"all:x AND all:y"}]
  --title "<title>"    论文的完整标题（用于匹配命中）

可选
  --arxiv-id <id>      有则 arXiv 后端可精确比对 ID
  --engines <list>     逗号分隔，默认 arxiv。可选 arxiv,openai,perplexity
  --out <file>         写 JSON 结果
  --dry-run            只打印将要发出的请求，不实际调用（openai/perplexity 用）
  --top 10             每条 query 在 arXiv 结果里检查前 N 条，默认 10

为什么 q 和 arxiv_query 要分开：AI 引擎吃自然语言问句，arXiv 走字面短语匹配。
实跑发现，把问句直接丢给 arXiv 的 all:"..." 返回恒为 0——论文摘要里不会出现
那句话。派生出 arxiv_query 需要判断力，所以由调用方写，脚本不做转换。
缺 arxiv_query 的行会计入 unmeasured，不参与 hit_rate。

环境变量：OPENAI_API_KEY / PERPLEXITY_API_KEY（缺了就跳过对应后端，不报错）`);
  process.exit(argv.length === 0 ? 1 : 0);
}

const opt = { queriesFile: null, title: "", arxivId: null, engines: ["arxiv"], out: null, dryRun: false, top: 10 };
for (let i = 0; i < argv.length; i++) {
  const a = argv[i];
  if (a === "--queries") opt.queriesFile = argv[++i];
  else if (a === "--title") opt.title = argv[++i];
  else if (a === "--arxiv-id") opt.arxivId = argv[++i];
  else if (a === "--engines") opt.engines = argv[++i].split(",").map((s) => s.trim());
  else if (a === "--out") opt.out = argv[++i];
  else if (a === "--dry-run") opt.dryRun = true;
  else if (a === "--top") opt.top = Number(argv[++i]);
  else { console.error(`无法解析参数: ${a}`); process.exit(1); }
}
if (!opt.queriesFile || !opt.title) { console.error("--queries 和 --title 都是必需的"); process.exit(1); }
if (!existsSync(opt.queriesFile)) { console.error(`找不到 ${opt.queriesFile}`); process.exit(1); }

const qRaw = JSON.parse(readFileSync(opt.queriesFile, "utf8"));
const rawQueries = Array.isArray(qRaw) ? qRaw : qRaw.queries;
if (!Array.isArray(rawQueries) || rawQueries.length === 0) { console.error("queries 文件里没有非空数组"); process.exit(1); }

// 归一化成 {q, arxiv_query, derived}。derived=false 表示调用方没给 arxiv 检索式，
// 此时 arxiv 后端大概率返回 0——结果里会显式标注 derived=false，别把它读成"论文不可见"。
const queries = rawQueries.map((r) => {
  if (typeof r === "string") return { q: r, arxiv_query: null, derived: false };
  return { q: r.q, arxiv_query: r.arxiv_query ?? null, derived: Boolean(r.arxiv_query) };
});
if (queries.some((q) => !q.q)) { console.error("每条 query 都要有 q 字段"); process.exit(1); }
const missingDerived = queries.filter((q) => !q.derived).length;
if (missingDerived > 0) {
  process.stderr.write(
    `提示: ${missingDerived}/${queries.length} 条 query 缺 arxiv_query。\n` +
    `      自然语言问句在 arXiv 上会字面失配，arxiv 后端的结果只作参考，不要当结论。\n`
  );
}

const titleTokens = opt.title.toLowerCase().split(/[^a-z0-9]+/).filter((t) => t.length > 3);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// ---- 后端: arxiv --------------------------------------------------------
async function probeArxiv(q) {
  if (!q.arxiv_query) {
    return { status: "ok", derived: false, found: null, detail: "调用方未提供 arxiv_query，未查询" };
  }
  const url = `https://export.arxiv.org/api/query?${new URLSearchParams({
    search_query: q.arxiv_query, start: 0, max_results: opt.top, sortBy: "relevance",
  })}`;
  try {
    const res = await fetch(url, {
      headers: { "User-Agent": "paper-title-optimizer/0.1 (visibility probe; contact: local)" },
      signal: AbortSignal.timeout(45000),
    });
    if (!res.ok) return { status: "error", detail: `HTTP ${res.status}` };
    const body = await res.text();
    const total = Number(body.match(/opensearch:totalResults[^>]*>(\d+)</)?.[1] ?? 0);
    const entries = [...body.matchAll(/<entry>[\s\S]*?<\/entry>/g)].map((m) => m[0]);

    let rank = null, via = null;
    if (opt.arxivId) {
      const i = entries.findIndex((e) => e.includes(opt.arxivId));
      if (i >= 0) { rank = i + 1; via = "arxiv_id"; }
    }
    if (rank == null && titleTokens.length) {
      const i = entries.findIndex((e) => {
        const t = (e.match(/<title>([\s\S]*?)<\/title>/)?.[1] ?? "").toLowerCase();
        const hit = titleTokens.filter((tok) => t.includes(tok)).length;
        return hit >= Math.ceil(titleTokens.length * 0.7);
      });
      if (i >= 0) { rank = i + 1; via = "title_overlap"; }
    }
    return { status: "ok", derived: true, total_results: total, found: rank != null, rank, matched_by: via, checked_top: opt.top };
  } catch (e) {
    return { status: "error", detail: String(e.message ?? e) };
  }
}

// ---- 后端: openai -------------------------------------------------------
async function probeOpenai(q, { dryRun }) {
  const key = process.env.OPENAI_API_KEY;
  if (!key) return { status: "skipped", reason: "未设置 OPENAI_API_KEY —— 这不是 0，是没测" };
  const body = {
    model: process.env.PAPER_GEO_OPENAI_MODEL || "gpt-4o-mini",
    input: q.q,
    tools: [{ type: "web_search_preview" }],
  };
  if (dryRun) return { status: "dry_run", request: { url: "https://api.openai.com/v1/responses", body } };

  try {
    const res = await fetch("https://api.openai.com/v1/responses", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${key}` },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(120000),
    });
    if (!res.ok) return { status: "error", detail: `HTTP ${res.status}: ${(await res.text()).slice(0, 200)}` };
    const data = await res.json();
    const text = (data.output_text ?? "").toLowerCase();
    const citedUrls = (data.output ?? [])
      .flatMap((o) => o.content ?? [])
      .flatMap((c) => c.annotations ?? [])
      .map((a) => String(a.url ?? "").toLowerCase());
    const idHit = opt.arxivId ? citedUrls.some((u) => u.includes(opt.arxivId)) : false;
    const titleHit = titleTokens.length
      ? titleTokens.filter((t) => text.includes(t)).length >= Math.ceil(titleTokens.length * 0.7)
      : false;
    return {
      status: "ok",
      cited: idHit || titleHit,
      cited_by: idHit ? "arxiv_id_in_citation" : titleHit ? "title_in_answer" : null,
      n_citations: citedUrls.length,
    };
  } catch (e) {
    return { status: "error", detail: String(e.message ?? e) };
  }
}

// ---- 后端: perplexity ---------------------------------------------------
async function probePerplexity(q, { dryRun }) {
  const key = process.env.PERPLEXITY_API_KEY;
  if (!key) return { status: "skipped", reason: "未设置 PERPLEXITY_API_KEY —— 这不是 0，是没测" };
  const body = {
    model: process.env.PAPER_GEO_PPLX_MODEL || "sonar",
    messages: [{ role: "user", content: q.q }],
  };
  if (dryRun) return { status: "dry_run", request: { url: "https://api.perplexity.ai/chat/completions", body } };

  try {
    const res = await fetch("https://api.perplexity.ai/chat/completions", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${key}` },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(120000),
    });
    if (!res.ok) return { status: "error", detail: `HTTP ${res.status}: ${(await res.text()).slice(0, 200)}` };
    const data = await res.json();
    const text = (data.choices?.[0]?.message?.content ?? "").toLowerCase();
    const urls = (data.citations ?? []).map(String);
    const idHit = opt.arxivId ? urls.some((u) => u.toLowerCase().includes(opt.arxivId)) : false;
    const titleHit = titleTokens.length
      ? titleTokens.filter((t) => text.includes(t)).length >= Math.ceil(titleTokens.length * 0.7)
      : false;
    return { status: "ok", cited: idHit || titleHit, cited_by: idHit ? "arxiv_id_in_citation" : titleHit ? "title_in_answer" : null, n_citations: urls.length };
  } catch (e) {
    return { status: "error", detail: String(e.message ?? e) };
  }
}

const BACKENDS = { arxiv: probeArxiv, openai: probeOpenai, perplexity: probePerplexity };

// ---- 主流程 --------------------------------------------------------------
const rows = [];
for (const q of queries) {
  const row = { query: q.q, arxiv_query: q.arxiv_query, engines: {} };
  for (const name of opt.engines) {
    const fn = BACKENDS[name];
    if (!fn) { row.engines[name] = { status: "error", detail: "未知后端" }; continue; }
    row.engines[name] = await fn(q, { dryRun: opt.dryRun });
    if (name === "arxiv") await sleep(3200); // arXiv 礼貌间隔
  }
  rows.push(row);
  process.stderr.write(`  [${rows.length}/${queries.length}] ${q.q}\n`);
}

// ---- 汇总 ----------------------------------------------------------------
// 只统计真正测到了的行。derived=false 的行 found 是 null，算进分母会把
// "没测" 稀释成 "测了没命中"，那比漏报更坏。
const summary = {};
for (const name of opt.engines) {
  const res = rows.map((r) => r.engines[name]).filter((r) => r?.status === "ok");
  const measured = res.filter((r) => r.derived !== false);
  summary[name] = {
    measured: measured.length,
    unmeasured: res.length - measured.length,
    skipped: rows.some((r) => r.engines[name]?.status === "skipped"),
    hit_rate: measured.length
      ? +(measured.filter((r) => (r.found ?? r.cited) === true).length / measured.length).toFixed(3)
      : null,
  };
}

const report = {
  measured_at: new Date().toISOString(),
  paper: { title: opt.title, arxiv_id: opt.arxivId },
  n_queries: queries.length,
  engines_requested: opt.engines,
  summary,
  rows,
  caveat: skippedAny(rows)
    ? "部分后端未测量。summary 里 skipped=true 的引擎，其 hit_rate 为 null（未测），不可解读为 0。"
    : "全部后端均已测量。",
};
function skippedAny(rs) { return rs.some((r) => Object.values(r.engines).some((e) => e?.status === "skipped")); }

if (opt.out) { writeFileSync(opt.out, JSON.stringify(report, null, 2)); process.stderr.write(`基线已写入 ${opt.out}\n`); }
console.log(JSON.stringify(report, null, 2));
