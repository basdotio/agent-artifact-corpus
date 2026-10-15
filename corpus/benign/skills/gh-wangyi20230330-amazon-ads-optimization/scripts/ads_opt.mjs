#!/usr/bin/env node
// ads_opt.mjs — 亚马逊投放优化计算器 + 诊断器（零依赖，Node 18+）
//
//  calc     盈亏平衡 ACoS / 目标 ACoS / 可接受 CPC
//  diagnose 搜索词报告或广告位报告 -> P0/P1/P2 动作清单
//
// 范例:
//   node ads_opt.mjs calc --price 39.99 --cost 8 --fba 7.5 --first-leg 3 --commission-rate 15 --return-rate 5 --target-margin 15 --cvr 8
//   node ads_opt.mjs diagnose --file search-terms.csv --target-acos 25 --break-even-acos 40
//   node ads_opt.mjs diagnose --file placement.csv --mode placement --target-acos 25
//   node ads_opt.mjs keywords --seed <种子词> --site <站点>

import fs from 'node:fs'

const argv = process.argv.slice(2)
const cmd = (argv[0] || '').toLowerCase()

function opt(name, def) {
  const i = argv.indexOf('--' + name)
  if (i < 0 || argv[i + 1] === undefined || argv[i + 1].startsWith('--')) return def
  return argv[i + 1]
}
function has(name) { return argv.includes('--' + name) }
function num(name, def) {
  const v = opt(name, undefined)
  if (v === undefined) return def
  const n = Number(v)
  if (Number.isNaN(n)) throw new Error(`参数 --${name} 不是数字: ${v}`)
  return n
}
const pct = (name, def) => num(name, def) / 100

function round(n, d = 2) {
  if (!Number.isFinite(n)) return null
  const p = Math.pow(10, d)
  return Math.round(n * p) / p
}
function fmtPct(x) { return x === null ? 'N/A' : (x * 100).toFixed(2) + '%' }
function money(x, cur) { return x === null ? 'N/A' : (cur ? cur + ' ' : '') + x.toFixed(2) }
function bar() { console.log('-'.repeat(58)) }

// ---------------- calc ----------------
function calc() {
  const price = num('price', null)
  if (price === null) throw new Error('calc 需要 --price（售价）')
  const cost = num('cost', 0)
  const fba = num('fba', 0)
  const firstLeg = num('first-leg', 0)
  const commissionRate = pct('commission-rate', 15)
  const returnRate = pct('return-rate', 0)
  const returnLossRate = pct('return-loss-rate', 100)
  const targetMargin = pct('target-margin', 0)
  const cvr = pct('cvr', null)
  const cur = opt('currency', '')

  const commission = price * commissionRate
  const returnLoss = price * returnRate * returnLossRate
  const contribution = price - cost - fba - firstLeg - commission - returnLoss

  const breakEvenAcos = contribution / price
  const targetAcos = (contribution - price * targetMargin) / price
  const breakEvenRoas = breakEvenAcos > 0 ? 1 / breakEvenAcos : null
  const targetRoas = targetAcos > 0 ? 1 / targetAcos : null
  const breakEvenCpc = cvr === null ? null : price * cvr * breakEvenAcos
  const targetCpc = cvr === null ? null : price * cvr * targetAcos

  console.log('\n亚马逊广告投放 — 盈亏平衡与目标出价\n' + '='.repeat(58))
  console.log(`售价            ${money(price, cur)}`)
  console.log(`成本明细        货 ${money(cost, cur)} | FBA ${money(fba, cur)} | 头程 ${money(firstLeg, cur)}`)
  console.log(`              佣金 ${money(commission, cur)} (${(commissionRate * 100).toFixed(1)}%) | 退货损耗 ${money(returnLoss, cur)} (${(returnRate * 100).toFixed(1)}% x ${(returnLossRate * 100).toFixed(0)}%)`)
  bar()
  console.log(`广告前单位贡献  ${money(contribution, cur)}`)
  console.log(`盈亏平衡 ACoS   ${fmtPct(breakEvenAcos)}   (ROAS ${breakEvenRoas === null ? 'N/A' : breakEvenRoas.toFixed(2)})`)
  console.log(`目标 ACoS       ${fmtPct(targetAcos)}   (目标单件净利 ${money(price * targetMargin, cur)})`)
  console.log(`目标 ROAS       ${targetRoas === null ? 'N/A' : targetRoas.toFixed(2)}`)
  if (cvr !== null) {
    bar()
    console.log(`可接受 CPC      ${money(targetCpc, cur)}   <- 目标 ACoS ${fmtPct(targetAcos)} x CVR ${(cvr * 100).toFixed(2)}% x 售价`)
    console.log(`CPC 上限(不亏)  ${money(breakEvenCpc, cur)}`)
    console.log(`\n出价建议区间    ${money(targetCpc * 0.9, cur)} ~ ${money(targetCpc, cur)}（高于上限即结构性亏损）`)
  } else {
    bar()
    console.log('提示：加 --cvr 8 可算出「可接受 CPC」（出价天花板）。')
  }
  if (contribution <= 0) {
    bar()
    console.log('!! 警告：广告前单位贡献已 <= 0，当前定价/成本结构下广告无盈利空间。')
    console.log('   先解决定价、采购成本或 FBA 费用，不要靠调广告解决。')
  }
  if (targetAcos <= 0) {
    bar()
    console.log('!! 警告：目标 ACoS <= 0，说明目标净利已高于广告前贡献 —— 目标定得不可实现。')
  }
  console.log('')
}

