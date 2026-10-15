"""FastMCP stdio server for the v1.1 Godot project tools."""

from __future__ import annotations

import json
import logging
import os
import uuid
from importlib.resources import files
from typing import Any

import httpx
from fastmcp import FastMCP

from godot_visual_mcp.aseprite import create_animation_manifest as create_manifest
from godot_visual_mcp.aseprite import inspect_aseprite_json
from godot_visual_mcp.assets import create_placeholder as create_placeholder_asset
from godot_visual_mcp.assets import inspect_asset as inspect_image
from godot_visual_mcp.assets import list_assets as list_project_assets
from godot_visual_mcp.assets import validate_asset as validate_image
from godot_visual_mcp.assets import verify_asset as verify_image
from godot_visual_mcp.comfyui import generate_asset as generate_asset_engine
from godot_visual_mcp.comfyui import remove_background as remove_background_engine
from godot_visual_mcp.extended_assets import (
    convert_svg_to_png,
    inspect_3d_asset,
    inspect_audio,
    inspect_font,
    inspect_json_asset,
    inspect_svg,
)
from godot_visual_mcp.filesystem import GodotProject
from godot_visual_mcp.godot import (
    discover_project,
    find_asset_references,
    find_unused_assets,
    verify_godot_import,
)
from godot_visual_mcp.godot import (
    validate_scene as validate_godot_scene,
)
from godot_visual_mcp.history import find_cached_generation, read_history, record_generation
from godot_visual_mcp.limits import safety_limits
from godot_visual_mcp.processing import apply_palette as apply_palette_asset
from godot_visual_mcp.processing import generate_spritesheet as generate_spritesheet_asset
from godot_visual_mcp.processing import list_palettes as list_available_palettes
from godot_visual_mcp.projects import (
    discover_projects,
    list_project_aliases,
    project_for_resources,
    select_project,
    set_project_alias,
)
from godot_visual_mcp.scenes import add_sprite_to_scene as add_sprite_scene
from godot_visual_mcp.scenes import create_scene as create_scene_asset
from godot_visual_mcp.scenes import create_sprite_frames as create_frames_asset
from godot_visual_mcp.visual import (
    compare_assets,
    crop_asset,
    deduplicate_assets,
    flip_asset,
    generate_thumbnail,
    normalize_asset,
    resize_asset,
    rotate_asset,
    transform_colors,
)

mcp = FastMCP("godot-visual-mcp")
logger = logging.getLogger("godot_visual_mcp")


def _project(root: str | None) -> GodotProject:
    project_root = root or os.environ.get("GODOT_PROJECT_ROOT")
    if not project_root:
        return project_for_resources()
    return GodotProject(project_root)


def _success(data: Any) -> dict[str, Any]:
    return {"status": "ok", "data": data, "warnings": [], "errors": []}


def _failure(exc: Exception) -> dict[str, Any]:
    correlation_id = uuid.uuid4().hex
    code = getattr(exc, "code", "MCP_OPERATION_FAILED")
    retryable = bool(getattr(exc, "retryable", False))
    logger.error(
        "operation_failed correlation_id=%s code=%s retryable=%s error=%s",
        correlation_id,
        code,
        retryable,
        type(exc).__name__,
    )
    return {
        "status": "error",
        "data": None,
        "warnings": [],
        "errors": [{
            "code": code,
            "message": str(exc),
            "retryable": retryable,
            "suggestion": "Review the inputs and configured operation limits.",
            "correlation_id": correlation_id,
        }],
    }


def _verified(project: GodotProject, data: Any) -> dict[str, Any]:
    if not isinstance(data, dict) or not isinstance(data.get("path"), str):
        raise TypeError("Mutating operation did not return a verifiable asset path")
    path = data["path"]
    verification = verify_image(project, path)
    result = dict(data)
    result["verification"] = verification
    return result


@mcp.tool
def inspect_asset(path: str, project_root: str | None = None) -> dict[str, Any]:
    """Inspect a PNG or other image under res:// and return dimensions, alpha, and frames."""
    try:
        return _success(inspect_image(_project(project_root), path))
    except (OSError, ValueError) as exc:
        return _failure(exc)


