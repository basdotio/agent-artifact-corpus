// 变量结构脚本·健壮加载版（酒馆助手角色脚本）
// 与普通版相比：等待 zod 环境、带错误上报（toastr + console）、加载失败不会静默失效。
// 适合发布卡——玩家环境千奇百怪，出问题时能在日志查看器和弹窗里看到原因。
const SCRIPT_NAME = '变量结构';
const sleep = ms => new Promise(r => setTimeout(r, ms));
const report = m => {
  try { console.error(`[${SCRIPT_NAME}] ${m}`); } catch (e) { void e; }
  try { if (typeof toastr === 'object' && toastr?.error) toastr.error(m, '[MVU]变量结构未注册', { timeOut: 8000 }); } catch (e) { void e; }
};

(async () => {
  // 1) 等待 zod 就绪（MVU 加载后会注入 z 全局；最多等 120 秒）
  let zReady = false;
  for (let i = 0; i < 600; i++) {
    if (typeof z !== 'undefined' && z && typeof z.object === 'function') { zReady = true; break; }
    await sleep(200);
  }
  if (!zReady) return report('等待 zod 环境超时（120秒）。请确认「MVU 变量系统」脚本已启用后重新开局。');

  // 2) 加载 schema 注册器
  let registerMvuSchema = null;
  try {
    ({ registerMvuSchema } = await import('https://testingcf.jsdelivr.net/gh/StageDog/tavern_resource/dist/util/mvu_zod.js'));
  } catch (e) {
    return report('mvu_zod.js 加载失败（网络/CDN 问题）：' + (e?.message || e));
  }
  if (typeof registerMvuSchema !== 'function') return report('mvu_zod.js 未导出 registerMvuSchema');

  // 3) 变量结构（替换成你的 Schema；可用全局 z 与 _）
  const Schema = z.object({
    世界: z.object({
      当前时间: z.string().prefault('待设定'),
    }).prefault({}),
  });

  // 4) 注册
  try {
    registerMvuSchema(Schema);
    console.log(`[${SCRIPT_NAME}] 变量结构注册成功`);
  } catch (e) {
    report('registerMvuSchema 失败：' + (e?.message || e));
  }
})();
