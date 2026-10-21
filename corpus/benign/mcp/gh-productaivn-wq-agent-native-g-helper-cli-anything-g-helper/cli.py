"""Main Click CLI entrypoint for cli-anything-g_helper."""
import click
import json
import sys
from .utils.output_formatter import format_output
from .utils.repl_skin import start_repl
from .core.backend_client import BackendEngineClient
from .core.memento_state import SessionMemento
from .core.hardware_controller import GHelperHardwareController

memento = SessionMemento()
hardware = GHelperHardwareController()

@click.group(invoke_without_command=True)
@click.option("--json", "json_output", is_flag=True, help="Emit output strictly as JSON")
@click.option("--server-url", default="http://127.0.0.1:8080", help="Backend server URL")
@click.pass_context
def cli(ctx, json_output, server_url):
    """cli-anything-g_helper: Autonomous agent harness for g_helper."""
    ctx.ensure_object(dict)
    ctx.obj["json"] = json_output
    ctx.obj["server_url"] = server_url
    ctx.obj["client"] = BackendEngineClient(base_url=server_url)

    if ctx.invoked_subcommand is None:
        if not json_output and sys.stdin.isatty():
            start_repl(ctx)
        else:
            click.echo(ctx.get_help())
            ctx.exit(0)

@cli.group()
def daemon():
    """Manage backend daemon and inspection."""
    pass

@daemon.command("status")
@click.pass_context
def daemon_status(ctx):
    """Check daemon status and telemetry."""
    client = ctx.obj["client"]
    status_data = client.get_status()
    format_output(ctx, data=status_data, human_title="Daemon Telemetry")

@cli.group()
def session():
    """State tracking and undo/redo operations."""
    pass

@session.command("undo")
@click.pass_context
def session_undo(ctx):
    """Revert last session state change."""
    prev = memento.undo()
    format_output(ctx, data=prev or {"message": "Nothing to undo"}, human_title="Undo State")

@session.command("redo")
@click.pass_context
def session_redo(ctx):
    """Reapply reverted session state change."""
    next_s = memento.redo()
    format_output(ctx, data=next_s or {"message": "Nothing to redo"}, human_title="Redo State")

# ==========================================
# 1. Performance Profile Controls
# ==========================================
@cli.group()
def profile():
    """Manage ASUS performance profiles (Turbo, Balanced, Silent)."""
    pass

@profile.command("set")
@click.option("--mode", required=True, help="Mode name or id (turbo, balanced, silent)")
@click.pass_context
def profile_set(ctx, mode):
    """Set performance mode via OpenJev discrete option selector."""
    res = hardware.set_performance_mode(mode)
    format_output(ctx, data=res, human_title="Performance Profile")

@profile.command("get")
@click.pass_context
def profile_get(ctx):
    """Get active hardware profile state."""
    res = hardware.get_current_state()
    format_output(ctx, data=res, human_title="Hardware State")

# ==========================================
# 2. GPU Mode Controls (MUX & dGPU Power)
# ==========================================
@cli.group()
def gpu():
    """Manage GPU operation modes (Eco, Standard, Ultimate)."""
    pass

@gpu.command("set-mode")
@click.option("--mode", required=True, help="GPU mode (eco, standard, ultimate)")
@click.pass_context
def gpu_set_mode(ctx, mode):
    """Set GPU mode (Eco: dGPU off, Standard: dynamic, Ultimate: MUX direct)."""
    res = hardware.set_gpu_mode(mode)
    format_output(ctx, data=res, human_title="GPU Operating Mode")

@gpu.command("get")
@click.pass_context
def gpu_get(ctx):
    """Inspect active GPU mode and MUX status."""
    state = hardware.get_current_state()
    gpu_id = state.get("gpu_mode", 1)
    mode_names = {0: "eco", 1: "standard", 2: "ultimate"}
    res = {"gpu_mode_id": gpu_id, "gpu_mode": mode_names.get(gpu_id, "unknown")}
    format_output(ctx, data=res, human_title="GPU Mode Status")

# ==========================================
# 3. Battery Health & Charging Limit Controls
# ==========================================
@cli.group()
def battery():
    """Manage battery charging limits."""
    pass

@battery.command("set-limit")
@click.option("--percent", type=int, required=True, help="Charge limit threshold (60, 80, 100)")
@click.pass_context
def battery_set_limit(ctx, percent):
    """Set battery charge threshold."""
    res = hardware.set_battery_limit(percent)
    format_output(ctx, data=res, human_title="Battery Threshold")

