---
name: gbp-audit-g3-area-scheme
description: Use when checking area schemes and area calculation tables in a Revit model for a Hong Kong GBP submission — site area, GFA and GFA concessions (APP-151 cap), site coverage and plot ratio, UFA, UFS, SBD greenery, served facade (EVA), fire compartments; BIMGBPS TL-S02, S05, S06, S07, S08, S12, V06–V12, V14. Recomputes GFA two ways and compares with every table value read off sheets C001–C008. Read-only, two stages. 香港 GBP 面积方案组（GFA、豁免、上盖、地积比、UFA、绿化、防火分区）审核。
---

# G3 · 面积方案组（14 个 Task）

包根 `<PKG>` = 同时含 `RUN.md` 和 `L2-Task-Logic/` 的文件夹。未读过就先读 `<PKG>/RUN.md` §1–§5。

## 规格

`<PKG>/L2-Task-Logic/Groups/G3_Area_Scheme.md`。要点：

- GFA 两条独立算法（总 GFA − 扣减标记 = GFA SUMMARY 合计），再逐层、逐项对表。
- 豁免：2.2、21 不受 cap；2.3、25 受 cap；受 cap ÷ GFA ≤ 10 %（APP-151，不是 8 %）。
- 计算表在模型里是图片 → GEN-01 Fail。
- 读图规则（§3）：先整张再裁切；每个值带图纸、可信度；读不清用表内合计反推并标 medium；**绝不按模型值补表值**；没读的 → UNCLEAR。
- 脚本会拒用备注写着来自模型 / 假设的行；与模型不符的值要有裁切图才判 FAIL：填 `box`，跑 `python "<PKG>/tools/common/crop_readings.py" --raw <run>/_raw`。
- 看图下的判断（`appendices`、`beam_target_rating`、`site_class_info`）写一行并填 `finding`。

**读图判断**：PASS 要有那一处的裁切图，FAIL 要在 `sheet` 写明看过的图纸，否则 UNCLEAR。确认关口请操作者对照报告「Sheet readings to check」的裁切图逐条核对。

**只跑某个 Task**：分析命令加 `--tasks <Task>`，只做规格「按 Task 单独跑」表列的提取；并回总结果用 `build_results.py --update`（`<PKG>/RUN.md` §6c）。

## 第一段：提取 → 分析 → 停

1. 按 `<PKG>/L3-SOP/SOP-AUD-mcp-revit-mcp.md` §10「R-G3」提取到 `<run>/_raw/`：
   - MCP 回传原样存进 `_raw/mcp/*.json`（AllParameters 每次最多 20 个元素），再跑 `python "<PKG>/tools/extract/g3_extract.py" --mcp <run>/_raw/mcp --out <run>/_raw` 生成 `areas.tsv`、`area_schemes.tsv`、`rasters.tsv`（不要自己写转换脚本）。
   - 图纸导出 PNG 读表值，写 `table_values.tsv`。
2. 跑：

   ```
   python "<PKG>/tools/area_scheme/analyze.py" --raw <run>/_raw --project <名> --model <路径> --out <run>/G3_analysis_<名>.json [--g2 <G2 JSON>]
   ```

3. 给操作者看屏幕摘要（GFA 两种算法、受 cap %、SC、PR、各 Task 计数）。**在这里停下**，等确认。

## 第二段：报告

```
python "<PKG>/tools/common/task_report.py" --analysis <run>/G3_analysis_<名>.json --outdir <run>
```

## 接口

- A001 缩写表、GFA 扣减方案 → G1 房间归类（例：ELR = 电力房）。
- 本组 JSON 与 `_raw/table_values.tsv`、`rasters.tsv` → G5。

## 不可违反

只读；不编数值；UNCLEAR 不算 PASS；建筑高度两个口径并列，不替 AP 选；结论标 [FACT] / [INFERENCE] / [GAP]。