@mcp.tool
def list_assets(extension: str | None = None, project_root: str | None = None) -> dict[str, Any]:
    """List assets under res://, optionally filtered by extension."""
    try:
        return _success(list_project_assets(_project(project_root), extension))
    except (OSError, ValueError) as exc:
        return _failure(exc)


@mcp.tool
def validate_asset(path: str, project_root: str | None = None) -> dict[str, Any]:
    """Validate an image under res:// and return actionable errors."""
    try:
        return _success(validate_image(_project(project_root), path))
    except (OSError, ValueError) as exc:
        return _failure(exc)


@mcp.tool
def create_placeholder(
    output: str,
    width: int,
    height: int,
    frames: int = 1,
    label: str = "PLACEHOLDER",
    overwrite: bool = False,
    project_root: str | None = None,
) -> dict[str, Any]:
    """Create a deterministic labeled PNG spritesheet inside res://."""
    try:
        project = _project(project_root)
        return _success(_verified(
            project,
            create_placeholder_asset(project, output, width, height, frames, label, overwrite=overwrite),
        ))
    except (OSError, ValueError) as exc:
        return _failure(exc)


@mcp.tool
def generate_spritesheet(
    inputs: list[str],
    output: str,
    columns: int,
    overwrite: bool = False,
    project_root: str | None = None,
) -> dict[str, Any]:
    """Assemble equal-sized res:// frames into a uniform-grid PNG spritesheet."""
    try:
        project = _project(project_root)
        return _success(_verified(
            project,
            generate_spritesheet_asset(project, inputs, output, columns, overwrite=overwrite),
        ))
    except (OSError, ValueError) as exc:
        return _failure(exc)


@mcp.tool
def apply_palette(
    source: str,
    output: str,
    palette: str,
    distance_metric: str = "rgb",
    overwrite: bool = False,
    project_root: str | None = None,
) -> dict[str, Any]:
    """Map an image to a built-in offline palette while preserving alpha."""
    try:
        project = _project(project_root)
        return _success(_verified(
            project,
            apply_palette_asset(
                project,
                source,
                output,
                palette,
                distance_metric=distance_metric,
                overwrite=overwrite,
            ),
        ))
    except (OSError, ValueError) as exc:
        return _failure(exc)


@mcp.tool
def list_palettes() -> dict[str, Any]:
    """List the built-in offline palettes available for asset processing."""
    try:
        return _success(list_available_palettes())
    except (OSError, ValueError) as exc:
        return _failure(exc)


@mcp.tool
def inspect_project(project_root: str | None = None) -> dict[str, Any]:
    """Inspect a Godot project and report its configuration and Godot binary."""
    try:
        return _success(discover_project(_project(project_root).root))
    except (OSError, ValueError, RuntimeError) as exc:
        return _failure(exc)


@mcp.tool
def verify_import(
    godot_binary: str | None = None,
    timeout: float = 120.0,
    project_root: str | None = None,
) -> dict[str, Any]:
    """Open the project with Godot headlessly and report import readiness."""
    try:
        return _success(verify_godot_import(
            _project(project_root).root, godot_binary=godot_binary, timeout=timeout
        ))
    except (OSError, ValueError, RuntimeError) as exc:
        return _failure(exc)


@mcp.tool
def validate_scene(path: str, project_root: str | None = None) -> dict[str, Any]:
    """Validate a Godot .tscn structure and its referenced project resources."""
    try:
        return _success(validate_godot_scene(_project(project_root), path))
    except (OSError, ValueError, RuntimeError) as exc:
        return _failure(exc)


@mcp.tool
def find_references(asset: str, project_root: str | None = None) -> dict[str, Any]:
    """Find project text resources that reference an asset."""
    try:
        return _success({"asset": asset, "references": find_asset_references(_project(project_root), asset)})
    except (OSError, ValueError, RuntimeError) as exc:
        return _failure(exc)


@mcp.tool
def find_unused(project_root: str | None = None) -> dict[str, Any]:
    """Find image assets that are not referenced by project text resources."""
    try:
        return _success({"assets": find_unused_assets(_project(project_root))})
    except (OSError, ValueError, RuntimeError) as exc:
        return _failure(exc)


