#!/usr/bin/env python3
"""
MagicaVoxel MCP Server - Minimal Version
Provides basic tools for creating and modifying MagicaVoxel .vox files
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from vox_utils import VoxelModel, read_vox_file, write_vox_file, render_model_all_angles

# Initialize MCP server
app = Server("magicavoxel-mcp")

# Default paths
DEFAULT_VOX_DIR = Path(os.getenv("VOX_DIR", "vox"))
DEFAULT_VOX_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_EXPORT_DIR = Path(os.getenv("EXPORT_DIR", "export"))
DEFAULT_EXPORT_DIR.mkdir(parents=True, exist_ok=True)


def get_vox_path(filename: str) -> Path:
    """Get full path to a .vox file"""
    if not filename.endswith('.vox'):
        filename += '.vox'
    return DEFAULT_VOX_DIR / filename


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools"""
    return [
        Tool(
            name="create_voxel_model",
            description="Create a new empty voxel model with specified dimensions",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file (without .vox extension)"},
                    "width": {"type": "integer", "description": "Width (X dimension)", "default": 10},
                    "height": {"type": "integer", "description": "Height (Y dimension)", "default": 10},
                    "depth": {"type": "integer", "description": "Depth (Z dimension)", "default": 10}
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="read_voxel_model",
            description="Read and inspect a .vox file, returning information about its structure",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file (without .vox extension)"}
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="place_voxel",
            description="Place a voxel at a specific coordinate in a model",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "x": {"type": "integer", "description": "X coordinate"},
                    "y": {"type": "integer", "description": "Y coordinate"},
                    "z": {"type": "integer", "description": "Z coordinate"},
                    "color_index": {"type": "integer", "description": "Color index (0-255)", "default": 1}
                },
                "required": ["filename", "x", "y", "z"]
            }
        ),
        Tool(
            name="remove_voxel",
            description="Remove a voxel at specific coordinates in a model",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "x": {"type": "integer", "description": "X coordinate"},
                    "y": {"type": "integer", "description": "Y coordinate"},
                    "z": {"type": "integer", "description": "Z coordinate"}
                },
                "required": ["filename", "x", "y", "z"]
            }
        ),
        Tool(
            name="fill_box",
            description="Fill a rectangular region with voxels",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "x1": {"type": "integer", "description": "Start X coordinate"},
                    "y1": {"type": "integer", "description": "Start Y coordinate"},
                    "z1": {"type": "integer", "description": "Start Z coordinate"},
                    "x2": {"type": "integer", "description": "End X coordinate"},
                    "y2": {"type": "integer", "description": "End Y coordinate"},
                    "z2": {"type": "integer", "description": "End Z coordinate"},
                    "color_index": {"type": "integer", "description": "Color index (0-255)", "default": 1}
                },
                "required": ["filename", "x1", "y1", "z1", "x2", "y2", "z2"]
            }
        ),
        Tool(
            name="clear_region",
            description="Remove all voxels in a rectangular region",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "x1": {"type": "integer", "description": "Start X coordinate"},
                    "y1": {"type": "integer", "description": "Start Y coordinate"},
                    "z1": {"type": "integer", "description": "Start Z coordinate"},
                    "x2": {"type": "integer", "description": "End X coordinate"},
                    "y2": {"type": "integer", "description": "End Y coordinate"},
                    "z2": {"type": "integer", "description": "End Z coordinate"}
                },
                "required": ["filename", "x1", "y1", "z1", "x2", "y2", "z2"]
            }
        ),
        Tool(
            name="create_sphere",
            description="Create a sphere in a model at specified center with given radius",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "center_x": {"type": "integer", "description": "X coordinate of sphere center"},
                    "center_y": {"type": "integer", "description": "Y coordinate of sphere center"},
                    "center_z": {"type": "integer", "description": "Z coordinate of sphere center"},
                    "radius": {"type": "integer", "description": "Radius of the sphere"},
                    "color_index": {"type": "integer", "description": "Color index (0-255)", "default": 1},
                    "hollow": {"type": "boolean", "description": "Create hollow sphere (surface only)", "default": False}
                },
                "required": ["filename", "center_x", "center_y", "center_z", "radius"]
            }
        ),
        Tool(
            name="create_cylinder",
            description="Create a cylinder in a model",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "center_x": {"type": "integer", "description": "X coordinate of cylinder base center"},
                    "center_y": {"type": "integer", "description": "Y coordinate of cylinder base center"},
                    "center_z": {"type": "integer", "description": "Z coordinate of cylinder base center"},
                    "radius": {"type": "integer", "description": "Radius of the cylinder"},
                    "height": {"type": "integer", "description": "Height of the cylinder"},
                    "axis": {"type": "string", "description": "Axis direction: 'x', 'y', or 'z'", "default": "y"},
                    "color_index": {"type": "integer", "description": "Color index (0-255)", "default": 1},
                    "hollow": {"type": "boolean", "description": "Create hollow cylinder", "default": False}
                },
                "required": ["filename", "center_x", "center_y", "center_z", "radius", "height"]
            }
        ),
        Tool(
            name="create_pyramid",
            description="Create a pyramid in a model",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "base_x": {"type": "integer", "description": "X coordinate of pyramid base corner"},
                    "base_y": {"type": "integer", "description": "Y coordinate of pyramid base (bottom)"},
                    "base_z": {"type": "integer", "description": "Z coordinate of pyramid base corner"},
                    "base_width": {"type": "integer", "description": "Width of pyramid base"},
                    "base_depth": {"type": "integer", "description": "Depth of pyramid base"},
                    "height": {"type": "integer", "description": "Height of the pyramid"},
                    "color_index": {"type": "integer", "description": "Color index (0-255)", "default": 1},
                    "hollow": {"type": "boolean", "description": "Create hollow pyramid", "default": False}
                },
                "required": ["filename", "base_x", "base_y", "base_z", "base_width", "base_depth", "height"]
            }
        ),
        Tool(
            name="create_torus",
            description="Create a torus (donut) shape in a model",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "center_x": {"type": "integer", "description": "X coordinate of center"},
                    "center_y": {"type": "integer", "description": "Y coordinate of center"},
                    "center_z": {"type": "integer", "description": "Z coordinate of center"},
                    "major_radius": {"type": "integer", "description": "Distance from center to tube center"},
                    "minor_radius": {"type": "integer", "description": "Radius of the tube"},
                    "axis": {"type": "string", "description": "Axis: 'x', 'y', or 'z'", "default": "y"},
                    "color_index": {"type": "integer", "description": "Color index (0-255)", "default": 1},
                    "hollow": {"type": "boolean", "description": "Create hollow torus", "default": False}
                },
                "required": ["filename", "center_x", "center_y", "center_z", "major_radius", "minor_radius"]
            }
        ),
        Tool(
            name="create_cone",
            description="Create a cone shape in a model",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "base_x": {"type": "integer", "description": "X coordinate of base center"},
                    "base_y": {"type": "integer", "description": "Y coordinate of base (bottom)"},
                    "base_z": {"type": "integer", "description": "Z coordinate of base center"},
                    "base_radius": {"type": "integer", "description": "Radius of base"},
                    "height": {"type": "integer", "description": "Height of cone"},
                    "axis": {"type": "string", "description": "Axis: 'x', 'y', or 'z'", "default": "y"},
                    "color_index": {"type": "integer", "description": "Color index (0-255)", "default": 1},
                    "hollow": {"type": "boolean", "description": "Create hollow cone", "default": False}
                },
                "required": ["filename", "base_x", "base_y", "base_z", "base_radius", "height"]
            }
        ),
        Tool(
            name="set_palette_color",
            description="Set a specific color in the model's palette",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "color_index": {"type": "integer", "description": "Palette index to set (0-255)"},
                    "r": {"type": "integer", "description": "Red component (0-255)"},
                    "g": {"type": "integer", "description": "Green component (0-255)"},
                    "b": {"type": "integer", "description": "Blue component (0-255)"},
                    "a": {"type": "integer", "description": "Alpha component (0-255)", "default": 255}
                },
                "required": ["filename", "color_index", "r", "g", "b"]
            }
        ),
        Tool(
            name="replace_color",
            description="Replace all voxels of one color with another color in a model",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "old_color": {"type": "integer", "description": "Color index to replace (0-255)"},
                    "new_color": {"type": "integer", "description": "New color index (0-255)"}
                },
                "required": ["filename", "old_color", "new_color"]
            }
        ),
        Tool(
            name="get_voxel",
            description="Get the color index of a voxel at specific coordinates",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "x": {"type": "integer", "description": "X coordinate"},
                    "y": {"type": "integer", "description": "Y coordinate"},
                    "z": {"type": "integer", "description": "Z coordinate"}
                },
                "required": ["filename", "x", "y", "z"]
            }
        ),
        Tool(
            name="get_palette",
            description="Get all palette colors from a model",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"}
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="get_model_info",
            description="Get detailed information about a voxel model including dimensions and voxel count",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"}
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="delete_model",
            description="Delete a .vox file from the vox directory",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"}
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="copy_model",
            description="Copy a .vox file to a new filename",
            inputSchema={
                "type": "object",
                "properties": {
                    "source_filename": {"type": "string", "description": "Source .vox file name"},
                    "target_filename": {"type": "string", "description": "Target .vox file name"}
                },
                "required": ["source_filename", "target_filename"]
            }
        ),
        Tool(
            name="take_snapshot",
            description="Take a snapshot (backup copy) of a model with optional name or auto-generated timestamp",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file to snapshot"},
                    "snapshot_name": {"type": "string", "description": "Optional name for the snapshot (without .vox). If not provided, uses timestamp"}
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="rotate_region",
            description="Rotate a region of voxels around a center point",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "x1": {"type": "integer", "description": "Start X coordinate of region"},
                    "y1": {"type": "integer", "description": "Start Y coordinate of region"},
                    "z1": {"type": "integer", "description": "Start Z coordinate of region"},
                    "x2": {"type": "integer", "description": "End X coordinate of region"},
                    "y2": {"type": "integer", "description": "End Y coordinate of region"},
                    "z2": {"type": "integer", "description": "End Z coordinate of region"},
                    "center_x": {"type": "integer", "description": "X coordinate of rotation center"},
                    "center_y": {"type": "integer", "description": "Y coordinate of rotation center"},
                    "center_z": {"type": "integer", "description": "Z coordinate of rotation center"},
                    "axis": {"type": "string", "description": "Rotation axis: 'x', 'y', or 'z'"},
                    "degrees": {"type": "integer", "description": "Rotation angle: 90, 180, or 270"}
                },
                "required": ["filename", "x1", "y1", "z1", "x2", "y2", "z2", "center_x", "center_y", "center_z", "axis", "degrees"]
            }
        ),
        Tool(
            name="mirror_region",
            description="Mirror a region of voxels across a plane",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "x1": {"type": "integer", "description": "Start X coordinate of region"},
                    "y1": {"type": "integer", "description": "Start Y coordinate of region"},
                    "z1": {"type": "integer", "description": "Start Z coordinate of region"},
                    "x2": {"type": "integer", "description": "End X coordinate of region"},
                    "y2": {"type": "integer", "description": "End Y coordinate of region"},
                    "z2": {"type": "integer", "description": "End Z coordinate of region"},
                    "plane": {"type": "string", "description": "Mirror plane: 'x', 'y', or 'z'"},
                    "position": {"type": "integer", "description": "Position of the mirror plane along the axis"}
                },
                "required": ["filename", "x1", "y1", "z1", "x2", "y2", "z2", "plane", "position"]
            }
        ),
        Tool(
            name="copy_region",
            description="Copy a region of voxels to a new location",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "x1": {"type": "integer", "description": "Start X coordinate of source region"},
                    "y1": {"type": "integer", "description": "Start Y coordinate of source region"},
                    "z1": {"type": "integer", "description": "Start Z coordinate of source region"},
                    "x2": {"type": "integer", "description": "End X coordinate of source region"},
                    "y2": {"type": "integer", "description": "End Y coordinate of source region"},
                    "z2": {"type": "integer", "description": "End Z coordinate of source region"},
                    "target_x": {"type": "integer", "description": "Target X coordinate (top-left corner)"},
                    "target_y": {"type": "integer", "description": "Target Y coordinate (top-left corner)"},
                    "target_z": {"type": "integer", "description": "Target Z coordinate (top-left corner)"}
                },
                "required": ["filename", "x1", "y1", "z1", "x2", "y2", "z2", "target_x", "target_y", "target_z"]
            }
        ),
        Tool(
            name="extrude_region",
            description="Extrude a region in a direction to create extended shapes",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "x1": {"type": "integer", "description": "Start X coordinate of region"},
                    "y1": {"type": "integer", "description": "Start Y coordinate of region"},
                    "z1": {"type": "integer", "description": "Start Z coordinate of region"},
                    "x2": {"type": "integer", "description": "End X coordinate of region"},
                    "y2": {"type": "integer", "description": "End Y coordinate of region"},
                    "z2": {"type": "integer", "description": "End Z coordinate of region"},
                    "direction": {"type": "string", "description": "Extrusion direction: 'x+', 'x-', 'y+', 'y-', 'z+', 'z-'"},
                    "distance": {"type": "integer", "description": "Distance to extrude"},
                    "color_index": {"type": "integer", "description": "Optional color override (uses original colors if not specified)"}
                },
                "required": ["filename", "x1", "y1", "z1", "x2", "y2", "z2", "direction", "distance"]
            }
        ),
        Tool(
            name="find_connected_components",
            description="Find all disconnected parts in a model (useful for detecting floating pieces)",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"}
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="get_surface_voxels",
            description="Get all surface (exposed) voxels in a model",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"}
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="subtract_region",
            description="Remove all voxels in a region (boolean subtract operation)",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "x1": {"type": "integer", "description": "Start X coordinate"},
                    "y1": {"type": "integer", "description": "Start Y coordinate"},
                    "z1": {"type": "integer", "description": "Start Z coordinate"},
                    "x2": {"type": "integer", "description": "End X coordinate"},
                    "y2": {"type": "integer", "description": "End Y coordinate"},
                    "z2": {"type": "integer", "description": "End Z coordinate"}
                },
                "required": ["filename", "x1", "y1", "z1", "x2", "y2", "z2"]
            }
        ),
        Tool(
            name="union_models",
            description="Combine two models together (boolean union operation)",
            inputSchema={
                "type": "object",
                "properties": {
                    "target_filename": {"type": "string", "description": "Target model to modify"},
                    "source_filename": {"type": "string", "description": "Source model to add"},
                    "offset_x": {"type": "integer", "description": "X offset for source model", "default": 0},
                    "offset_y": {"type": "integer", "description": "Y offset for source model", "default": 0},
                    "offset_z": {"type": "integer", "description": "Z offset for source model", "default": 0}
                },
                "required": ["target_filename", "source_filename"]
            }
        ),
        Tool(
            name="intersect_region",
            description="Keep only voxels within a region (boolean intersect operation)",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "x1": {"type": "integer", "description": "Start X coordinate"},
                    "y1": {"type": "integer", "description": "Start Y coordinate"},
                    "z1": {"type": "integer", "description": "Start Z coordinate"},
                    "x2": {"type": "integer", "description": "End X coordinate"},
                    "y2": {"type": "integer", "description": "End Y coordinate"},
                    "z2": {"type": "integer", "description": "End Z coordinate"}
                },
                "required": ["filename", "x1", "y1", "z1", "x2", "y2", "z2"]
            }
        ),
        Tool(
            name="scale_model",
            description="Scale the model uniformly or per-axis",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "factor": {"type": "number", "description": "Uniform scale factor", "default": 2.0},
                    "factor_x": {"type": "number", "description": "X-axis scale factor (overrides factor if set)"},
                    "factor_y": {"type": "number", "description": "Y-axis scale factor (overrides factor if set)"},
                    "factor_z": {"type": "number", "description": "Z-axis scale factor (overrides factor if set)"}
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="dilate",
            description="Dilate: expand surface voxels outward (adds layers to make model larger)",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "iterations": {"type": "integer", "description": "Number of dilation iterations", "default": 1}
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="erode",
            description="Erode: remove surface voxels (shrinks model, refines shape)",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "iterations": {"type": "integer", "description": "Number of erosion iterations", "default": 1}
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="flood_fill",
            description="Fill all hollow interior spaces with color (or remove if color_index=0)",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "color_index": {"type": "integer", "description": "Color index to fill with (0 = remove hollow spaces)", "default": 0}
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="shell",
            description="Remove all interior voxels, keep only surface (hull operation)",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"}
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="invert",
            description="Invert: swap solid and empty space within model bounds",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"}
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="shrink",
            description="Resize model bounds to fit actual voxels (remove empty space around model)",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"}
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="repeat_pattern",
            description="Repeat/tile the model pattern across axes (create patterns)",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "count_x": {"type": "integer", "description": "Repeat count on X axis", "default": 2},
                    "count_y": {"type": "integer", "description": "Repeat count on Y axis", "default": 1},
                    "count_z": {"type": "integer", "description": "Repeat count on Z axis", "default": 1},
                    "mirror": {"type": "boolean", "description": "Mirror on odd repetitions", "default": False}
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="apply_noise",
            description="Apply procedural noise to voxel colors (adds texture/variation)",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "seed": {"type": "integer", "description": "Random seed for noise", "default": 0},
                    "scale": {"type": "number", "description": "Noise scale factor", "default": 0.1},
                    "min_val": {"type": "number", "description": "Minimum noise value", "default": 0.0},
                    "max_val": {"type": "number", "description": "Maximum noise value", "default": 1.0}
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="randomize_colors",
            description="Randomize voxel colors within palette range",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "min_index": {"type": "integer", "description": "Minimum color index", "default": 1},
                    "max_index": {"type": "integer", "description": "Maximum color index", "default": 255}
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="optimize_palette",
            description="Remove unused palette colors and remap (optimize color usage)",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"}
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="list_models",
            description="List all .vox files in the vox directory",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls"""
    
    try:
        if name == "create_voxel_model":
            filename = arguments["filename"]
            width = arguments.get("width", 10)
            height = arguments.get("height", 10)
            depth = arguments.get("depth", 10)
            
            filepath = get_vox_path(filename)
            model = VoxelModel(width, height, depth)
            write_vox_file(filepath, model)
            
            return [TextContent(type="text", text=f"Created model '{filename}' with dimensions {width}x{height}x{depth}")]
        
        elif name == "read_voxel_model":
            filename = arguments["filename"]
            filepath = get_vox_path(filename)
            
            if not filepath.exists():
                return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
            
            model = read_vox_file(filepath)
            bounds = model.get_bounds()
            voxel_count = model.get_voxel_count()
            
            return [TextContent(type="text", text=f"Model '{filename}': {bounds[0]}x{bounds[1]}x{bounds[2]}, {voxel_count} voxels")]
        
        elif name == "place_voxel":
            filename = arguments["filename"]
            x = arguments["x"]
            y = arguments["y"]
            z = arguments["z"]
            color_index = arguments.get("color_index", 1)
            
            filepath = get_vox_path(filename)
            if not filepath.exists():
                return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
            
            model = read_vox_file(filepath)
            model.set_voxel(x, y, z, color_index)
            write_vox_file(filepath, model)
            
            return [TextContent(type="text", text=f"Placed voxel at ({x}, {y}, {z}) with color {color_index}")]
        
        elif name == "remove_voxel":
            filename = arguments["filename"]
            x = arguments["x"]
            y = arguments["y"]
            z = arguments["z"]
            
            filepath = get_vox_path(filename)
            if not filepath.exists():
                return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
            
            model = read_vox_file(filepath)
            model.remove_voxel(x, y, z)
            write_vox_file(filepath, model)
            
            return [TextContent(type="text", text=f"Removed voxel at ({x}, {y}, {z})")]
        
        elif name == "fill_box":
            filename = arguments["filename"]
            x1 = arguments["x1"]
            y1 = arguments["y1"]
            z1 = arguments["z1"]
            x2 = arguments["x2"]
            y2 = arguments["y2"]
            z2 = arguments["z2"]
            color_index = arguments.get("color_index", 1)
            
            filepath = get_vox_path(filename)
            if not filepath.exists():
                return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
            
            model = read_vox_file(filepath)
            model.fill_box(x1, y1, z1, x2, y2, z2, color_index)
            write_vox_file(filepath, model)
            
            return [TextContent(type="text", text=f"Filled box from ({x1}, {y1}, {z1}) to ({x2}, {y2}, {z2})")]
        
        elif name == "clear_region":
            filename = arguments["filename"]
            x1 = arguments["x1"]
            y1 = arguments["y1"]
            z1 = arguments["z1"]
            x2 = arguments["x2"]
            y2 = arguments["y2"]
            z2 = arguments["z2"]
            
            filepath = get_vox_path(filename)
            if not filepath.exists():
                return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
            
            model = read_vox_file(filepath)
            model.clear_region(x1, y1, z1, x2, y2, z2)
            write_vox_file(filepath, model)
            
            return [TextContent(type="text", text=f"Cleared region from ({x1}, {y1}, {z1}) to ({x2}, {y2}, {z2})")]
        
        elif name == "create_sphere":
            filename = arguments["filename"]
            center_x = arguments["center_x"]
            center_y = arguments["center_y"]
            center_z = arguments["center_z"]
            radius = arguments["radius"]
            color_index = arguments.get("color_index", 1)
            hollow = arguments.get("hollow", False)
            
            filepath = get_vox_path(filename)
            if not filepath.exists():
                model = VoxelModel(1, 1, 1)
                write_vox_file(filepath, model)
            
            model = read_vox_file(filepath)
            model.create_sphere(center_x, center_y, center_z, radius, color_index, hollow)
            write_vox_file(filepath, model)
            
            return [TextContent(type="text", text=f"Created sphere at ({center_x}, {center_y}, {center_z}) with radius {radius}")]
        
        elif name == "create_cylinder":
            filename = arguments["filename"]
            center_x = arguments["center_x"]
            center_y = arguments["center_y"]
            center_z = arguments["center_z"]
            radius = arguments["radius"]
            height = arguments["height"]
            axis = arguments.get("axis", "y")
            color_index = arguments.get("color_index", 1)
            hollow = arguments.get("hollow", False)
            
            filepath = get_vox_path(filename)
            if not filepath.exists():
                model = VoxelModel(1, 1, 1)
                write_vox_file(filepath, model)
            
            model = read_vox_file(filepath)
            model.create_cylinder(center_x, center_y, center_z, radius, height, axis, color_index, hollow)
            write_vox_file(filepath, model)
            
            return [TextContent(type="text", text=f"Created cylinder at ({center_x}, {center_y}, {center_z}) with radius {radius} and height {height}")]
        
        elif name == "create_pyramid":
            filename = arguments["filename"]
            base_x = arguments["base_x"]
            base_y = arguments["base_y"]
            base_z = arguments["base_z"]
            base_width = arguments["base_width"]
            base_depth = arguments["base_depth"]
            height = arguments["height"]
            color_index = arguments.get("color_index", 1)
            hollow = arguments.get("hollow", False)
            
            filepath = get_vox_path(filename)
            if not filepath.exists():
                model = VoxelModel(1, 1, 1)
                write_vox_file(filepath, model)
            
            model = read_vox_file(filepath)
            model.create_pyramid(base_x, base_y, base_z, base_width, base_depth, height, color_index, hollow)
            write_vox_file(filepath, model)
            
            return [TextContent(type="text", text=f"Created pyramid at ({base_x}, {base_y}, {base_z})")]
        
        elif name == "create_torus":
            filename = arguments["filename"]
            center_x = arguments["center_x"]
            center_y = arguments["center_y"]
            center_z = arguments["center_z"]
            major_radius = arguments["major_radius"]
            minor_radius = arguments["minor_radius"]
            axis = arguments.get("axis", "y")
            color_index = arguments.get("color_index", 1)
            hollow = arguments.get("hollow", False)
            
            filepath = get_vox_path(filename)
            if not filepath.exists():
                model = VoxelModel(1, 1, 1)
                write_vox_file(filepath, model)
            
            model = read_vox_file(filepath)
            model.create_torus(center_x, center_y, center_z, major_radius, minor_radius, axis, color_index, hollow)
            write_vox_file(filepath, model)
            
            return [TextContent(type="text", text=f"Created torus at ({center_x}, {center_y}, {center_z})")]
        
        elif name == "create_cone":
            filename = arguments["filename"]
            base_x = arguments["base_x"]
            base_y = arguments["base_y"]
            base_z = arguments["base_z"]
            base_radius = arguments["base_radius"]
            height = arguments["height"]
            axis = arguments.get("axis", "y")
            color_index = arguments.get("color_index", 1)
            hollow = arguments.get("hollow", False)
            
            filepath = get_vox_path(filename)
            if not filepath.exists():
                model = VoxelModel(1, 1, 1)
                write_vox_file(filepath, model)
            
            model = read_vox_file(filepath)
            model.create_cone(base_x, base_y, base_z, base_radius, height, axis, color_index, hollow)
            write_vox_file(filepath, model)
            
            return [TextContent(type="text", text=f"Created cone at ({base_x}, {base_y}, {base_z})")]
        
        elif name == "set_palette_color":
            filename = arguments["filename"]
            color_index = arguments["color_index"]
            r = arguments["r"]
            g = arguments["g"]
            b = arguments["b"]
            a = arguments.get("a", 255)
            
            filepath = get_vox_path(filename)
            if not filepath.exists():
                return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
            
            model = read_vox_file(filepath)
            model.set_palette_color(color_index, r, g, b, a)
            write_vox_file(filepath, model)
            
            return [TextContent(type="text", text=f"Set palette color {color_index} to RGBA({r}, {g}, {b}, {a})")]
        
        elif name == "replace_color":
            filename = arguments["filename"]
            old_color = arguments["old_color"]
            new_color = arguments["new_color"]
            
            filepath = get_vox_path(filename)
            if not filepath.exists():
                return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
            
            model = read_vox_file(filepath)
            model.replace_color(old_color, new_color)
            write_vox_file(filepath, model)
            
            return [TextContent(type="text", text=f"Replaced color {old_color} with {new_color}")]
        
        elif name == "get_voxel":
            filename = arguments["filename"]
            x = arguments["x"]
            y = arguments["y"]
            z = arguments["z"]
            
            filepath = get_vox_path(filename)
            if not filepath.exists():
                return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
            
            model = read_vox_file(filepath)
            color = model.get_voxel(x, y, z)
            
            return [TextContent(type="text", text=f"Voxel at ({x}, {y}, {z}) has color index {color}")]
        
        elif name == "get_palette":
            filename = arguments["filename"]
            filepath = get_vox_path(filename)
            
            if not filepath.exists():
                return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
            
            model = read_vox_file(filepath)
            palette_info = []
            for i, (r, g, b, a) in enumerate(model.palette):
                if i < 10 or (r, g, b) != (i % 256, i % 256, i % 256):  # Show first 10 and non-default colors
                    palette_info.append(f"  {i}: RGBA({r}, {g}, {b}, {a})")
            
            return [TextContent(type="text", text=f"Palette for '{filename}':\n" + "\n".join(palette_info[:20]))]
        
        elif name == "get_model_info":
            filename = arguments["filename"]
            filepath = get_vox_path(filename)
            
            if not filepath.exists():
                return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
            
            model = read_vox_file(filepath)
            bounds = model.get_bounds()
            voxel_count = model.get_voxel_count()
            
            return [TextContent(type="text", text=f"Model '{filename}':\n  Dimensions: {bounds[0]}x{bounds[1]}x{bounds[2]}\n  Voxel count: {voxel_count}")]
        
        elif name == "delete_model":
            filename = arguments["filename"]
            filepath = get_vox_path(filename)
            
            if not filepath.exists():
                return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
            
            filepath.unlink()
            return [TextContent(type="text", text=f"Deleted model '{filename}'")]
        
        elif name == "copy_model":
            source_filename = arguments["source_filename"]
            target_filename = arguments["target_filename"]
            
            source_path = get_vox_path(source_filename)
            target_path = get_vox_path(target_filename)
            
            if not source_path.exists():
                return [TextContent(type="text", text=f"Error: Source file '{source_filename}' not found")]
            
            model = read_vox_file(source_path)
            write_vox_file(target_path, model)
            
            return [TextContent(type="text", text=f"Copied '{source_filename}' to '{target_filename}'")]
        
        elif name == "take_snapshot":
            filename = arguments["filename"]
            snapshot_name = arguments.get("snapshot_name")
            
            source_path = get_vox_path(filename)
            if not source_path.exists():
                return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
            
            # Generate snapshot name if not provided
            if snapshot_name:
                if snapshot_name.endswith('.vox'):
                    snapshot_name = snapshot_name[:-4]
            else:
                base_name = filename.replace('.vox', '')
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                snapshot_name = f"{base_name}_snapshot_{timestamp}"
            
            target_path = get_vox_path(snapshot_name)
            
            model = read_vox_file(source_path)
            write_vox_file(target_path, model)
            
            # Render images from all 6 angles
            image_base_path = DEFAULT_EXPORT_DIR / snapshot_name
            image_results = render_model_all_angles(model, image_base_path)
            
            result_text = f"Snapshot saved as '{snapshot_name}.vox'"
            if image_results:
                result_text += f"\nImages saved from {len(image_results)} angles:"
                for angle, img_path in image_results.items():
                    result_text += f"\n  - {angle}: {img_path.name}"
            else:
                result_text += "\nNote: Image rendering requires Pillow (pip install Pillow)"
            
            return [TextContent(type="text", text=result_text)]
        
        elif name == "rotate_region":
            filename = arguments["filename"]
            x1, y1, z1 = arguments["x1"], arguments["y1"], arguments["z1"]
            x2, y2, z2 = arguments["x2"], arguments["y2"], arguments["z2"]
            center_x = arguments["center_x"]
            center_y = arguments["center_y"]
            center_z = arguments["center_z"]
            axis = arguments["axis"]
            degrees = arguments["degrees"]
            
            filepath = get_vox_path(filename)
            if not filepath.exists():
                return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
            
            model = read_vox_file(filepath)
            model.rotate_region(x1, y1, z1, x2, y2, z2, center_x, center_y, center_z, axis, degrees)
            write_vox_file(filepath, model)
            
            return [TextContent(type="text", text=f"Rotated region {degrees}° around {axis}-axis")]
        
        elif name == "mirror_region":
            filename = arguments["filename"]
            x1, y1, z1 = arguments["x1"], arguments["y1"], arguments["z1"]
            x2, y2, z2 = arguments["x2"], arguments["y2"], arguments["z2"]
            plane = arguments["plane"]
            position = arguments["position"]
            
            filepath = get_vox_path(filename)
            if not filepath.exists():
                return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
            
            model = read_vox_file(filepath)
            model.mirror_region(x1, y1, z1, x2, y2, z2, plane, position)
            write_vox_file(filepath, model)
            
            return [TextContent(type="text", text=f"Mirrored region across {plane}={position} plane")]
        
        elif name == "copy_region":
            filename = arguments["filename"]
            x1, y1, z1 = arguments["x1"], arguments["y1"], arguments["z1"]
            x2, y2, z2 = arguments["x2"], arguments["y2"], arguments["z2"]
            target_x = arguments["target_x"]
            target_y = arguments["target_y"]
            target_z = arguments["target_z"]
            
            filepath = get_vox_path(filename)
            if not filepath.exists():
                return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
            
            model = read_vox_file(filepath)
            model.copy_region(x1, y1, z1, x2, y2, z2, target_x, target_y, target_z)
            write_vox_file(filepath, model)
            
            return [TextContent(type="text", text=f"Copied region to ({target_x}, {target_y}, {target_z})")]
        
        elif name == "extrude_region":
            filename = arguments["filename"]
            x1, y1, z1 = arguments["x1"], arguments["y1"], arguments["z1"]
            x2, y2, z2 = arguments["x2"], arguments["y2"], arguments["z2"]
            direction = arguments["direction"]
            distance = arguments["distance"]
            color_index = arguments.get("color_index")
            
            filepath = get_vox_path(filename)
            if not filepath.exists():
                return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
            
            model = read_vox_file(filepath)
            model.extrude_region(x1, y1, z1, x2, y2, z2, direction, distance, color_index)
            write_vox_file(filepath, model)
            
            return [TextContent(type="text", text=f"Extruded region {distance} units in {direction} direction")]
        
        elif name == "find_connected_components":
            filename = arguments["filename"]
            filepath = get_vox_path(filename)
            
            if not filepath.exists():
                return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
            
            model = read_vox_file(filepath)
            components = model.find_connected_components()
            
            result_text = f"Found {len(components)} connected component(s):\n"
            for i, comp in enumerate(components, 1):
                result_text += f"  Component {i}: {comp['voxel_count']} voxels, bounds {comp['bounds']}\n"
            
            return [TextContent(type="text", text=result_text)]
        
        elif name == "get_surface_voxels":
            filename = arguments["filename"]
            filepath = get_vox_path(filename)
            
            if not filepath.exists():
                return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
            
            model = read_vox_file(filepath)
            surface = model.get_surface_voxels()
            
            return [TextContent(type="text", text=f"Found {len(surface)} surface voxels (exposed faces)")]
        
        elif name == "subtract_region":
            filename = arguments["filename"]
            x1, y1, z1 = arguments["x1"], arguments["y1"], arguments["z1"]
            x2, y2, z2 = arguments["x2"], arguments["y2"], arguments["z2"]
            
            filepath = get_vox_path(filename)
            if not filepath.exists():
                return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
            
            model = read_vox_file(filepath)
            model.subtract_region(x1, y1, z1, x2, y2, z2)
            write_vox_file(filepath, model)
            
            return [TextContent(type="text", text=f"Subtracted region from ({x1}, {y1}, {z1}) to ({x2}, {y2}, {z2})")]
        
        elif name == "union_models":
            target_filename = arguments["target_filename"]
            source_filename = arguments["source_filename"]
            offset_x = arguments.get("offset_x", 0)
            offset_y = arguments.get("offset_y", 0)
            offset_z = arguments.get("offset_z", 0)
            
            target_path = get_vox_path(target_filename)
            source_path = get_vox_path(source_filename)
            
            if not target_path.exists():
                return [TextContent(type="text", text=f"Error: Target file '{target_filename}' not found")]
            if not source_path.exists():
                return [TextContent(type="text", text=f"Error: Source file '{source_filename}' not found")]
            
            target_model = read_vox_file(target_path)
            source_model = read_vox_file(source_path)
            target_model.union_with_model(source_model, offset_x, offset_y, offset_z)
            write_vox_file(target_path, target_model)
            
            return [TextContent(type="text", text=f"Combined '{source_filename}' into '{target_filename}' with offset ({offset_x}, {offset_y}, {offset_z})")]
        
        elif name == "intersect_region":
            filename = arguments["filename"]
            x1, y1, z1 = arguments["x1"], arguments["y1"], arguments["z1"]
            x2, y2, z2 = arguments["x2"], arguments["y2"], arguments["z2"]
            
            filepath = get_vox_path(filename)
            if not filepath.exists():
                return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
            
            model = read_vox_file(filepath)
            before_count = model.get_voxel_count()
            model.intersect_region(x1, y1, z1, x2, y2, z2)
            after_count = model.get_voxel_count()
            write_vox_file(filepath, model)
            
            return [TextContent(type="text", text=f"Intersected region: kept {after_count} voxels (removed {before_count - after_count})")]
        
        elif name == "scale_model":
            filename = arguments["filename"]
            factor = arguments.get("factor", 2.0)
            factor_x = arguments.get("factor_x", factor)
            factor_y = arguments.get("factor_y", factor)
            factor_z = arguments.get("factor_z", factor)
            
            filepath = get_vox_path(filename)
            if not filepath.exists():
                return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
            
            model = read_vox_file(filepath)
            model.scale_model(factor_x, factor_y, factor_z)
            write_vox_file(filepath, model)
            
            return [TextContent(type="text", text=f"Scaled model by ({factor_x}, {factor_y}, {factor_z})")]
        
        elif name == "dilate":
            filename = arguments["filename"]
            iterations = arguments.get("iterations", 1)
            
            filepath = get_vox_path(filename)
            if not filepath.exists():
                return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
            
            model = read_vox_file(filepath)
            model.dilate(iterations)
            write_vox_file(filepath, model)
            
            return [TextContent(type="text", text=f"Dilated model {iterations} time(s)")]
        
        elif name == "erode":
            filename = arguments["filename"]
            iterations = arguments.get("iterations", 1)
            
            filepath = get_vox_path(filename)
            if not filepath.exists():
                return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
            
            model = read_vox_file(filepath)
            model.erode(iterations)
            write_vox_file(filepath, model)
            
            return [TextContent(type="text", text=f"Eroded model {iterations} time(s)")]
        
        elif name == "flood_fill":
            filename = arguments["filename"]
            color_index = arguments.get("color_index", 0)
            
            filepath = get_vox_path(filename)
            if not filepath.exists():
                return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
            
            model = read_vox_file(filepath)
            model.flood_fill(color_index)
            write_vox_file(filepath, model)
            
            action = "removed hollow spaces" if color_index == 0 else f"filled with color {color_index}"
            return [TextContent(type="text", text=f"Flood fill: {action}")]
        
        elif name == "shell":
            filename = arguments["filename"]
            filepath = get_vox_path(filename)
            
            if not filepath.exists():
                return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
            
            model = read_vox_file(filepath)
            before_count = model.get_voxel_count()
            model.shell()
            after_count = model.get_voxel_count()
            write_vox_file(filepath, model)
            
            return [TextContent(type="text", text=f"Shell operation: {after_count} surface voxels (removed {before_count - after_count} interior)")]
        
        elif name == "invert":
            filename = arguments["filename"]
            filepath = get_vox_path(filename)
            
            if not filepath.exists():
                return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
            
            model = read_vox_file(filepath)
            model.invert()
            write_vox_file(filepath, model)
            
            return [TextContent(type="text", text="Inverted model (swapped solid/empty space)")]
        
        elif name == "shrink":
            filename = arguments["filename"]
            filepath = get_vox_path(filename)
            
            if not filepath.exists():
                return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
            
            model = read_vox_file(filepath)
            old_bounds = model.get_bounds()
            model.shrink()
            new_bounds = model.get_bounds()
            write_vox_file(filepath, model)
            
            return [TextContent(type="text", text=f"Shrunk bounds from {old_bounds} to {new_bounds}")]
        
        elif name == "repeat_pattern":
            filename = arguments["filename"]
            count_x = arguments.get("count_x", 2)
            count_y = arguments.get("count_y", 1)
            count_z = arguments.get("count_z", 1)
            mirror = arguments.get("mirror", False)
            
            filepath = get_vox_path(filename)
            if not filepath.exists():
                return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
            
            model = read_vox_file(filepath)
            model.repeat_pattern(count_x, count_y, count_z, mirror)
            write_vox_file(filepath, model)
            
            return [TextContent(type="text", text=f"Repeated pattern {count_x}x{count_y}x{count_z} times")]
        
        elif name == "apply_noise":
            filename = arguments["filename"]
            seed = arguments.get("seed", 0)
            scale = arguments.get("scale", 0.1)
            min_val = arguments.get("min_val", 0.0)
            max_val = arguments.get("max_val", 1.0)
            
            filepath = get_vox_path(filename)
            if not filepath.exists():
                return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
            
            model = read_vox_file(filepath)
            model.apply_noise(seed, scale, min_val, max_val)
            write_vox_file(filepath, model)
            
            return [TextContent(type="text", text=f"Applied noise with seed {seed}")]
        
        elif name == "randomize_colors":
            filename = arguments["filename"]
            min_index = arguments.get("min_index", 1)
            max_index = arguments.get("max_index", 255)
            
            filepath = get_vox_path(filename)
            if not filepath.exists():
                return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
            
            model = read_vox_file(filepath)
            model.randomize_colors(min_index, max_index)
            write_vox_file(filepath, model)
            
            return [TextContent(type="text", text=f"Randomized colors between {min_index} and {max_index}")]
        
        elif name == "optimize_palette":
            filename = arguments["filename"]
            filepath = get_vox_path(filename)
            
            if not filepath.exists():
                return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
            
            model = read_vox_file(filepath)
            before_colors = len(set(model.voxels.values()))
            model.optimize_palette()
            after_colors = len(set(model.voxels.values()))
            write_vox_file(filepath, model)
            
            return [TextContent(type="text", text=f"Optimized palette: {after_colors} colors (removed {before_colors - after_colors} unused)")]
        
        elif name == "list_models":
            vox_files = sorted(DEFAULT_VOX_DIR.glob("*.vox"))
            if not vox_files:
                return [TextContent(type="text", text="No .vox files found in vox directory")]
            
            file_list = "\n".join([f"  - {f.name}" for f in vox_files])
            return [TextContent(type="text", text=f"Found {len(vox_files)} .vox files:\n{file_list}")]
        
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    """Run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