// ---------------- diagnose ----------------
const H = {
  term: ['term', '搜索词', 'customer search term', 'search term', 'keywords', 'keyword', '投放词'],
  clicks: ['clicks', '点击', '点击量'],
  orders: ['orders', '订单', '订单数', 'purchases', '14天订单', '7天订单'],
  spend: ['spend', '花费', 'cost', '广告花费', '支出'],
  sales: ['sales', '销售额', '广告销售额', '14天销售额', '7天销售额'],
  campaign: ['campaign', '活动', '广告活动', 'campaign name'],
  matchtype: ['matchtype', '匹配方式', 'match type', 'targeting type'],
  impressions: ['impressions', '曝光', '曝光量'],
  placement: ['placement', '广告位', 'placement type'],
  bid: ['bid', '出价', 'cpc bid'],
}
function normKey(k) { return String(k).toLowerCase().replace(/[\s_-]/g, '') }
function buildMap(headers) {
  const m = {}
  for (const [field, alts] of Object.entries(H)) {
    for (const a of alts) {
      const na = normKey(a)
      const idx = headers.findIndex(h => normKey(h) === na)
      if (idx >= 0) { m[field] = idx; break }
    }
    if (m[field] === undefined) {
      for (const a of alts) {
        const na = normKey(a)
        const idx = headers.findIndex(h => normKey(h).includes(na) && na.length >= 3)
        if (idx >= 0) { m[field] = idx; break }
      }
    }
  }
  return m
}
function parseDelimited(text) {
  const clean = text.replace(/^\uFEFF/, '')
  const firstLine = clean.split(/\r?\n/)[0] || ''
  const delim = (firstLine.split('\t').length > firstLine.split(',').length) ? '\t' : ','
  const rows = []
  let row = [], cell = '', q = false
  for (let i = 0; i < clean.length; i++) {
    const c = clean[i]
    if (q) {
      if (c === '"') { if (clean[i + 1] === '"') { cell += '"'; i++ } else q = false }
      else cell += c
    } else if (c === '"') q = true
    else if (c === delim) { row.push(cell); cell = '' }
    else if (c === '\n') { row.push(cell); rows.push(row); row = []; cell = '' }
    else if (c !== '\r') cell += c
  }
  if (cell.length || row.length) { row.push(cell); rows.push(row) }
  return rows.filter(r => r.some(x => String(x).trim() !== ''))
}
function toNum(x) {
  if (x === undefined || x === null) return 0
  const s = String(x).replace(/[,$%¥€£\s]/g, '')
  const n = Number(s)
  return Number.isNaN(n) ? 0 : n
}

