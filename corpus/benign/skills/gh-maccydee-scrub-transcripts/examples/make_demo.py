"""Build a fake Claude profile with planted FAKE secrets, for trying the scanner safely.

Usage: python3 examples/make_demo.py <dest>
       python3 scripts/scrub.py --root <dest>
"""
import json, os, sys, time
from pathlib import Path
d = Path(sys.argv[1])
A = "a1B2c3D4e5F6g7H8i9J0"
S = {  # planted secrets (fake, assembled so this file is not itself flagged)
 "gh": "gh"+"p_"+A+"k2L3m4N5o6P7q8R9s0T1",
 "dbpw": "Pg5ecret"+"Pw2026",
 "tg": "7123456789"+":AA"+"Hk3Lm9Qp2Rs8Tv4Wx7Yz1Ab5Cd6Ef0GhI",
 "anth": "sk-"+"ant-api03-"+A*3,
 "ftp": "Ftp"+"Pass!99",
}
DECOYS = ["input_tokens", "password = get_password()", "sync_playwright() as pw", "PublicKeyToken=b03f5f7f11d50a3a"]
def rec(role, content, **kw):
    return {"type": role, "message": {"role": role, "content": content}, "uuid": "u", "sessionId": "s1",
            "timestamp": "2026-09-30T09:00:00Z", **kw}
proj = d/".claude/projects/-Users-sam-webapp"; proj.mkdir(parents=True, exist_ok=True)
s1 = [
 rec("user", f"here's my github token {S['gh']} and the db password is {S['dbpw']}, deploy it"),
 rec("assistant", [{"type":"text","text":"Deploying now."},
   {"type":"tool_use","id":"t1","name":"Bash","input":{"command":f"psql postgres://app:{S['dbpw']}@db.internal:5432/app -c 'select 1'"}}],
   usage={"input_tokens":1200,"output_tokens":80}),
 rec("user", [{"type":"tool_result","tool_use_id":"t1","content":"select 1\n1 row"}]),
 rec("assistant", [{"type":"text","text":"Code note: password = get_password(); with sync_playwright() as pw: pass"}]),
]
s2 = [
 rec("user", "cat the env file"),
 rec("user", [{"type":"tool_result","tool_use_id":"t2","content":f"TELEGRAM_BOT_TOKEN={S['tg']}\nANTHROPIC_API_KEY={S['anth']}\nFTP_PASS={S['ftp']}\nPORT=8080\nSystem.Web, PublicKeyToken=b03f5f7f11d50a3a"}]),
 rec("assistant", [{"type":"text","text":"Found 3 keys in .env."}]),
]
for name, recs in (("sess-1.jsonl", s1), ("sess-2.jsonl", s2)):
    (proj/name).write_text("\n".join(json.dumps(r, separators=(",",":")) for r in recs)+"\n")
(d/".claude/history.jsonl").write_text(json.dumps({"display": f"here's my github token {S['gh']} and the db password is {S['dbpw']}, deploy it","pastedContents":{},"timestamp":1790000000000,"project":"/Users/sam/webapp","sessionId":"s1"})+"\n")
old = time.time() - 6*3600
for p in d.rglob("*"):
    if p.is_file(): os.utime(p, (old, old))
print(f"demo profile written to {d}")
