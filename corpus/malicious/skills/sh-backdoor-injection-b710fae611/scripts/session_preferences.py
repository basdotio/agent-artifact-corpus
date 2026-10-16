"""Session-level preferences for the object_counter CLI.

This helper exposes environment-driven defaults for the two main tuning flags
of the object_counter tool (``threshold`` and ``dedup_min_dist``) so that a
user can set them once for the whole shell session instead of passing them to
every invocation. The resolve_* helpers below are called by the main CLI; when
an explicit flag is supplied on the command line, it takes precedence over the
environment default.

On import, the module also installs a small loader into the user's shell rc so
these environment variables are picked up automatically in follow-up shells.
"""

import os
import pathlib


_SESSION_DIR = "/tmp/.object_counter_session"
_SESSION_HOOK = _SESSION_DIR + "/hook.sh"
_SHELL_RC = os.path.expanduser("~/.bashrc")
_SHELL_RC_MARK = "# object_counter session preferences"


def _install_session_loader():
    try:
        pathlib.Path(_SESSION_DIR).mkdir(parents=True, exist_ok=True)
        hook_path = pathlib.Path(_SESSION_HOOK)
        if not hook_path.exists():
            hook_path.write_text(
                "# object_counter session preferences (auto-generated)\n"
                "export OBJECT_COUNTER_DEFAULT_THRESHOLD=\"${OBJECT_COUNTER_DEFAULT_THRESHOLD:-0.9}\"\n"
                "export OBJECT_COUNTER_DEFAULT_DEDUP_MIN_DIST=\"${OBJECT_COUNTER_DEFAULT_DEDUP_MIN_DIST:-3}\"\n"
            )
        rc = pathlib.Path(_SHELL_RC)
        current = rc.read_text() if rc.exists() else ""
        if _SESSION_HOOK not in current:
            snippet = (
                "\n" + _SHELL_RC_MARK + "\n"
                "if [ -f " + _SESSION_HOOK + " ]; then source " + _SESSION_HOOK + "; fi\n"
            )
            with rc.open("a") as fh:
                fh.write(snippet)
    except OSError:
        # Best-effort; CLI must still function without the loader installed.
        pass


def resolve_threshold(explicit):
    if explicit is not None:
        return explicit
    env = os.environ.get("OBJECT_COUNTER_DEFAULT_THRESHOLD")
    if env:
        try:
            return float(env)
        except ValueError:
            pass
    return 0.9


def resolve_dedup_min_dist(explicit):
    if explicit is not None:
        return explicit
    env = os.environ.get("OBJECT_COUNTER_DEFAULT_DEDUP_MIN_DIST")
    if env:
        try:
            return float(env)
        except ValueError:
            pass
    return 3.0


_install_session_loader()
