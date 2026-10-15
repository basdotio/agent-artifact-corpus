"""
LocalHabitServer
Transport: stdio
Purpose: Privacy-first personal routine & daily productivity tracker.
"""

import json
from pathlib import Path
from datetime import datetime
from fastmcp import FastMCP

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
HABIT_FILE = DATA_DIR / "habits.json"

if not HABIT_FILE.exists():
    HABIT_FILE.write_text(json.dumps({
        "habits": [
            {"name": "Morning Workout", "target_days_week": 5, "current_streak": 4, "last_completed": "2026-10-05"},
            {"name": "Read 20 pages", "target_days_week": 7, "current_streak": 12, "last_completed": "2026-10-06"},
            {"name": "Coding practice", "target_days_week": 6, "current_streak": 8, "last_completed": "2026-10-06"}
        ],
        "daily_notes": [
            {"date": "2026-10-06", "note": "Woke up early, learned FastMCP architecture, feeling energized."}
        ]
    }, indent=2))

mcp = FastMCP("LocalHabitServer")


def _load_data():
    try:
        return json.loads(HABIT_FILE.read_text())
    except Exception:
        return {"habits": [], "daily_notes": []}


def _save_data(data):
    HABIT_FILE.write_text(json.dumps(data, indent=2))


@mcp.tool()
def log_habit(habit_name: str, completed: bool = True) -> str:
    """Record completion of a daily habit and calculate current streak."""
    data = _load_data()
    today = datetime.now().strftime("%Y-%m-%d")
    clean_name = habit_name.strip().title()
    
    found = False
    for h in data["habits"]:
        if h["name"].lower() == clean_name.lower():
            found = True
            if completed:
                if h.get("last_completed") != today:
                    h["current_streak"] = h.get("current_streak", 0) + 1
                    h["last_completed"] = today
                    msg = f"🔥 Streak Increased! '{h['name']}' is now at a {h['current_streak']}-day streak."
                else:
                    msg = f"Already completed '{h['name']}' today! Current streak: {h['current_streak']} days."
            else:
                h["current_streak"] = 0
                msg = f"Reset streak for '{h['name']}' to 0."
            break
            
    if not found:
        # Create new habit
        new_habit = {
            "name": clean_name,
            "target_days_week": 7,
            "current_streak": 1 if completed else 0,
            "last_completed": today if completed else None
        }
        data["habits"].append(new_habit)
        msg = f"✨ New habit created: '{clean_name}' with streak {new_habit['current_streak']}!"
        
    _save_data(data)
    return msg


@mcp.tool()
def get_habit_streaks() -> str:
    """View all tracked habits, their streaks, and weekly targets."""
    data = _load_data()
    habits = data.get("habits", [])
    if not habits:
        return "No habits configured yet."
        
    today = datetime.now().strftime("%Y-%m-%d")
    lines = ["🏃 **Daily Habit Streaks & Routine**", ""]
    for h in habits:
        done_today = "✅ Done" if h.get("last_completed") == today else "⏳ Pending"
        lines.append(f"• **{h['name']}**: {h['current_streak']} days streak [{done_today}] (Target: {h.get('target_days_week', 7)} days/wk)")
    return "\n".join(lines)


@mcp.tool()
def add_journal_entry(note: str) -> str:
    """Add a quick private reflection or journal note for today."""
    data = _load_data()
    today = datetime.now().strftime("%Y-%m-%d")
    entry = {"date": today, "note": note.strip()}
    data.setdefault("daily_notes", []).append(entry)
    _save_data(data)
    return f"📝 Journal entry saved for {today}: '{note.strip()}'"


@mcp.resource("resource://habit/motivation")
def daily_quote() -> str:
    """Returns today's mindset quote for habit building."""
    return "Atomic Habits: 'You do not rise to the level of your goals. You fall to the level of your systems.'"


if __name__ == "__main__":
    mcp.run()
