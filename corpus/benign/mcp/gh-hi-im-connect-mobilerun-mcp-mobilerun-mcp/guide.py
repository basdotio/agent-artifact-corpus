"""Usage guide served by get_usage_guide and the mobilerun://guide resource (written for this server)."""

from __future__ import annotations

TOPICS: dict[str, str] = {
    "overview": """\
Perceive, act, verify.
1. read_screen (text grid, cheap) or perceive_screen (annotated screenshot + e array): numbered
   marks (som_id). perceive_screen(detail="full") adds the icon detector + OCR for unlabelled icons.
2. Act with tap/type_text/swipe/scroll_*/press_*/launch_app. Each call settles and returns
   post_action_observation (foreground app, element_count, keyboard_visible, top_labels,
   screen_changed, settled). That block is your verification: read it before perceiving again.
3. som_ids are single-use. After ANY action they are stale (stale_som_id); perceive to get new ones.
Prefer read_screen when you only need text (no image). get_ui_tree shows structure and flags.""",
    "shortcuts": """\
A typed call beats tapping through an app:
- system_intent: set_alarm(hour, minute), set_timer(seconds), dial, compose_sms, add_calendar_event,
  share_text, navigate. dial/compose_sms only prefill; the user presses send.
- read_notifications / notification_action / dismiss_notification: no need to open the app.
- media_control, volume_up/down, mute for playback.
- list_app_deeplinks + open_deeplink jump straight to a screen. resolve_contact turns a name into a number.
- launch_app(app_name=...) resolves names itself; an ambiguous name returns ranked candidates.""",
    "text_entry": """\
type_text goes to the FOCUSED field: tap it first (or pass som_id) and check keyboard_visible.
type_text appends; use clear=true to replace. Autocomplete fields need a commit tap on the
suggestion. Search bars submit with press_enter (or submit=true). press_back closes the keyboard
without leaving the screen. Read the field back afterwards: autocorrect can change what you typed.""",
    "failures": """\
Do not repeat a failed action. Ladder: re-perceive -> scroll_to / scroll_* -> press_back and take
another route (deep link, search bar, another tab) -> web_search the specific problem -> ask the user.
A policy_blocked error is a safety decision: never route around it (not via adb or run_task either).
Cold app starts can take ~20s on this device; launch_app/open_deeplink wait for them.""",
    "ledger": """\
For multi-step goals: set_plan(steps, goal, deliverable, target_count) then mark_step as you go.
record_finding(item, quote) for each item you read (the quote must appear on the current screen).
end_session(outcome="success") is refused until findings reach target_count; otherwise finish with
outcome="partial" and say exactly what was covered. Never claim an unverified success.""",
    "browser": """\
browser_open(url) returns the page text, numbered elements (el_id) and a generation. session
"scratch" (default) is this server's browser, signed into nothing; "mine" drives the user's
signed-in browser (Chrome). browser_act(action, el_id, value, generation) acts and returns the new
page; a stale generation returns stale_handles. browser_find(text) locates an element (scrolling
lazy lists), browser_extract pulls repeated items, browser_tabs keeps several pages, browser_wait
waits for text. browser_handoff(prompt) lets the person sign in or solve a CAPTCHA; call it again
with check=true. Never ask for passwords.""",
    "safety": """validate_action(gesture_type, target) pre-checks the policy. With MOBILERUN_MCP_POLICY on, banking,
payment, authenticator and password-manager apps, card numbers, CVVs (and in strict mode passwords,
PINs, national ids) are refused with policy_blocked. That is final: never reach it through adb,
run_task or coordinates. sensitive_foreground in an observation means leave the app.""",
    "stop": """Finish with end_session(reason, outcome, goal_type). Claim success only from evidence you hold:
the last post_action_observation or a fresh read_screen. For send_message, send_email, purchase
and post, success is refused unless you looked at the screen after your last action.""",
    "efficiency": """One consequential action per turn, then read its observation instead of re-reading the screen.
Prefer typed tools and deep links over navigation. wait_for is for long waits only (downloads,
processing); gestures already settle. read_screen is cheaper than perceive_screen.""",
}


# AURA's topic names
ALIASES = {
    "decision_tree": "shortcuts",
    "perception": "overview",
    "loop": "overview",
    "loading": "efficiency",
    "trust": "safety",
    "deeplinks": "shortcuts",
    "action_plane": "text_entry",
}


def guide(topic: str | None = None) -> str:
    topic = ALIASES.get(topic or "", topic)
    if topic == "full":
        topic = None
    if topic and topic in TOPICS:
        return TOPICS[topic]
    if topic:
        return f"Unknown topic {topic!r}. Topics: {', '.join(TOPICS)}"
    return "\n\n".join(f"## {name}\n{body}" for name, body in TOPICS.items())
