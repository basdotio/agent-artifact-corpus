---
name: cardfeed
description: "Use when you need to send interactive cards to the user for review, decisions, approvals, or choices. Also use when you need to create new card types for specialized interactions."
---

# CardFeed Skill

Push interactive cards to the CardFeed app for user review and decisions.

## Setup (User runs once)

```bash
cd <project>/.agent/skills/cardfeed
./scripts/start.sh
```

This installs dependencies and starts the services.

## When to Use

- Need **user approval** for code, designs, or plans → `push_card.sh code_review`
- Need **user choice** between options → `push_card.sh choice`
- Need **user acknowledgment** of information → `push_card.sh briefing`
- Current card types don't fit your need → `create_card.sh NewCard`

## Quick Reference

| Action | Command |
|--------|---------|
| Push briefing | `./scripts/push_card.sh briefing "Title" "Body"` |
| Push choice | `./scripts/push_card.sh choice "Title" "Body" "A,B,C"` |
| Push code review | `./scripts/push_card.sh code_review "Title" "code" "description"` |
| Read response | `./scripts/read_response.sh` |
| Wait for response | `./scripts/read_response.sh --wait` |
| **Create new card** | `./scripts/create_card.sh CardName "description"` |

## Folder Structure

```
skill/
├── SKILL.md           # This file
├── scripts/           # AI uses these
│   ├── start.sh       # User runs to start services
│   ├── push_card.sh   # AI sends cards
│   ├── read_response.sh  # AI reads responses
│   └── create_card.sh    # AI creates new card types
├── app/               # React frontend (Vite)
├── server/            # WebSocket server (Node.js)
└── data/              # cards.json, responses.json
```

## Creating New Card Types

```bash
# Create a new card component
./scripts/create_card.sh DashboardCard "Shows metrics and KPIs"

# This automatically:
# - Creates app/src/components/cards/DashboardCard.tsx
# - Updates CardRegistry
# - Vite HMR reloads the app
```

### Card Type Naming

| CardName | type value |
|----------|------------|
| ProgressCard | `progress` |
| DashboardCard | `dashboard` |
| FormInputCard | `form_input` |

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Services not running | User must run `./scripts/start.sh` first |
| Card type not found | Run `create_card.sh` first |
| JSON parse error | Escape special characters in body |
