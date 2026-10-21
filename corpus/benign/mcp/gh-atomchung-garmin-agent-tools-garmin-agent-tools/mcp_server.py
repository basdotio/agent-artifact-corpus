"""Optional stdio MCP adapter. Login and credentials are outside the model tool surface."""
from . import core


def run():
    from mcp.server.fastmcp import FastMCP
    from mcp.types import ToolAnnotations
    server=FastMCP('Garmin Agent Tools',log_level='CRITICAL')
    def safe(fn):
        try: return fn()
        except Exception as exc:
            return {'status':'failed','error_type':type(exc).__name__,
                    'message':str(exc) if isinstance(exc,core.ToolError) else 'Provider operation failed; no raw response disclosed'}
    @server.tool(annotations=ToolAnnotations(readOnlyHint=True,destructiveHint=False))
    def read_snapshot(date:str)->dict:
        """Read a small live Garmin activity, readiness and device summary for an explicit date."""
        return safe(lambda:core.snapshot(core.authenticated(),date))
    @server.tool(annotations=ToolAnnotations(readOnlyHint=True,destructiveHint=False))
    def read_workout(workout_id:int)->dict:
        """Read the stored steps of one Garmin workout; this does not prove watch receipt."""
        return safe(lambda:core.readback(core.authenticated(),workout_id))
    @server.tool(annotations=ToolAnnotations(readOnlyHint=False,destructiveHint=False,idempotentHint=True))
    def preview_test(tag:str,date:str|None=None,device_id:int|None=None)->dict:
        """Save an exact local preview of a fixed 20-minute test; no Garmin write. Date and device are optional explicit effects."""
        return safe(lambda:core.preview_test(core.authenticated(),tag,date,device_id))
    @server.tool(annotations=ToolAnnotations(readOnlyHint=False,destructiveHint=False,idempotentHint=True))
    def apply_test(approval_sha256:str)->dict:
        """Write only the exact preview the athlete approved, and read it back; never claims watch receipt."""
        return safe(lambda:core.apply_test(core.authenticated(),approval_sha256))
    server.run(transport='stdio')