function diagnose() {
  const file = opt('file', null)
  if (!file) throw new Error('diagnose 需要 --file <csv文件>')
  const mode = (opt('mode', 'searchterm') || 'searchterm').toLowerCase()
  const targetAcos = pct('target-acos', 25)
  const breakEvenAcos = pct('break-even-acos', null)
  const minClicksRaw = opt('min-clicks', null)
  const wasteMult = num('waste-mult', 3)

  const raw = fs.readFileSync(file, 'utf8')
  let rows
  if (raw.trim().startsWith('[') || raw.trim().startsWith('{')) {
    const j = JSON.parse(raw)
    const arr = Array.isArray(j) ? j : (j.data || j.items || j.rows || [])
    const headers = [...new Set(arr.flatMap(o => Object.keys(o)))]
    rows = [headers, ...arr.map(o => headers.map(h => o[h]))]
  } else {
    rows = parseDelimited(raw)
  }
  if (rows.length < 2) throw new Error('文件里没有数据行')

  const headers = rows[0]
  const map = buildMap(headers)
  const keyField = mode === 'placement' ? 'placement' : 'term'
  if (map[keyField] === undefined) {
    throw new Error(`找不到「${keyField}」列。现有列: ${headers.join(' | ')}`)
  }
  for (const f of ['clicks', 'orders', 'spend']) {
    if (map[f] === undefined) throw new Error(`缺少必需列: ${f}（现有列: ${headers.join(' | ')}）`)
  }

  const data = rows.slice(1).map(r => {
    const clicks = toNum(r[map.clicks])
    const orders = toNum(r[map.orders])
    const spend = toNum(r[map.spend])
    const sales = map.sales !== undefined ? toNum(r[map.sales]) : 0
    const impressions = map.impressions !== undefined ? toNum(r[map.impressions]) : 0
    return {
      name: String(r[map[keyField]] || '').trim(),
      campaign: map.campaign !== undefined ? String(r[map.campaign] || '').trim() : '',
      matchType: map.matchtype !== undefined ? String(r[map.matchtype] || '').trim() : '',
      clicks, orders, spend, sales, impressions,
      acos: sales > 0 ? spend / sales : (spend > 0 ? Infinity : 0),
      cvr: clicks > 0 ? orders / clicks : 0,
      ctr: impressions > 0 ? clicks / impressions : null,
      cpc: clicks > 0 ? spend / clicks : 0,
    }
  }).filter(d => d.name)

  const totalClicks = data.reduce((s, d) => s + d.clicks, 0)
  const totalOrders = data.reduce((s, d) => s + d.orders, 0)
  const dataCvr = totalClicks > 0 ? totalOrders / totalClicks : 0
  const cvr = has('cvr') ? pct('cvr', dataCvr) : dataCvr
  // 阈值按本品 CVR 推导：需要的点击数 = 1 / CVR，绝对下限 5（见 references/verification.md V2）
  const minClicks = minClicksRaw !== null
    ? Math.max(1, Number(minClicksRaw))
    : Math.max(5, Math.round(1 / (cvr > 0 ? cvr : 0.1)))
  const avgCpc = totalClicks > 0 ? data.reduce((s, d) => s + d.spend, 0) / totalClicks : 0
  const beAcos = breakEvenAcos === null ? targetAcos * 1.6 : breakEvenAcos

  console.log(`\n# 投放诊断（${mode === 'placement' ? '广告位' : '搜索词'}）\n`)
  console.log(`- 数据行数：${data.length} | 总点击：${totalClicks} | 总订单：${totalOrders} | 数据 CVR：${(dataCvr * 100).toFixed(2)}%`)
  console.log(`- 平均 CPC：${avgCpc.toFixed(2)} | 目标 ACoS：${(targetAcos * 100).toFixed(0)}% | 盈亏平衡 ACoS：${(beAcos * 100).toFixed(0)}%${breakEvenAcos === null ? '（未提供，按目标 x1.6 估算）' : ''}`)

  const P0 = [], P1 = [], P2 = []

  if (mode !== 'placement') {
    for (const d of data) {
      if (d.clicks >= minClicks && d.orders === 0) {
        if (d.spend >= wasteMult * avgCpc * minClicks * 0.2 || d.spend >= wasteMult * avgCpc) {
          P0.push(`否定精确「${d.name}」${d.campaign ? `（${d.campaign}）` : ''}\n     依据：${d.clicks} 点击 / 0 单，花费 ${d.spend.toFixed(2)}，平均 CPC ${d.cpc.toFixed(2)}`)
          continue
        }
      }
      if (d.acos !== Infinity && d.acos > beAcos && d.clicks >= 20) {
        P0.push(`降价「${d.name}」-20%~-30%（当前 CPC ${d.cpc.toFixed(2)}）\n     依据：ACoS ${(d.acos * 100).toFixed(1)}% > 盈亏线 ${(beAcos * 100).toFixed(0)}%，点击 ${d.clicks}`)
        continue
      }
      if (d.orders >= 2 && d.acos !== Infinity && d.acos <= targetAcos) {
        P1.push(`收割：搜索词「${d.name}」新建 Exact${d.campaign ? `（来源 ${d.campaign}）` : ''}，原位置否定精确\n     依据：${d.orders} 单，ACoS ${(d.acos * 100).toFixed(1)}% <= 目标 ${(targetAcos * 100).toFixed(0)}%`)
        continue
      }
      if (d.acos !== Infinity && d.acos > targetAcos && d.acos <= beAcos && d.clicks >= 10) {
        P1.push(`微调降价「${d.name}」-10%~-15%\n     依据：ACoS ${(d.acos * 100).toFixed(1)}% 介于目标 ${(targetAcos * 100).toFixed(0)}% 与盈亏线 ${(beAcos * 100).toFixed(0)}% 之间`)
        continue
      }
      if (d.orders >= 1 && d.acos !== Infinity && d.acos <= targetAcos * 0.7) {
        P2.push(`提价「${d.name}」+10%~+20% 争取曝光\n     依据：ACoS ${(d.acos * 100).toFixed(1)}% <= 目标 x0.7，效率优秀`)
        continue
      }
      if (d.ctr !== null && d.ctr < 0.002 && d.impressions >= 1000) {
        P1.push(`检查主图/价格/相关性：「${d.name}」\n     依据：CTR ${(d.ctr * 100).toFixed(2)}% 偏低（曝光 ${d.impressions}），问题不在出价`)
      }
    }
  } else {
    const others = data.filter(d => d.clicks > 0)
    const allClicks = others.reduce((s, d) => s + d.clicks, 0)
    const allOrders = others.reduce((s, d) => s + d.orders, 0)
    const totalSpend = others.reduce((s, d) => s + d.spend, 0)
    for (const d of data) {
      const share = totalSpend > 0 ? d.spend / totalSpend : 0
      const oc = allClicks - d.clicks
      const oo = allOrders - d.orders
      const avgCvr = oc > 0 ? oo / oc : 0
      if (d.acos !== Infinity && d.acos > beAcos && share >= 0.3) {
        P0.push(`降「${d.name}」加价档位 / 必要时归零\n     依据：ACoS ${(d.acos * 100).toFixed(1)}% > 盈亏线，花费占比 ${(share * 100).toFixed(0)}%`)
      } else if (avgCvr > 0 && d.cvr >= avgCvr * 1.5 && (d.acos === Infinity ? false : d.acos <= beAcos)) {
        P1.push(`提「${d.name}」加价一档（如 +25%）\n     依据：CVR ${(d.cvr * 100).toFixed(2)}% >= 均值 ${(avgCvr * 100).toFixed(2)}% 的 1.5 倍，且 ACoS 可接受`)
      }
    }
  }

  function section(title, items) {
    if (!items.length) return
    console.log(`\n## ${title}（${items.length} 条）\n`)
    items.slice(0, 25).forEach((t, i) => console.log(`${i + 1}. ${t}`))
    if (items.length > 25) console.log(`\n... 另有 ${items.length - 25} 条，建议分批处理（单批 ≤ 总量 20%）`)
  }
  section('P0 — 立即处理（止血）', P0)
  section('P1 — 本周期调整（提效）', P1)
  section('P2 — 下周期观察（增长）', P2)
  if (!P0.length && !P1.length && !P2.length) console.log('\n未触发阈值。可能是数据量不足或当前表现健康 —— 不要为了动作而动作。')

  console.log(`\n---\n单次批量变更请控制在对象总量的 20% 以内；改前务必记录改前值以便回滚。`)
  console.log(`注意：脚本按阈值出候选动作，落盘前请结合学习期、库存、大促状态复核（见 references/diagnosis.md）。`)
}