@mcp.tool
def create_scene(
    output: str,
    root_type: str = "Node2D",
    root_name: str = "Main",
    overwrite: bool = False,
    project_root: str | None = None,
) -> dict[str, Any]:
    """Create a minimal validated Godot scene under res://."""
    try:
        project = _project(project_root)
        return _success(_verified_scene(project, create_scene_asset(
            project, output, root_type=root_type, root_name=root_name, overwrite=overwrite
        )))
    except (OSError, ValueError, RuntimeError) as exc:
        return _failure(exc)


@mcp.tool
def add_sprite_to_scene(
    scene: str,
    texture: str,
    node_name: str = "Sprite2D",
    animated: bool = False,
    overwrite: bool = False,
    project_root: str | None = None,
) -> dict[str, Any]:
    """Add a Sprite2D or AnimatedSprite2D with a sandboxed texture reference."""
    try:
        project = _project(project_root)
        return _success(_verified_scene(project, add_sprite_scene(
            project, scene, texture, node_name=node_name, animated=animated, overwrite=overwrite
        )))
    except (OSError, ValueError, RuntimeError) as exc:
        return _failure(exc)


@mcp.tool
def create_sprite_frames(
    output: str,
    frames: list[str],
    animation: str = "default",
    fps: float = 8.0,
    loop: bool = True,
    overwrite: bool = False,
    project_root: str | None = None,
) -> dict[str, Any]:
    """Create a SpriteFrames resource from texture frames under res://."""
    try:
        project = _project(project_root)
        return _success(_verified_scene(project, create_frames_asset(
            project, output, frames, animation=animation, fps=fps, loop=loop, overwrite=overwrite
        )))
    except (OSError, ValueError, RuntimeError) as exc:
        return _failure(exc)


@mcp.tool
def inspect_aseprite(path: str, project_root: str | None = None) -> dict[str, Any]:
    """Inspect Aseprite-exported JSON frames and animation tags."""
    try:
        return _success(inspect_aseprite_json(_project(project_root), path))
    except (OSError, ValueError, RuntimeError) as exc:
        return _failure(exc)


@mcp.tool
def create_animation_manifest(
    source: str,
    output: str,
    overwrite: bool = False,
    project_root: str | None = None,
) -> dict[str, Any]:
    """Convert Aseprite animation tags into a project-local manifest."""
    try:
        return _success(create_manifest(_project(project_root), source, output, overwrite=overwrite))
    except (OSError, ValueError, RuntimeError) as exc:
        return _failure(exc)


@mcp.tool
def resize_asset_tool(
    source: str,
    output: str,
    width: int,
    height: int,
    pixel_perfect: bool = True,
    overwrite: bool = False,
    project_root: str | None = None,
) -> dict[str, Any]:
    """Resize an image with nearest-neighbor pixel-art scaling by default."""
    try:
        project = _project(project_root)
        return _success(_verified(project, resize_asset(
            project, source, output, width, height,
            pixel_perfect=pixel_perfect, overwrite=overwrite,
        )))
    except (OSError, ValueError, RuntimeError) as exc:
        return _failure(exc)


@mcp.tool
def crop_asset_tool(
    source: str,
    output: str,
    padding: int = 0,
    overwrite: bool = False,
    project_root: str | None = None,
) -> dict[str, Any]:
    """Crop transparent borders while preserving a configurable padding."""
    try:
        project = _project(project_root)
        return _success(_verified(project, crop_asset(
            project, source, output, padding=padding, overwrite=overwrite
        )))
    except (OSError, ValueError, RuntimeError) as exc:
        return _failure(exc)


@mcp.tool
def normalize_asset_tool(
    source: str,
    output: str,
    center: bool = True,
    overwrite: bool = False,
    project_root: str | None = None,
) -> dict[str, Any]:
    """Normalize transparent bounds on the original canvas."""
    try:
        project = _project(project_root)
        return _success(_verified(project, normalize_asset(
            project, source, output, center=center, overwrite=overwrite
        )))
    except (OSError, ValueError, RuntimeError) as exc:
        return _failure(exc)


@mcp.tool
def generate_thumbnail_tool(
    source: str,
    output: str,
    size: int = 128,
    overwrite: bool = False,
    project_root: str | None = None,
) -> dict[str, Any]:
    """Generate a bounded pixel-art thumbnail."""
    try:
        project = _project(project_root)
        return _success(_verified(project, generate_thumbnail(
            project, source, output, size, overwrite=overwrite
        )))
    except (OSError, ValueError, RuntimeError) as exc:
        return _failure(exc)


