"""Native MCP transport is supplied by the official SDK, not implemented here."""
import json
import sys
from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, TextContent, ToolAnnotations
from pydantic import Field

from .client import SoarClient
from .config import Settings
from .operations import OwnedOperations

PositiveId = Annotated[int, Field(strict=True, gt=0)]
Page = Annotated[int, Field(strict=True, ge=0)]
PageSize = Annotated[int, Field(strict=True, ge=1, le=100)]
RunKind = Literal['playbook_run', 'action_run', 'app_run']
READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True)
WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=True)


def result(value):
    return CallToolResult(content=[TextContent(type='text', text=json.dumps(value, ensure_ascii=False, allow_nan=False))],
                          structuredContent=value, isError='error' in value)


def create_server(client: SoarClient, operations: OwnedOperations | None = None):
    server = FastMCP('soar', log_level='WARNING', instructions=(
        'SOAR observations and explicitly selected owned-resource operations. HTTP/tool success is not action success or product PASS. '
        'List operations return one explicit page; inspect num_pages/count and request further pages. '
        'Large bodies remain complete in evidence; use read_evidence with next_offset until complete. '
        'Do not treat a preview as full evidence. Without an owner namespace/source root this server is read-only. '
        'For writes, choose a stable operation_id. Repeating it reads back the committed result, never reruns it. '
        'Unknown execution requires inspection, not a new ID to retry. Source files remain role-authored. '
        'After debugger start inspect actual run and nested action results; clean only owned objects after retaining evidence.'))

    @server.tool(annotations=READ_ONLY)
    def list_apps(page: Page = 0, page_size: PageSize = 20) -> CallToolResult:
        """Read one installed-app inventory page from SOAR; no installation or mutation."""
        return result(client.list_records('app', page=page, page_size=page_size))

    @server.tool(annotations=READ_ONLY)
    def get_app(app_id: PositiveId) -> CallToolResult:
        """Read installed app details with pretty action names; do not infer parameter schemas."""
        return result(client.get_app(app_id))

    @server.tool(annotations=READ_ONLY)
    def list_app_actions(app_id: PositiveId, page: Page = 0, page_size: PageSize = 20) -> CallToolResult:
        """Read one installed action-definition page, including original parameters/output fields.

        Select the exact returned action ID; no fuzzy match or inferred schema. Installed
        metadata is an observation, not a replacement for sealed connector source behavior.
        """
        return result(client.list_app_actions(app_id, page=page, page_size=page_size))

    @server.tool(annotations=READ_ONLY)
    def get_app_action(app_action_id: PositiveId) -> CallToolResult:
        """Read the complete installed definition of one exact action ID from list_app_actions."""
        return result(client.get_app_action(app_action_id))

    @server.tool(annotations=READ_ONLY)
    def export_playbook(playbook_id: PositiveId) -> CallToolResult:
        """Retain the exact SOAR gzip Playbook export (Python and graph/metadata), without execution.

        Use its evidence resource for full binary bytes. Do not ask the model to transcribe
        Base64. Unknown layouts retain all bytes but return an explicit diagnostic.
        """
        return result(client.export_playbook(playbook_id))

    @server.tool(annotations=READ_ONLY)
    def inspect_playbook_bundle(evidence_id: str) -> CallToolResult:
        """Read Python and complete graph/metadata from an already retained export, without new HTTP.

        Each exact member has its own evidence ID and paged view. Follow next_offset
        with read_evidence. graph_fields_present reports keys, not graph correctness;
        absent graph fields remain absent. No source generation, filtering or execution.
        """
        return result(client.inspect_playbook_bundle(evidence_id))

    @server.tool(annotations=READ_ONLY)
    def get_artifact(artifact_id: PositiveId) -> CallToolResult:
        """Read one artifact's original fields/CEF; reading does not grant mutation ownership."""
        return result(client.get_artifact(artifact_id))

    @server.tool(annotations=READ_ONLY)
    def list_artifacts(container_id: PositiveId, page: Page = 0, page_size: PageSize = 20) -> CallToolResult:
        """Read one explicit artifact page of a selected container, with original CEF values."""
        return result(client.list_artifacts(container_id, page=page, page_size=page_size))

    @server.tool(annotations=READ_ONLY)
    def get_run(kind: RunKind, run_id: PositiveId) -> CallToolResult:
        """Read a known run. Nested connector results can fail even when the outer status succeeds."""
        return result(client.get_run(kind, run_id))

    @server.tool(annotations=READ_ONLY)
    def get_playbook_logs(run_id: PositiveId, page: Page = 0, page_size: PageSize = 20,
                          message_contains: str | None = None) -> CallToolResult:
        """Read one original PlaybookRun log page, optionally filtered by literal message text.

        Empty logs do not prove success: logging may be disabled or evidence deleted.
        Preserve logs before deleting the container, which cascades run records.
        """
        return result(client.playbook_logs(run_id, page=page, page_size=page_size,
                                          message_contains=message_contains))

    @server.tool(annotations=READ_ONLY)
    def list_related_runs(kind: Literal['action_run', 'app_run'], parent_id: PositiveId,
                          page: Page = 0, page_size: PageSize = 20) -> CallToolResult:
        """Read one related-run page: action_run uses PlaybookRun parent; app_run uses ActionRun parent."""
        return result(client.list_records(kind, parent_id=parent_id, page=page, page_size=page_size))

    @server.tool(annotations=READ_ONLY)
    def get_action_results(app_run_id: PositiveId, page: Page = 0,
                           page_size: PageSize = 20) -> CallToolResult:
        """Read one AppRun action_result page, retaining data, summary, parameters and failure fields."""
        return result(client.action_results(app_run_id, page=page, page_size=page_size))

    @server.tool(annotations=READ_ONLY)
    def read_evidence(evidence_id: str, offset: Page = 0,
                      limit: Annotated[int, Field(strict=True, ge=1, le=16000)] = 16000) -> CallToolResult:
        """Read retained bytes without repeating SOAR requests. Follow next_offset; units are explicit."""
        return result(client.evidence.read(evidence_id, offset=offset, limit=limit))

    if operations is not None:
        @server.tool(annotations=READ_ONLY)
        def list_owned_resources() -> CallToolResult:
            """Read this scope's resource IDs and unknown/pending writes; historical IDs may be retired."""
            return result(operations.inventory())

        @server.tool(annotations=READ_ONLY)
        def get_owned_resource(kind: Literal['asset', 'container', 'playbook', 'artifact'], resource_id: PositiveId) -> CallToolResult:
            """Read back an owned object and check original ID/name; a deleted container returns 404."""
            return result(operations.get_owned(kind, resource_id))

        @server.tool(annotations=WRITE)
        def create_asset(operation_id: str, name: str, app_id: PositiveId, configuration: dict) -> CallToolResult:
            """Create a new namespaced asset. Configuration comes from the role/product, never a fixed connector helper."""
            return result(operations.create_asset(operation_id, name, app_id, configuration))

        @server.tool(annotations=WRITE)
        def create_container(operation_id: str, name: str, label: str) -> CallToolResult:
            """Create a new namespaced event with automatic playbook execution disabled."""
            return result(operations.create_container(operation_id, name, label))

        @server.tool(annotations=WRITE)
        def create_artifact(operation_id: str, name: str, container_id: PositiveId,
                            cef: dict, label: str, cef_types: dict | None = None) -> CallToolResult:
            """Create an artifact only in this scope's owned container, with automation disabled.

            Explicit test input, not a fabricated connector result. Remote duplicates are not adopted.
            """
            return result(operations.create_artifact(operation_id, name, container_id, cef, label, cef_types))

        @server.tool(annotations=WRITE)
        def update_artifact_cef(operation_id: str, artifact_id: PositiveId, cef_patch: dict) -> CallToolResult:
            """Merge explicit top-level CEF keys of an owned artifact without triggering automation.

            Unspecified keys and cef_types remain; null is a value, not deletion. Nested values
            are replaced whole. Use only at a quiet setup boundary: this is not a concurrent CAS.
            No rename/reparent, no modification of foreign or connector-created artifacts.
            """
            return result(operations.update_artifact_cef(operation_id, artifact_id, cef_patch))

        @server.tool(annotations=WRITE)
        def import_playbook(operation_id: str, source_path: str, scm_id: PositiveId) -> CallToolResult:
            """Import an exact assigned gzip bundle as a NEW namespaced Playbook, never overwrite.

            Only a flat matching Python/JSON pair up to 32 MiB compressed/uncompressed is
            supported. No links, traversal, ambiguous names or active request. The bundle
            is sent unchanged; code performs Base64 transport. Verify inactive readback,
            source/graph and validation before any explicit Debugger execution. No replay.
            """
            return result(operations.import_playbook(operation_id, source_path, scm_id))

        @server.tool(annotations=WRITE)
        def save_playbook(operation_id: str, name: str, source_path: str, scm_id: PositiveId,
                          labels: list[str], python_version: str) -> CallToolResult:
            """Save a new inactive VPE from an exact UTF-8 Python file relative to the selected source root.

            No code generation/rewriting or existing Playbook update. Inspect returned validation and
            separate get_owned_resource before execution. Labels and Python version are explicit.
            """
            return result(operations.save_playbook(operation_id, name, source_path, scm_id, labels, python_version))

        @server.tool(annotations=WRITE)
        def start_debugger(operation_id: str, playbook_id: PositiveId, container_id: PositiveId) -> CallToolResult:
            """Start the verified VPE Debugger HTTP path for owned validated inactive VPE/event.

            Returns immediately with the actual run ID, NOT execution success. Inspect get_run,
            list_related_runs and get_action_results. No automatic retry, polling or cleanup.
            """
            return result(operations.start_debugger(operation_id, playbook_id, container_id))

        @server.tool(annotations=WRITE)
        def cancel_owned_run(operation_id: str, run_id: PositiveId) -> CallToolResult:
            """Request cancellation of one run created by this scope; verify actual status separately."""
            return result(operations.cancel_run(operation_id, run_id))

        @server.tool(annotations=WRITE)
        def delete_owned_resource(operation_id: str, kind: Literal['asset', 'container', 'playbook', 'artifact'],
                                   resource_id: PositiveId) -> CallToolResult:
            """Delete/retire only a matching owned object, never foreign IDs.

            Retain full run/action evidence first: container deletion cascades run records.
            SOAR retains disabled Playbook/asset history; verify cleanup via get_owned_resource.
            """
            return result(operations.delete(operation_id, kind, resource_id))

    @server.resource('soar-evidence://{evidence_id}/body', mime_type='application/octet-stream')
    def evidence_body(evidence_id: str) -> str | bytes:
        """Full unmodified HTTP response body (may be large); binary data uses SDK blob transport."""
        body = client.evidence.raw(evidence_id)
        try:
            return body.decode('utf-8')
        except UnicodeDecodeError:
            return body

    return server


def main():
    try:
        settings = Settings.from_env()
    except (ValueError, OSError) as exc:
        print(f'Invalid SOAR MCP configuration: {exc}', file=sys.stderr)
        raise SystemExit(2) from None
    with SoarClient(settings) as client:
        operations = OwnedOperations(client, settings.namespace, settings.source_root) if settings.namespace else None
        create_server(client, operations).run(transport='stdio')