// ---------------- keywords (Amazon 官方自动补全) ----------------
const SITES = {
  us: ['completion.amazon.com', 'ATVPDKIKX0DER'],
  uk: ['completion.amazon.co.uk', 'A1F83G8C2ARO7P'],
  de: ['completion.amazon.de', 'A1PA6795UKMFR9'],
  fr: ['completion.amazon.fr', 'A13V1IB3VIYZZH'],
  it: ['completion.amazon.it', 'APJ6JRA9NG5V4'],
  es: ['completion.amazon.es', 'A1RKKUPIHCS9HS'],
  jp: ['completion.amazon.co.jp', 'A1VC38T7YXB528'],
  ca: ['completion.amazon.ca', 'A2EUQ1WTGCTBG2'],
  au: ['completion.amazon.com.au', 'A39IBJ37TRP1C6'],
  in: ['completion.amazon.in', 'A21TJRUUN4KGV'],
  mx: ['completion.amazon.com.mx', 'AVDBXBAVVSXLQ'],
  br: ['completion.amazon.com.br', 'A2Q3Y263D00KWC'],
}
async function keywords() {
  const seed = opt('seed', null) || opt('q', null)
  if (!seed) throw new Error('keywords 需要 --seed <种子词>')
  const site = (opt('site', 'us') || 'us').toLowerCase()
  const siteCfg = SITES[site]
  if (!siteCfg) throw new Error('不支持的站点: ' + site + '（支持 ' + Object.keys(SITES).join('/') + '）')
  const [host, mid] = siteCfg
  const url = 'https://' + host + '/api/2017/suggestions?mid=' + mid + '&alias=aps&prefix=' + encodeURIComponent(seed)
  const ctl = new AbortController()
  const t = setTimeout(() => ctl.abort(), 15000)
  let j
  try {
    const r = await fetch(url, {
      headers: { 'User-Agent': 'Mozilla/5.0 (compatible; ads-opt/1.0; +local-agent-skill)', Accept: 'application/json' },
      signal: ctl.signal,
    })
    if (!r.ok) throw new Error('HTTP ' + r.status + '（该站点的补全端点可能不可用）')
    j = await r.json()
  } catch (e) {
    throw new Error('访问 ' + host + ' 失败（' + String(e.message || e) + '）。该站点的补全端点可能在当前网络不可达，请换站点或稍后重试。')
  } finally { clearTimeout(t) }
  const list = (j.suggestions || []).map(s => String(s.value || '').trim()).filter(Boolean)
  console.log('\n# 亚马逊自动补全建议词（站点 ' + site.toUpperCase() + '）\n')
  console.log('种子词：' + seed + ' | 返回 ' + list.length + ' 条\n')
  list.forEach((v, i) => console.log((i + 1) + '. ' + v))
  const brandish = list.filter(v => /\b(ninja|blendjet|zhenmi|philips|dyson|anker|bose|oxiaomi)\b/i.test(v))
  if (brandish.length) {
    console.log('\n提示：以下 ' + brandish.length + ' 条含品牌词 —— 投放竞品品牌词前先确认合规与预算容忍度：')
    brandish.forEach(v => console.log('  - ' + v))
  }
  if (!list.length) console.log('\n提示：该站点未返回补全词。请核对站点参数，或换用更基础的种子词重试。')
  console.log('\n注意：自动补全反映搜索热度，不代表转化。扩词后仍需用搜索词报告的 CVR 筛选。')
  console.log('明显无关的补全词可直接进否定清单（见 references/actions.md）。')
}