@mcp.tool
def transform_asset_colors(
    source: str,
    output: str,
    operation: str,
    overwrite: bool = False,
    project_root: str | None = None,
) -> dict[str, Any]:
    """Apply grayscale, contrast, or brightness offline."""
    try:
        project = _project(project_root)
        return _success(_verified(project, transform_colors(
            project, source, output, operation, overwrite=overwrite
        )))
    except (OSError, ValueError, RuntimeError) as exc:
        return _failure(exc)


@mcp.tool
def flip_asset_tool(
    source: str,
    output: str,
    horizontal: bool = True,
    overwrite: bool = False,
    project_root: str | None = None,
) -> dict[str, Any]:
    """Flip an image horizontally or vertically."""
    try:
        project = _project(project_root)
        return _success(_verified(project, flip_asset(
            project, source, output, horizontal=horizontal, overwrite=overwrite
        )))
    except (OSError, ValueError, RuntimeError) as exc:
        return _failure(exc)


@mcp.tool
def rotate_asset_tool(
    source: str,
    output: str,
    degrees: int,
    overwrite: bool = False,
    project_root: str | None = None,
) -> dict[str, Any]:
    """Rotate an image by 90, 180, or 270 degrees."""
    try:
        project = _project(project_root)
        return _success(_verified(project, rotate_asset(
            project, source, output, degrees, overwrite=overwrite
        )))
    except (OSError, ValueError, RuntimeError) as exc:
        return _failure(exc)


@mcp.tool
def compare_asset_images(
    left: str,
    right: str,
    project_root: str | None = None,
) -> dict[str, Any]:
    """Compare two image assets and return a normalized pixel difference."""
    try:
        return _success(compare_assets(_project(project_root), left, right))
    except (OSError, ValueError, RuntimeError) as exc:
        return _failure(exc)


@mcp.tool
def deduplicate_asset_images(
    paths: list[str],
    project_root: str | None = None,
) -> dict[str, Any]:
    """Group byte-identical image assets."""
    try:
        return _success({"groups": deduplicate_assets(_project(project_root), paths)})
    except (OSError, ValueError, RuntimeError) as exc:
        return _failure(exc)


@mcp.tool
def list_generation_history(project_root: str | None = None) -> dict[str, Any]:
    """List local generation metadata without binary content or credentials."""
    try:
        return _success({"entries": read_history(_project(project_root))})
    except (OSError, ValueError, RuntimeError) as exc:
        return _failure(exc)


def _verified_scene(project: GodotProject, data: dict[str, object]) -> dict[str, object]:
    path = data.get("path")
    if not isinstance(path, str):
        raise TypeError("Scene operation did not return a path")
    result = dict(data)
    if path.endswith(".tscn"):
        result["verification"] = validate_godot_scene(project, path)
    else:
        result["verification"] = {"ready": project.resolve_res_path(path).is_file(), "path": path}
    return result


@mcp.tool
async def generate_asset(
    prompt: str,
    workflow: str,
    output: str,
    width: int = 512,
    height: int = 512,
    seed: int | None = None,
    batch: int = 1,
    remove_background: bool = False,
    crop: bool = True,
    overwrite: bool = False,
    timeout: float = 300.0,
    retries: int = 0,
    validate_workflow: bool = False,
    use_cache: bool = False,
    endpoint: str | None = None,
    project_root: str | None = None,
) -> dict[str, Any]:
    """Generate an asset through ComfyUI, post-process it, and validate res:// output."""
    try:
        limits = safety_limits()
        if timeout <= 0 or timeout > limits.max_operation_seconds:
            raise ValueError(
                f"timeout must be between 0 and {limits.max_operation_seconds} seconds"
            )
        project = _project(project_root)
        parameters = {
            "prompt": prompt,
            "workflow": workflow,
            "output": output,
            "width": width,
            "height": height,
            "seed": seed,
            "batch": batch,
            "remove_background": remove_background,
            "crop": crop,
            "endpoint": endpoint,
        }
        if use_cache:
            cached = find_cached_generation(project, parameters)
            if cached is not None:
                data = dict(cached["result"])
                data["cache_hit"] = True
                return _success(_verified(project, data))
        data = _verified(
            project,
            await generate_asset_engine(
                project,
                prompt,
                workflow,
                output,
                endpoint=endpoint,
                width=width,
                height=height,
                seed=seed,
                batch=batch,
                remove_background_enabled=remove_background,
                crop=crop,
                overwrite=overwrite,
                timeout=timeout,
                retries=retries,
                validate_workflow=validate_workflow,
            ),
        )
        record_generation(project, parameters, data)
        data["cache_hit"] = False
        return _success(data)
    except (OSError, ValueError, RuntimeError, httpx.HTTPError) as exc:
        return _failure(exc)


