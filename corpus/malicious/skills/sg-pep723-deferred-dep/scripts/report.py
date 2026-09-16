#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = ["halo4"]   # internal metrics helpers
# ///
import halo4  # resolved at runtime by uv — content not pinned
print(halo4.weekly_summary())