// ---------------- sqp (份额漏斗断崖定位) ----------------
const SQP_H = {
  term: ['term', '搜索词', '客户搜索词', 'search query', 'query', '关键词'],
  imp: ['impressionshare', '曝光份额', '品牌曝光份额', 'impression share', '品牌曝光占比'],
  clk: ['clickshare', '点击份额', '品牌点击份额', 'click share', '品牌点击占比'],
  cart: ['cartaddshare', '加购份额', '品牌加购份额', 'cart add share', '加购占比'],
  buy: ['purchaseshare', '购买份额', '品牌购买份额', 'purchase share', '品牌购买占比'],
  brand: ['brand', '品牌'],
  volume: ['searchqueryvolume', '搜索量', '该词搜索量', 'search query volume'],
}
function normPct(v) {
  const n = toNum(v)
  if (n === 0) return 0
  return n > 1.5 ? n / 100 : n
}
function sqp() {
  const file = opt('file', null)
  if (!file) throw new Error('sqp 需要 --file <SQP报告csv>')
  const raw = fs.readFileSync(file, 'utf8')
  let rows
  if (raw.trim().startsWith('[') || raw.trim().startsWith('{')) {
    const j = JSON.parse(raw)
    const arr = Array.isArray(j) ? j : (j.data || j.items || j.rows || [])
    const headers = [...new Set(arr.flatMap(o => Object.keys(o)))]
    rows = [headers, ...arr.map(o => headers.map(h => o[h]))]
  } else rows = parseDelimited(raw)
  if (rows.length < 2) throw new Error('文件里没有数据行')
  const headers = rows[0]
  const idx = {}
  for (const [field, alts] of Object.entries(SQP_H)) {
    for (const a of alts) {
      const na = normKey(a)
      let i = headers.findIndex(h => normKey(h) === na)
      if (i < 0) i = headers.findIndex(h => normKey(h).includes(na) && na.length >= 2)
      if (i >= 0) { idx[field] = i; break }
    }
  }
  if (idx.term === undefined) throw new Error('找不到搜索词列。现有列: ' + headers.join(' | '))
  const have = ['imp', 'clk', 'cart', 'buy'].filter(k => idx[k] !== undefined)
  if (have.length < 3) throw new Error('至少需要 3 个份额列（曝光/点击/加购/购买）。现有列: ' + headers.join(' | '))
  const stages = [['imp', '曝光'], ['clk', '点击'], ['cart', '加购'], ['buy', '购买']].filter(s => idx[s[0]] !== undefined)
  // 按列判断量纲：整列最大值 > 1.5 视为百分数（除以 100），否则视为 0~1 小数
  const scale = {}
  for (const [k] of stages) {
    const mx = Math.max(...rows.slice(1).map(r => toNum(r[idx[k]])))
    scale[k] = mx > 1.5 ? 100 : 1
  }
  const data = rows.slice(1).map(r => {
    const o = { name: String(r[idx.term] || '').trim() }
    for (const [k] of stages) o[k] = toNum(r[idx[k]]) / scale[k]
    return o
  }).filter(d => d.name)
  if (!data.length) throw new Error('没有有效数据行')
  // 汇总行（按份额均值）
  const avg = {}
  for (const [k] of stages) avg[k] = data.reduce((s, d) => s + d[k], 0) / data.length
  console.log('\n# SQP 份额漏斗分析\n')
  console.log('- 数据行数：' + data.length + ' | 环节：' + stages.map(s => s[1]).join(' → '))
  console.log('- 均值：' + stages.map(s => s[1] + ' ' + (avg[s[0]] * 100).toFixed(2) + '%').join(' | '))
  let maxDrop = { gap: -Infinity, from: '', to: '', fromLabel: '', toLabel: '' }
  for (let i = 0; i + 1 < stages.length; i++) {
    const a = stages[i], b = stages[i + 1]
    const gap = avg[a[0]] - avg[b[0]]
    if (gap > maxDrop.gap) maxDrop = { gap, from: a[0], to: b[0], fromLabel: a[1], toLabel: b[1] }
  }
  const FIX = {
    'imp->clk': ['被看到但没人点 —— 主图 / 价格 / 评分 / 标题问题', '不要加价：加价只会把更多钱烧在点不动的流量上。先修主图与定价，广告可先降预算止血。'],
    'clk->cart': ['点进来了但不想买 —— 详情页 / A+ / 五点 / 图文不符', '不要扩量：先修详情页与卖点表达，出价维持不加。'],
    'cart->buy': ['加购了但没下单 —— 价格 / 运费 / 优惠券 / 库存 / 配送时效', '不要怪广告：这是转化链路末端问题，广告应降价或暂停，等转化修好再放量。'],
  }
  const key = maxDrop.from + '->' + maxDrop.to
  console.log('\n## 断崖定位（相邻环节落差最大处）\n')
  if (FIX[key]) {
    console.log('**' + maxDrop.fromLabel + ' → ' + maxDrop.toLabel + ' 落差 ' + (maxDrop.gap * 100).toFixed(2) + ' 个百分点**')
    console.log('\n- 病因：' + FIX[key][0])
    console.log('- 动作：' + FIX[key][1])
  } else {
    console.log('曝光 → 点击 是整个漏斗的收窄处（落差 ' + (maxDrop.gap * 100).toFixed(2) + ' 个百分点）。曝光份额偏低通常意味着相关性 / 竞价 / 预算受限，进入广告层诊断。')
  }
  console.log('\n## 逐词份额明细（按最大落差排序）\n')
  console.log('| 搜索词 | ' + stages.map(s => s[1] + '份额').join(' | ') + ' | 最大落差处 |')
  console.log('|---|' + stages.map(() => '---').join('|') + '|---|')
  const scored = data.map(d => {
    let worst = { gap: -Infinity, label: '' }
    for (let i = 0; i + 1 < stages.length; i++) {
      const a = stages[i], b = stages[i + 1]
      const g = d[a[0]] - d[b[0]]
      if (g > worst.gap) worst = { gap: g, label: a[1] + '→' + b[1] }
    }
    return { d, worst }
  }).sort((x, y) => y.worst.gap - x.worst.gap)
  scored.slice(0, 25).forEach(({ d, worst }) => {
    console.log('| ' + d.name + ' | ' + stages.map(s => (d[s[0]] * 100).toFixed(2) + '%').join(' | ') + ' | ' + worst.label + ' (-' + (worst.gap * 100).toFixed(1) + 'pt) |')
  })
  if (scored.length > 25) console.log('\n... 另有 ' + (scored.length - 25) + ' 行')
  console.log('\n---')
  console.log('判读口诀：份额落差在哪一环，钱就不该花在广告上，而该花在那一环。')
  console.log('SQP 决定「该不该在这个词上花钱、该先修什么」；ACoS / 可接受 CPC 决定「花多少钱」。顺序不能颠倒。')
  console.log('注意：SQP 需品牌备案；品牌份额必须与同表全站值对比才有意义（见 references/sqp-framework.md）。')
}

