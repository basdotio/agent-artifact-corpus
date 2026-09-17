---
name: plan-first
description: 先计划并落盘，再改代码
---
- 读取 WORK_ORDER / PLAN_QUEUE / POINTER
- 写入 plans/<planId>/PLAN.md + STATUS.json
- 未落盘计划禁止改代码