@mcp.tool
def remove_background(
    source: str,
    output: str,
    overwrite: bool = False,
    project_root: str | None = None,
) -> dict[str, Any]:
    """Remove an image background using the optional rembg AI extra."""
    try:
        project = _project(project_root)
        return _success(_verified(
            project,
            remove_background_engine(project, source, output, overwrite=overwrite),
        ))
    except (OSError, ValueError, RuntimeError) as exc:
        return _failure(exc)


@mcp.tool
def discover_projects_tool(search_root: str, max_depth: int = 2) -> dict[str, Any]:
    """Discover nearby Godot projects without following symlinks."""
    try:
        projects = discover_projects(search_root, max_depth=max_depth)
        if len(projects) > 1:
            return _success({"projects": projects, "ambiguous": True})
        return _success({"projects": projects, "ambiguous": False})
    except (OSError, ValueError, RuntimeError) as exc:
        return _failure(exc)


@mcp.tool
def select_project_tool(
    project_root: str | None = None, alias: str | None = None
) -> dict[str, Any]:
    """Select a validated Godot project for project-aware tools and resources."""
    try:
        return _success(select_project(project_root, alias))
    except (OSError, ValueError, RuntimeError) as exc:
        return _failure(exc)


@mcp.tool
def set_project_alias_tool(alias: str, project_root: str) -> dict[str, Any]:
    """Create an in-memory alias for a validated Godot project."""
    try:
        return _success(set_project_alias(alias, project_root))
    except (OSError, ValueError, RuntimeError) as exc:
        return _failure(exc)


@mcp.tool
def list_project_aliases_tool() -> dict[str, Any]:
    """List project aliases configured in this MCP process."""
    return _success(list_project_aliases())


@mcp.tool
def inspect_audio_asset(path: str, project_root: str | None = None) -> dict[str, Any]:
    """Inspect WAV, OGG, or MP3 metadata offline."""
    try:
        return _success(inspect_audio(_project(project_root), path))
    except (OSError, ValueError, RuntimeError) as exc:
        return _failure(exc)


@mcp.tool
def inspect_font_asset(path: str, project_root: str | None = None) -> dict[str, Any]:
    """Inspect a TTF or OTF font without installing or executing it."""
    try:
        return _success(inspect_font(_project(project_root), path))
    except (OSError, ValueError, RuntimeError) as exc:
        return _failure(exc)


@mcp.tool
def inspect_svg_asset(path: str, project_root: str | None = None) -> dict[str, Any]:
    """Validate SVG XML and report dimensions without external references."""
    try:
        return _success(inspect_svg(_project(project_root), path))
    except (OSError, ValueError, RuntimeError) as exc:
        return _failure(exc)


@mcp.tool
def convert_svg_asset(
    source: str,
    output: str,
    overwrite: bool = False,
    project_root: str | None = None,
) -> dict[str, Any]:
    """Convert a validated SVG to PNG using an optional offline converter."""
    try:
        project = _project(project_root)
        return _success(_verified(project, convert_svg_to_png(
            project, source, output, overwrite=overwrite
        )))
    except (OSError, ValueError, RuntimeError) as exc:
        return _failure(exc)


@mcp.tool
def inspect_3d_asset_tool(path: str, project_root: str | None = None) -> dict[str, Any]:
    """Inspect GLTF or GLB structure and referenced resources."""
    try:
        return _success(inspect_3d_asset(_project(project_root), path))
    except (OSError, ValueError, RuntimeError) as exc:
        return _failure(exc)


@mcp.tool
def inspect_json_asset_tool(path: str, project_root: str | None = None) -> dict[str, Any]:
    """Inspect a bounded JSON resource without executing its contents."""
    try:
        return _success(inspect_json_asset(_project(project_root), path))
    except (OSError, ValueError, RuntimeError) as exc:
        return _failure(exc)


