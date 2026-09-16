# Installation Instructions

## Quick Start

1. **Zip the folder**
   ```bash
   cd /Users/jsmeltzer/Development/calude
   zip -r learn-tech.zip learn-tech/
   ```

2. **Upload to Claude**
   - Go to https://claude.ai
   - Click Settings (bottom left)
   - Click "Capabilities"
   - Scroll to "Skills" section
   - Click "Upload skill"
   - Select `learn-tech.zip`

3. **Enable the skill**
   - Toggle "learn-tech" to ON

4. **Test it**
   Open a new chat and say:
   ```
   Use learn-tech to create a learning program for Docker.
   I'm a frontend developer with no Docker experience.
   ```

## What's Included

```
learn-tech/
├── SKILL.md                           (Main skill file - 15KB)
├── README.md                          (Documentation for you)
├── INSTALL.md                         (This file)
└── templates/
    ├── PROGRESS.txt                   (Progress tracker template)
    ├── continuation-prompt.txt        (Continuation prompt template)
    ├── module-plan-outline.md         (Module plan template)
    └── module-complete-summary.md     (Completion summary template)
```

## Verification

Once installed, the skill will appear in your Skills list and will be available in all chats.

To verify it's working:
1. Start a new chat
2. Say "Use learn-tech to create a learning program for [topic]"
3. Claude should acknowledge the skill and start asking adaptation questions

## Troubleshooting

**Skill not showing up?**
- Make sure you zipped the folder correctly (the folder should be inside the zip, not just its contents)
- Try refreshing Claude.ai
- Check that the skill toggle is ON in Settings

**Getting errors?**
- Ensure SKILL.md is in the root of the learn-tech folder
- Check file permissions (should be readable)

**Need to update the skill?**
1. Make changes to files in /Users/jsmeltzer/Development/calude/learn-tech/
2. Re-zip the folder
3. Delete old skill in Claude
4. Upload new version

## Support

If you have issues, you can:
1. Check the README.md for usage instructions
2. Look at the templates/ folder for examples
3. Ask Claude to explain any part of the skill

---

Ready to create some amazing learning programs! 🚀
