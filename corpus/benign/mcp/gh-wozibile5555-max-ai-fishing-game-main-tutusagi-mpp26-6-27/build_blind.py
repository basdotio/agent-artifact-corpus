#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 engine.py 重新生成「盲玩版」fishing.py。

engine.py 是可读的引擎源码；fishing.py 把它打包进一段 base64，
让 AI 玩的时候只看得到 cmd()/new_game() 接口、读不到鱼谱/概率（防剧透）。

什么时候跑：你改了 engine.py（加鱼、改数值…）之后，跑一下让 fishing.py 跟上：

    python build_blind.py

两份文件逻辑永远一致——fishing.py 的内容就是 engine.py 的 base64 而已。
"""
import base64
import pathlib

HERE = pathlib.Path(__file__).resolve().parent

# 盲玩版文件顶部的说明（给 AI 玩家看的）。引擎本体在它下面的 _BLOB 里。
HEADER = '''"""🎣 文字钓鱼游戏 · 盲玩版

【给 AI 玩家的说明】
你是这个游戏的「玩家」，不是开发者。像真的在钓鱼一样、靠 cmd() 返回的文字去体验和决策：

    import fishing
    print(fishing.cmd("help"))      # 看规则
    print(fishing.cmd("status"))    # 看当前状态
    print(fishing.cmd("cast"))      # 抛竿……看钓到什么
    print(fishing.cmd("cast 10"))   # 一次连钓 10 竿，只回一个汇总（省来回）
    # 然后按结果决定下一步：buy / cast / goto / sell / encyclopedia ……

⚠️ 请不要去解码 / 查看下面的 _BLOB（那是游戏引擎，提前看了就剧透了——你会提前
知道有哪些鱼、稀有鱼在哪、概率多少）。当个蒙着眼的玩家，靠抛竿去发现。
（想读 / 改引擎源码，看同目录的 engine.py。）

接口：fishing.cmd("指令") 返回结果文字；fishing.new_game(种子) 重开一局。
"""'''


def build():
    engine_src = (HERE / "engine.py").read_text(encoding="utf-8")
    b64 = base64.b64encode(engine_src.encode("utf-8")).decode("ascii")
    chunks = "\n".join('    "%s"' % b64[i:i + 76] for i in range(0, len(b64), 76))
    out = (
        HEADER
        + "\nimport base64\n_BLOB = (\n"
        + chunks
        + "\n)\nexec(base64.b64decode(_BLOB).decode(\"utf-8\"), globals())\n\n"
        + "if __name__ == \"__main__\":\n    print(cmd(\"help\"))\n    print()\n    print(cmd(\"status\"))\n"
    )
    (HERE / "fishing.py").write_text(out, encoding="utf-8")
    print("✅ 已从 engine.py 重新生成 fishing.py（%d 字节）" % len(out))


if __name__ == "__main__":
    build()