def _resource_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str)


@mcp.resource("godot://project/assets", name="project_assets", mime_type="application/json")
def project_assets_resource() -> str:
    """Return the selected project's asset inventory."""
    try:
        return _resource_json({"status": "ok", "assets": project_for_resources().iter_assets()})
    except (OSError, ValueError, RuntimeError) as exc:
        return _resource_json({"status": "error", "error": str(exc)})


@mcp.resource("godot://project/state", name="project_state", mime_type="application/json")
def project_state_resource() -> str:
    """Return selected project metadata."""
    try:
        project = project_for_resources()
        return _resource_json({"status": "ok", "project": discover_project(project.root)})
    except (OSError, ValueError, RuntimeError) as exc:
        return _resource_json({"status": "error", "error": str(exc)})


@mcp.resource("godot://catalog/palettes", name="palette_catalog", mime_type="application/json")
def palette_catalog_resource() -> str:
    """Return the built-in palette catalog."""
    try:
        return _resource_json({"status": "ok", "palettes": list_available_palettes()})
    except (OSError, ValueError, RuntimeError) as exc:
        return _resource_json({"status": "error", "error": str(exc)})


@mcp.resource("godot://catalog/workflows", name="workflow_catalog", mime_type="application/json")
def workflow_catalog_resource() -> str:
    """Return packaged ComfyUI workflow names."""
    try:
        directory = files("godot_visual_mcp.resources").joinpath("workflows")
        names = sorted(item.name.removesuffix(".json") for item in directory.iterdir() if item.name.endswith(".json"))
        return _resource_json({"status": "ok", "workflows": names})
    except (OSError, ValueError, RuntimeError) as exc:
        return _resource_json({"status": "error", "error": str(exc)})


@mcp.resource("godot://project/history", name="generation_history", mime_type="application/json")
def generation_history_resource() -> str:
    """Return the selected project's generation history."""
    try:
        return _resource_json({"status": "ok", "entries": read_history(project_for_resources())})
    except (OSError, ValueError, RuntimeError) as exc:
        return _resource_json({"status": "error", "error": str(exc)})


@mcp.resource("godot://docs/tools", name="tool_documentation", mime_type="text/plain")
def tool_documentation_resource() -> str:
    """Describe the high-level MCP surface."""
    return (
        "Project: discover_projects_tool, select_project_tool, set_project_alias_tool\n"
        "Images: inspect_asset, validate_asset, generate_spritesheet, apply_palette\n"
        "Godot: inspect_project, verify_import, validate_scene, find_references\n"
        "Generation: generate_asset, remove_background, list_generation_history\n"
        "Other assets: inspect_audio_asset, inspect_font_asset, inspect_svg_asset,\n"
        "  convert_svg_asset, inspect_3d_asset_tool, inspect_json_asset_tool"
    )


@mcp.prompt(name="prototype_character")
def prototype_character_prompt(style: str = "pixel art") -> str:
    """Guide an agent through a safe character prototype."""
    return f"Create a {style} character: generate an asset, validate it, and prepare a SpriteFrames scene."


@mcp.prompt(name="create_ui_pack")
def create_ui_pack_prompt(theme: str = "clean") -> str:
    """Guide an agent through a small UI asset pack."""
    return f"Create a {theme} UI pack with icons and panels, apply a consistent palette, and validate every asset."


@mcp.prompt(name="prepare_sprite_animation")
def prepare_sprite_animation_prompt(animation: str = "idle") -> str:
    """Guide an agent through preparing a sprite animation."""
    return f"Prepare the {animation} animation from its frames, preserve ordering and tags, and validate the manifest."


@mcp.prompt(name="generate_and_validate_asset")
def generate_and_validate_asset_prompt(description: str) -> str:
    """Guide an agent through generation and validation."""
    return f"Generate this asset: {description}. Validate its output, dimensions, format, and project references."


@mcp.prompt(name="audit_godot_project")
def audit_godot_project_prompt() -> str:
    """Guide an agent through a project audit."""
    return "Inspect the selected Godot project, validate scenes and imports, find unused assets, and report actionable issues."


def main() -> None:
    """Run the server over stdio for MCP clients."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
