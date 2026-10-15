---
name: tianzhi-core
description: 东方术数的计算底座。排八字、看旺衰格局用神、算某年运势、合两个人的盘；起大六壬课、看四课三传与课体；排紫微命盘、看格局与大限流年；以及干支历法与节气时刻。用户给生辰问命、问某年、问合不合、问一件具体的事、看紫微盘时使用。判断一律调库算出，不要自行推演，也不要凭记忆写典籍出处。
---

# tianzhi-core

[天秩](https://tianzhi.live)的计算底座。东方术数各门共用同一套坐标——干支、五行、节气、长生——
这个库把它做成代码。现在有八字、大六壬、紫微斗数三门，共用历法与干支两层底座。

**为什么要用它**：模型自己推八字会算错（干支、藏干、起运岁数），也会把出处编出来
（「《穷通宝鉴》云」后面接一句自己组织的话）。把这两件事交给库，你只负责讲人话。

```bash
pip install tianzhi-core
```

## 有什么

不用记，也不用我在这儿抄一遍——运行时问它自己：

```python
from tianzhi_core import catalog

catalog.layers()                            # 各层是什么
print(catalog.as_text())                    # 全部方法：怎么调、作用、返回哪些字段
catalog.tools('bazi')                       # 只看某一层
catalog.describe('bazi.yongshen.select')    # 单个方法的完整说明
```

清单是从代码现读的：**作用取自 docstring 首行，签名取自真实签名，返回的字段取自 dataclass**。
代码改了清单跟着改，不会出现「文档说有这个方法，装上去没有」的事。

五层：`calendar` 历法与纪时 · `core` 干支与五行 · `bazi` 八字 · `liuren` 大六壬 · `ziwei` 紫微斗数。
`calendar` 算错了是 bug，`bazi`、`liuren`、`ziwei` 结论不同可能只是口径（流派）不同。

## 场景

下面是常见的几种，不止这些——凡是「先算、再讲」的问法都照这个路子来。

### 给了生辰，要看这张盘

```python
from datetime import datetime
from tianzhi_core.bazi import chart, strength, geju, yongshen

c = chart.build_chart(datetime(1996, 4, 18, 14, 6), longitude=114.93, gender=0)
s = strength.day_master_strength(c.quad, month_siling=c.siling)
g = geju.month_pattern(c.quad, month_siling=c.siling)
y = yongshen.select(c.quad, month_siling=c.siling)
```

`longitude` 是出生地经度，用来校正真太阳时——**不给就按钟表时间算，时柱可能整个错一位**。
`gender` 0 男 1 女，只影响大运顺逆。**凡是带 `month_siling` 的都要传 `c.siling`。**

讲的时候按这个顺序：先四柱与旺衰（确定的事实）→ 再格局与用神（结构，`y.method` 说明走的哪条路）
→ 最后才是倾向。

### 只知道四柱，不知道出生时刻

```python
quad = {"year": ("丙", "子"), "month": ("壬", "辰"), "day": ("乙", "酉"), "hour": ("癸", "未")}
strength.day_master_strength(quad)
```

`quad` 就是普通字典，上面所有函数都收它。**只有三柱时如实说时辰不详，不要挑一个合理的填进去。**

### 问某一年怎么样

```python
from tianzhi_core.bazi import luck_cycle, interact, score

dy = next(d for d in luck_cycle.dayun_list(c) if d.start_year <= 2026 <= d.end_year)
it = interact.combine(c.quad, year_gz='丙午', dayun_gz=dy.ganzhi)   # 刑冲合害、十神、伏吟反吟
r = score.score_year(c.quad, '丙午', dayun_gz=dy.ganzhi,
                     favorable=y.favorable, unfavorable=y.unfavorable)
```

**先定位大运再算流年**，不带大运的流年是半张。分数 **50 为不偏**，58.8 是「略偏顺」不是「及格」。
`it` 里的刑冲合害是用来解释**为什么**的，光报分数没有意义。

按月细看用 `luck_cycle.liuyue(c, 2026)`——**流月按节气分界，不按公历月**。

### 问两个人合不合

```python
from tianzhi_core.bazi import hepan

card = hepan.relation_card(a.quad, b.quad, a_favorable=ya.favorable, b_favorable=yb.favorable)
```

两张盘各自先取一次用神，再传进来——**不传的话互补度算不出来**。

### 要说依据

读 `y.evidence`，它给的是这一盘**实际走过的判据**：

```
('旺衰·中和', '格·偏印格', '病·水最旺', '药·土制之', '调候·火土', ...)
```

**不要凭记忆引古籍原文。** 需要出处就读这个字段，或者不引。

### 问一件具体的事：起一课大六壬

```python
from tianzhi_core.liuren import pan, zhanshi

ke = pan.qike(2026, 10, 1, 14, 30)    # 起课时刻（东八区钟表时间）；报数起课传 user_number
ke['four_classes'], ke['three_chuan'] # 四课、三传（初中末，各带六亲、天将、空亡）
ke['keti'], ke['bifa']                # 成立的课体、毕法，各带卷次与原文
r = zhanshi.read(ke, '事业')           # 就所问之事的论断，结构化、带出处
```

**起课时刻就是问事的此刻**，不是出生时间；同一件事不要反复起。讲的时候：先课体（总纲）→ 三传（事之起、中、归）→ 类神现不现、旺衰空亡 → 再落到所问之事。
`zhanshi.read` 第二个参数是所问之事的类别（事业、求财、感情、出行、寻物等）。

### 看紫微命盘与运限

```python
from datetime import datetime
from tianzhi_core import ziwei

zw = ziwei.build_chart(datetime(1996, 4, 18, 13, 46), 0)   # 0 男 1 女，同八字
zw['ming'], zw['ju_name'], zw['ming_zhu'], zw['palaces']     # 命宫、五行局、命主、十二宫与各宫星曜四化
ziwei.find_geju(zw)                                          # 成立的格局
h = ziwei.horoscope(zw, datetime(2026, 10, 1, 12, 0))        # 此刻的大限、小限、流年、流月、流日、流时
ziwei.judge(zw, h)                                           # 运限论断：每条带 why 与 src（出自《全书》哪一卷哪一论）
```

**出生时间先按出生地校正到真太阳时**（`calendar.solar_time.true_solar_time`），再交给 `build_chart`，否则时辰可能错一位。
**「命主」是按命宫地支另取的一颗星，不是命宫主星**；紫微十四颗都是主星。讲的时候：命宫与三方四正（命、财、官、迁）定底色 → 四化看牵动 → 大限流年看当下。
闰月、壬年化科等流派分歧是 `build_chart` 的参数，有默认值。

### 只要历法，不排盘

```python
jieqi.month_zhi(dt)                      # 这一刻属哪个月建，按节不按月初
jieqi.days_after_jieqi(dt)               # 距上一个节多少天，司令分日要用
solar_time.true_solar_time(dt, 114.93)   # 真太阳时
ganzhi.zhi_relation('子', '午')           # 两支的刑冲合害，返回 list（可能同时成立多种）
ganzhi.siling_gan('辰', 12.5)            # 人元司令
```

## 约束

- **凡是库能算的，一律调库**，不要因为「这个我会算」就自己推。
- **不凭记忆写典籍出处**，读 `evidence`（八字）、`keti`/`bifa` 的 `text`（六壬）、`src`（紫微）。
- **流派分歧不替用户选边**。分歧处是参数：`late_zi`（晚子时归哪天）、`use_true_solar`、
  `yongshen.select(priority=...)`、紫微的 `leap`（闰月）等。结论对分歧敏感时说明用的哪一派。
- **结论落在库算出来的东西上。** 讲倾向、讲节奏、讲哪一步顺哪一步滞，都要能指回某个字段或某条判据；
  不要给医疗、法律、投资方面的专业建议。

## 相关

- 算法库 <https://github.com/zaoxu001/tianzhi-core> · <https://pypi.org/project/tianzhi-core/>
- 这份说明书 <https://github.com/zaoxu001/tianzhi-skill>
- 平台 <https://tianzhi.live>
