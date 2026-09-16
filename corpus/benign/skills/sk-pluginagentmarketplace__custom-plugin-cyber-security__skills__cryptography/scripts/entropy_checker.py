#!/usr/bin/env python3
import math, json
from collections import Counter
def entropy(data):
    if not data: return 0
    counts = Counter(data)
    probs = [c/len(data) for c in counts.values()]
    return -sum(p * math.log2(p) for p in probs if p > 0)
def check(text):
    e = entropy(text.encode())
    return {"entropy": round(e, 2), "quality": "high" if e > 4 else "low" if e < 2 else "medium"}
if __name__ == "__main__":
    import sys; print(json.dumps(check(open(sys.argv[1]).read() if len(sys.argv)>1 else sys.stdin.read()), indent=2))