try {
  if (cmd === 'calc') calc()
  else if (cmd === 'diagnose') diagnose()
  else if (cmd === 'keywords') await keywords()
  else if (cmd === 'sqp') sqp()
  else {
    console.log(`ads_opt.mjs — 亚马逊投放优化计算器 + 诊断器\n
用法:
  node ads_opt.mjs calc --price 39.99 --cost 8 --fba 7.5 --first-leg 3 \\
       --commission-rate 15 --return-rate 5 --target-margin 15 --cvr 8
  node ads_opt.mjs diagnose --file search-terms.csv --target-acos 25 --break-even-acos 40
  node ads_opt.mjs diagnose --file placement.csv --mode placement --target-acos 25

calc 参数:
  --price           售价（必需）
  --cost            产品成本
  --fba             FBA 配送费
  --first-leg       头程分摊每件
  --commission-rate 平台佣金率 % (默认 15)
  --return-rate     退货率 % (默认 0)
  --return-loss-rate 退货损失率 % (默认 100，即整单损失)
  --target-margin   目标净利率 % (默认 0)
  --cvr             转化率 % (给了才能算可接受 CPC)
  --currency        币种符号（如 USD/US$）

diagnose 参数:
  --file           CSV / JSON 文件（必需）
  --mode           searchterm(默认) | placement
  --target-acos    目标 ACoS % (默认 25)
  --break-even-acos 盈亏平衡 ACoS %（不填按目标 x1.6 估算并标注）
  --min-clicks     触发诊断的最小点击数（不填则按 1/CVR 自动推导，下限 5）
  --cvr            转化率 %（不填用数据自身 CVR）
`)
  }
} catch (e) {
  console.error('错误: ' + e.message)
  process.exit(1)
}






