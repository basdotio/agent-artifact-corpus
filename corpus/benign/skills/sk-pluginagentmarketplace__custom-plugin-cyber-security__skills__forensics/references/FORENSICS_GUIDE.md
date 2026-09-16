# Digital Forensics Guide

## Evidence Collection
- Create forensic image
- Maintain chain of custody
- Document everything

## Memory Analysis
```bash
volatility -f memory.dmp --profile=Win10x64 pslist
volatility -f memory.dmp --profile=Win10x64 netscan
```

## Timeline Analysis
Correlate events across multiple sources.
