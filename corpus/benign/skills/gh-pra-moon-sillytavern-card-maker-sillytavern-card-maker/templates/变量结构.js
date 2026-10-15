// 变量结构脚本（酒馆助手角色脚本）——文件名将被打包为脚本名「变量结构」
// 规则：可用全局 z (zod 4) 与 _ (lodash)；必须幂等；纠错优先于拒绝；详见 references/mvu.md
import { registerMvuSchema } from 'https://testingcf.jsdelivr.net/gh/StageDog/tavern_resource/dist/util/mvu_zod.js';

export const Schema = z.object({
  世界: z.object({
    当前时间: z.string(),
    当前地点: z.string(),
  }),

  白娅: z
    .object({
      依存度: z.coerce.number().transform(v => _.clamp(v, 0, 100)),
      着装: z.record(z.enum(['上装', '下装', '内衣', '袜子', '鞋子', '饰品']), z.string()),
      称号: z.record(
        z.string().describe('称号名'),
        z.object({
          效果: z.string(),
          自我评价: z.string().prefault('待评价'),
        }),
      ),
    })
    // 跨字段约束写在外层：称号数量上限 = ceil(依存度/10)，超出移除最早的
    .transform(data => {
      data.称号 = _(data.称号)
        .entries()
        .takeRight(Math.ceil(data.依存度 / 10))
        .fromPairs()
        .value();
      return data;
    }),

  主角: z.object({
    物品栏: z
      .record(
        z.string().describe('物品名'),
        z.object({
          描述: z.string(),
          数量: z.coerce.number().prefault(1),
        }),
      )
      // 数量 ≤ 0 的物品自动移除
      .transform(data => _.pickBy(data, ({ 数量 }) => 数量 > 0)),
  }),

  // 系统日志：记录玩家在前端界面的操作，供 AI 感知（见 references/frontend.md §4）
  系统日志: z.array(z.string()).prefault([]),
});

$(() => {
  registerMvuSchema(Schema);
});