@battery.command("get-limit")
@click.pass_context
def battery_get_limit(ctx):
    """Get active battery charge limit."""
    state = hardware.get_current_state()
    limit = state.get("charge_limit", 100)
    format_output(ctx, data={"charge_limit": limit}, human_title="Battery Limit")

# ==========================================
# 4. Display Refresh Rate & Overdrive Controls
# ==========================================
@cli.group()
def display():
    """Manage display panel refresh rate, overdrive, and auto-switch."""
    pass

@display.command("set")
@click.option("--refresh-rate", type=int, default=None, help="Refresh rate in Hz (60, 120, 165, 240, -1)")
@click.option("--overdrive/--no-overdrive", default=None, help="Toggle LCD panel overdrive")
@click.option("--auto/--no-auto", default=None, help="Auto refresh rate switching on AC/DC")
@click.pass_context
def display_set(ctx, refresh_rate, overdrive, auto):
    """Set display refresh rate and overdrive."""
    res = hardware.set_display_config(refresh_rate=refresh_rate, overdrive=overdrive, auto=auto)
    format_output(ctx, data=res, human_title="Display Settings")

@display.command("get")
@click.pass_context
def display_get(ctx):
    """Inspect current display panel configuration."""
    state = hardware.get_current_state()
    res = {
        "panel": state.get("internal_display"),
        "max_frequency": state.get("max_frequency"),
        "frequency": state.get("frequency"),
        "overdrive": bool(state.get("overdrive", 0)),
        "screen_auto": bool(state.get("screen_auto", 0)),
    }
    format_output(ctx, data=res, human_title="Display State")

# ==========================================
# 5. Keyboard Backlight & Aura RGB Controls
# ==========================================
@cli.group()
def keyboard():
    """Manage keyboard backlight brightness and Aura RGB effects."""
    pass

@keyboard.command("set")
@click.option("--brightness", type=int, default=None, help="Brightness level (0=Off, 1=Low, 2=Med, 3=High)")
@click.option("--aura", default=None, help="Aura mode (static, breathing, color_cycle, strobing)")
@click.pass_context
def keyboard_set(ctx, brightness, aura):
    """Set keyboard brightness and Aura RGB effect."""
    res = hardware.set_keyboard_backlight(brightness=brightness, aura_mode=aura)
    format_output(ctx, data=res, human_title="Keyboard Lighting")

@keyboard.command("get")
@click.pass_context
def keyboard_get(ctx):
    """Get keyboard brightness and Aura RGB configuration."""
    state = hardware.get_current_state()
    res = {
        "brightness": state.get("keyboard_brightness", 0),
        "backlight_type": state.get("backlight_type", 0),
    }
    format_output(ctx, data=res, human_title="Keyboard State")

# ==========================================
# 6. Power Limit Tuning Controls (SPL / sPPT)
# ==========================================
@cli.group()
def power():
    """Manage CPU and platform power limits in Watts."""
    pass

@power.command("set-limits")
@click.option("--total-w", type=int, default=None, help="Platform total power limit in Watts")
@click.option("--cpu-w", type=int, default=None, help="Sustained CPU power limit (SPL) in Watts")
@click.option("--slow-w", type=int, default=None, help="Slow boost power limit (sPPT) in Watts")
@click.option("--fast-w", type=int, default=None, help="Fast boost power limit (fPPT) in Watts")
@click.pass_context
def power_set_limits(ctx, total_w, cpu_w, slow_w, fast_w):
    """Configure custom power limits in Watts."""
    res = hardware.set_power_limits(total_w=total_w, cpu_w=cpu_w, slow_w=slow_w, fast_w=fast_w)
    format_output(ctx, data=res, human_title="Power Limits")

@power.command("get-limits")
@click.pass_context
def power_get_limits(ctx):
    """Inspect configured power limits."""
    state = hardware.get_current_state()
    res = {
        "limit_total_w": state.get("limit_total_0"),
        "limit_cpu_w": state.get("limit_cpu_0"),
        "limit_slow_w": state.get("limit_slow_0"),
        "limit_fast_w": state.get("limit_fast_0"),
    }
    format_output(ctx, data=res, human_title="Active Power Limits")

def main():
    cli()

if __name__ == "__main__":
    main()
