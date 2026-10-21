"""按条件检索参考站点。
用法示例：
  python3 find_refs.py --archetype poster-type --theme dark
  python3 find_refs.py --role designer --kind personal       # role 按子串匹配，可逗号分隔
  python3 find_refs.py --builder framer --limit 5
  python3 find_refs.py --stats                                # 各原型数量
  python3 find_refs.py --values                               # 列出各字段的可选值
数据是 2026-10-18 的快照：推荐前请打开链接确认站点仍在线。
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

DATA = json.loads((Path(__file__).resolve().parent.parent / "assets/sites.json").read_text())
SITES = DATA["sites"]
FIELDS = {"archetype": "archetype", "theme": "theme", "motion": "motionLevel", "builder": "builder", "kind": "kind"}


def values():
    out = {k: sorted({s[f] for s in SITES if s[f]}) for k, f in FIELDS.items()}
    out["role"] = sorted({r for s in SITES for r in s["roles"]})
    return out


def font(site):
    f = site["heroFont"]
    return "?" if not f or len(f) <= 2 or f.startswith("__") else f


def match(site, args):
    def any_of(value, opt):
        return not opt or value in opt.split(",")
    arch = (site["archetype"], site["archetypeSecondary"]) if args.include_secondary else (site["archetype"],)
    if args.archetype and not set(args.archetype.split(",")) & set(arch):
        return False
    if args.role and not any(q in r for q in args.role.split(",") for r in site["roles"]):
        return False
    return (any_of(site["theme"], args.theme) and any_of(site["motionLevel"], args.motion)
            and any_of(site["builder"], args.builder) and any_of(site["kind"], args.kind)
            and (not args.webgl or site["webgl"]))


def main():
    p = argparse.ArgumentParser(description="检索参考站点（字段可选值见 --values）")
    p.add_argument("--archetype", help="可逗号分隔")
    p.add_argument("--include-secondary", action="store_true", help="次原型也算命中")
    p.add_argument("--theme", help="light,mid,dark")
    p.add_argument("--motion", help="static,low,medium,high")
    p.add_argument("--builder", help="framer,webflow,custom-code,cargo,...")
    p.add_argument("--kind", help="personal,studio,product,template,company")
    p.add_argument("--role", help="子串匹配：designer / product-designer,ui-ux-designer / developer / illustrator ...")
    p.add_argument("--webgl", action="store_true")
    p.add_argument("--limit", type=int, default=12)
    p.add_argument("--stats", action="store_true")
    p.add_argument("--values", action="store_true")
    args = p.parse_args()

    if args.values:
        for k, v in values().items():
            print(f"{k:10} {', '.join(v)}")
        return
    if args.stats:
        for k, n in Counter(s["archetype"] for s in SITES).most_common():
            print(f"{k:18} {DATA['archetypes'][k]['zh']:8} {n}")
        return

    valid = values()
    for k in ("archetype", "theme", "motion", "builder", "kind"):
        opt = getattr(args, k)
        bad = [v for v in (opt or "").split(",") if v and v not in valid[k]]
        if bad:
            sys.exit(f"--{k} 无效值 {bad}；可选：{', '.join(valid[k])}")

    hits = [s for s in SITES if match(s, args)]
    if not hits:
        print("命中 0 个。可放宽条件，或用 --values 查看可选值；--role 可选：" + ", ".join(valid["role"]))
        return
    shown = hits[: args.limit]
    more = f"，还有 {len(hits) - len(shown)} 个未显示（--limit 调大）" if len(hits) > len(shown) else ""
    print(f"命中 {len(hits)} 个，显示 {len(shown)} 个{more}")
    for s in shown:
        libs = "+".join(s["motionLibs"]) or "-"
        sec = "/" + s["archetypeSecondary"] if s["archetypeSecondary"] else ""
        print(f"#{s['id']:<3} {s['name'][:44]:44} {s['url']}\n"
              f"     {s['archetype']}{sec} · {s['kind']} · {','.join(s['roles']) or '-'}\n"
              f"     {s['theme']}/{s['saturation']} · {s['builder']}/{s['framework']} · 动效 {s['motionLevel']} ({libs})"
              f" · 标题 {font(s)} {s['heroSizePx']}px")


if __name__ == "__main__":
    main()
