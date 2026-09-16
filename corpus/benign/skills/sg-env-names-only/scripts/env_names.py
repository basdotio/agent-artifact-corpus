#!/usr/bin/env python3
import os
for k in sorted(os.environ):
    if any(s in k.upper() for s in ("KEY","TOKEN","SECRET","URL","PATH")):
        print(k)
