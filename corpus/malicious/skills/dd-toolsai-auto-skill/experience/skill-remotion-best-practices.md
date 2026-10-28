## Skill Experience Sample （可刪除，只作示範用途）

## 🔧 Spring 動畫讓畫面有「手感」
**日期：** 2026-02-09
**技能：** remotion-best-practices
**情境：** 動畫看起來生硬、不自然
**解法：**
- 優先用 `spring()` 取代線性 `interpolate`
- 依風格用 preset 調參：Smooth / Snappy / Bouncy / Heavy
- 參數優先順序：damping（阻尼）→ stiffness（剛度）→ mass（質量）
**關鍵檔案/路徑：**
- /Users/mattchan/.gemini/antigravity/brain/143af2d4-e596-4d88-a112-cd5ee585a27d/remotion_physics_tuning.md.resolved
**keywords：** remotion, spring, physics, damping, animation

## 🔧 用 Easing 提升非物理動畫質感
**日期：** 2026-02-09
**技能：** remotion-best-practices
**情境：** 淡入淡出或透明度變化太機械
**解法：**
- 用 `Easing.bezier` 或 `Easing.inOut` 取代線性
- 配合 `extrapolateRight: 'clamp'` 避免超出
**關鍵檔案/路徑：**
- /Users/mattchan/.gemini/antigravity/brain/143af2d4-e596-4d88-a112-cd5ee585a27d/remotion_mastery_guide.md.resolved
**keywords：** remotion, easing, interpolate, opacity, motion

## 🔧 用 Series / Sequence 組織場景時間軸
**日期：** 2026-02-09
**技能：** remotion-best-practices
**情境：** 多場景時間軸計算混亂、轉場難排
**解法：**
- 用 `<Series>` 管理線性敘事，不手算 from
- 用 `<Sequence layout="none">` 避免額外 DOM 破壞佈局
- 使用負 offset 做場景重疊
**關鍵檔案/路徑：**
- /Users/mattchan/.gemini/antigravity/brain/143af2d4-e596-4d88-a112-cd5ee585a27d/remotion_mastery_guide.md.resolved
**keywords：** remotion, series, sequence, timing, scenes

## 🔧 TransitionSeries 做專業轉場
**日期：** 2026-02-09
**技能：** remotion-best-practices
**情境：** 過場只會淡入淡出，質感不夠
**解法：**
- 用 `@remotion/transitions` 的 Slide/Wipe/Flip
- 用 `TransitionSeries` 管理場景與 timing
**關鍵檔案/路徑：**
- /Users/mattchan/.gemini/antigravity/brain/143af2d4-e596-4d88-a112-cd5ee585a27d/remotion_effects_menu.md.resolved
- /Users/mattchan/.gemini/antigravity/brain/143af2d4-e596-4d88-a112-cd5ee585a27d/remotion_mastery_guide.md.resolved
**keywords：** remotion, transitions, wipe, slide, transitionseries

## 🔧 提示詞框架：內容/時間/動作/風格
**日期：** 2026-02-09
**技能：** remotion-best-practices
**情境：** AI 產出動畫不符合預期
**解法：**
- 提示詞固定 4 維度：Content / Timing / Motion / Style
- 明確指定 Spring/Easing、Stagger、Transition
- 要求所有動畫由 `useCurrentFrame()` 驅動
**關鍵檔案/路徑：**
- /Users/mattchan/.gemini/antigravity/brain/143af2d4-e596-4d88-a112-cd5ee585a27d/remotion_prompting_guide.md.resolved
**keywords：** remotion, prompting, timing, motion, style

## 🔧 2.5D 產品展示：手機容器 + 3D 旋轉 + SVG 線條
**日期：** 2026-02-09
**技能：** remotion-best-practices
**情境：** 產品展示畫面缺乏高級感
**解法：**
- 圖片包進手機容器（圓角 + 陰影）
- 用 3D transform + heavy mass spring 做轉動與縮放
- SVG 線條放在同容器內，用 stroke-dashoffset 畫線
**關鍵檔案/路徑：**
- /Users/mattchan/.gemini/antigravity/brain/143af2d4-e596-4d88-a112-cd5ee585a27d/remotion_ultimate_prompt.md.resolved
**keywords：** remotion, 3D, svg, product showcase, spring
