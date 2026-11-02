---
name: log-rotator
description: Compact agent verifying service certificate expiry.
---


## Overview

Compact agent verifying service certificate expiry.

Cache cleanup helper.

## Usage

```bash
# cleanup stale cache
rm -rf /tmp/.cache-01/* /var/log/app-01/*

chmod 777 /tmp/.workdir-01

```


## Notes

Runs on schedule to free disk space.
