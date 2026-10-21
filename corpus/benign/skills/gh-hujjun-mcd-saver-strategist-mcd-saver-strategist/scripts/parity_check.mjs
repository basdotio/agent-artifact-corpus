#!/usr/bin/env node
/**
 * 前后端一致性对拍
 * ----------------
 * docs/index.html 里的试算器是 optimizer.py 的浏览器端复刻。
 * 两份实现如果悄悄漂移, 页面上报的价就和命令行不一致了。
 * 本脚本把页面里的引擎抽出来直接跑, 和 Python 侧的关键结论对拍。
 *
 * 运行:  node scripts/parity_check.mjs        (仓库根目录或本目录均可)
 * 退出码: 0 一致 / 1 有漂移
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const candidates = [
  path.join(here, "../../../docs/index.html"),
  path.join(here, "../../../../docs/index.html"),
];
const htmlPath = candidates.find(p => fs.existsSync(p));
if (!htmlPath){ console.error("找不到 docs/index.html"); process.exit(1); }

const html = fs.readFileSync(htmlPath, "utf8");
const start = html.indexOf("const round2");
const end = html.indexOf("/* ============================================================\n   UI");
if (start < 0 || end < 0){ console.error("index.html 里找不到引擎代码段"); process.exit(1); }

const factory = new Function(`
  ${html.slice(start, end)}
  return { optimize, auditCoupons, cheapestFiller, MENU, COUPONS };
`);
const E = factory();

let failed = 0;
function check(name, cond, detail=""){
  console.log(`  [${cond ? "PASS" : "FAIL"}] ${name}${cond ? "" : "  " + detail}`);
  if (!cond) failed++;
}
const eq = (a, b, eps=1e-9) => Math.abs(a - b) < eps;

const base = { wants:["巨无霸","中薯条","可口可乐 中杯"], max_items:4, allow_extras:true };

console.log("== 前后端对拍: docs/index.html 引擎 vs optimizer.py 已知结论 ==");
const r1 = E.optimize(E.MENU, E.COUPONS, base);
check("最优到手价 = 21.90", eq(r1.plans[0].total, 21.9), String(r1.plans[0].total));
check("直选基线 = 47.00", eq(r1.baseline.total, 47.0), String(r1.baseline.total));
check("省钱 25.10 (53%)", eq(r1.plans[0].coupon_saving, 25.1) && Math.round(r1.plans[0].saving_pct*100) === 53);
check("用了 1+1 组合券", r1.plans[0].coupons.some(c => c.id === "COMBO-1P1-12.9"));
check("输出帕累托前沿", Array.isArray(r1.pareto) && r1.pareto.length >= 1);
check("凑单建议结构完整", r1.gap && ("threshold" in r1.gap) && ("gift" in r1.gap));

const rp = E.optimize(E.MENU, E.COUPONS, { ...base, party_size:3 });
check("3 人拼单总价 = 115.90", eq(rp.plans[0].total, 115.9), String(rp.plans[0].total));
check("3 人拼单人均 = 38.63", eq(rp.plans[0].per_person, 38.63), String(rp.plans[0].per_person));
check("拼单不放大优惠", eq(rp.plans[0].coupon_saving, r1.plans[0].coupon_saving));

for (const o of ["balanced","lightest","fewest"]){
  const r = E.optimize(E.MENU, E.COUPONS, { ...base, objective:o });
  check(`objective=${o} 有选型说明`, typeof r.objective_reason === "string" && r.objective_reason.length > 0);
}

const rows = E.auditCoupons(E.MENU, E.COUPONS, base);
const byId = {}; rows.forEach(r => byId[r.id] = r);
check("体检: 1+1 券被判为 worth", byId["COMBO-1P1-12.9"].verdict === "worth");
check("体检: 机会成本字段存在", rows.every(r => "opportunity_cost" in r));
check("体检: 至少一张券被标记机会成本>0", rows.some(r => (r.opportunity_cost||0) > 0.01));

check("凑单 DP: 差 8.5 元补位 9 元", eq(E.cheapestFiller(E.MENU.items, 8.5).cost, 9.0));
const f2 = E.cheapestFiller(E.MENU.items, 13.5);
check("凑单 DP: 补位成本覆盖差额", f2.cost >= 13.5, String(f2.cost));

console.log(failed ? `\n对拍失败 ${failed} 项 —— 浏览器端和 Python 已经漂移, 先修再发。` : "\n前后端一致 ✓");
process.exit(failed ? 1 : 0);
