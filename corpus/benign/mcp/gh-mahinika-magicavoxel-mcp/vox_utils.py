"""
Utility functions for working with .vox files
Handles reading, writing, and manipulating MagicaVoxel .vox format
"""

import struct
from typing import List, Tuple, Optional, Dict
from pathlib import Path

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class VoxelModel:
    """Represents a voxel model"""
    
    def __init__(self, size_x: int = 0, size_y: int = 0, size_z: int = 0):
        self.size_x = size_x
        self.size_y = size_y
        self.size_z = size_z
        self.voxels: dict[Tuple[int, int, int], int] = {}  # (x, y, z) -> color_index
        self.palette = self._default_palette()
    
    def _default_palette(self) -> List[Tuple[int, int, int, int]]:
        """Default MagicaVoxel palette (RGBA)"""
        # First color is always transparent
        palette = [(0, 0, 0, 0)]
        # Add some basic colors
        basic_colors = [
            (255, 255, 255, 255),  # White
            (255, 0, 0, 255),      # Red
            (0, 255, 0, 255),      # Green
            (0, 0, 255, 255),      # Blue
            (255, 255, 0, 255),    # Yellow
            (255, 0, 255, 255),    # Magenta
            (0, 255, 255, 255),    # Cyan
        ]
        palette.extend(basic_colors)
        # Fill rest with grayscale
        for i in range(8, 256):
            gray = i % 256
            palette.append((gray, gray, gray, 255))
        return palette
    
    def set_voxel(self, x: int, y: int, z: int, color_index: int):
        """Set a voxel at position (x, y, z) with color index"""
        # Allow placing voxels up to 255 (max for .vox format)
        # Don't restrict to model size since we want to support large models
        if 0 <= x <= 255 and 0 <= y <= 255 and 0 <= z <= 255:
            if color_index > 0:  # 0 is transparent
                self.voxels[(x, y, z)] = color_index
            elif (x, y, z) in self.voxels:
                del self.voxels[(x, y, z)]
    
    def get_voxel(self, x: int, y: int, z: int) -> int:
        """Get color index at position (x, y, z), returns 0 if empty"""
        return self.voxels.get((x, y, z), 0)
    
    def remove_voxel(self, x: int, y: int, z: int):
        """Remove a voxel at position (x, y, z)"""
        if (x, y, z) in self.voxels:
            del self.voxels[(x, y, z)]
    
    def fill_box(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int, color_index: int):
        """Fill a box region with voxels"""
        for x in range(min(x1, x2), max(x1, x2) + 1):
            for y in range(min(y1, y2), max(y1, y2) + 1):
                for z in range(min(z1, z2), max(z1, z2) + 1):
                    self.set_voxel(x, y, z, color_index)
    
    def get_voxel_count(self) -> int:
        """Get total number of voxels"""
        return len(self.voxels)
    
    def get_bounds(self) -> Tuple[int, int, int]:
        """Get actual bounds of the model"""
        if not self.voxels:
            return (0, 0, 0)
        xs = [x for x, y, z in self.voxels.keys()]
        ys = [y for x, y, z in self.voxels.keys()]
        zs = [z for x, y, z in self.voxels.keys()]
        return (max(xs) + 1, max(ys) + 1, max(zs) + 1)
    
    def create_sphere(self, center_x: int, center_y: int, center_z: int, radius: int, color_index: int, hollow: bool = False):
        """Create a sphere at the specified center with given radius"""
        radius_sq = radius * radius
        for x in range(center_x - radius, center_x + radius + 1):
            for y in range(center_y - radius, center_y + radius + 1):
                for z in range(center_z - radius, center_z + radius + 1):
                    dx = x - center_x
                    dy = y - center_y
                    dz = z - center_z
                    dist_sq = dx*dx + dy*dy + dz*dz
                    
                    if hollow:
                        # Hollow sphere: only place voxels on the surface
                        if abs(dist_sq - radius_sq) <= radius:
                            self.set_voxel(x, y, z, color_index)
                    else:
                        # Solid sphere
                        if dist_sq <= radius_sq:
                            self.set_voxel(x, y, z, color_index)
    
    def create_cylinder(self, center_x: int, center_y: int, center_z: int, radius: int, height: int, 
                       axis: str = 'y', color_index: int = 1, hollow: bool = False):
        """Create a cylinder. Axis can be 'x', 'y', or 'z'"""
        radius_sq = radius * radius
        
        if axis == 'y':
            for y in range(center_y, center_y + height):
                for x in range(center_x - radius, center_x + radius + 1):
                    for z in range(center_z - radius, center_z + radius + 1):
                        dx = x - center_x
                        dz = z - center_z
                        dist_sq = dx*dx + dz*dz
                        if hollow:
                            if abs(dist_sq - radius_sq) <= radius:
                                self.set_voxel(x, y, z, color_index)
                        else:
                            if dist_sq <= radius_sq:
                                self.set_voxel(x, y, z, color_index)
        elif axis == 'x':
            for x in range(center_x, center_x + height):
                for y in range(center_y - radius, center_y + radius + 1):
                    for z in range(center_z - radius, center_z + radius + 1):
                        dy = y - center_y
                        dz = z - center_z
                        dist_sq = dy*dy + dz*dz
                        if hollow:
                            if abs(dist_sq - radius_sq) <= radius:
                                self.set_voxel(x, y, z, color_index)
                        else:
                            if dist_sq <= radius_sq:
                                self.set_voxel(x, y, z, color_index)
        else:  # axis == 'z'
            for z in range(center_z, center_z + height):
                for x in range(center_x - radius, center_x + radius + 1):
                    for y in range(center_y - radius, center_y + radius + 1):
                        dx = x - center_x
                        dy = y - center_y
                        dist_sq = dx*dx + dy*dy
                        if hollow:
                            if abs(dist_sq - radius_sq) <= radius:
                                self.set_voxel(x, y, z, color_index)
                        else:
                            if dist_sq <= radius_sq:
                                self.set_voxel(x, y, z, color_index)
    
    def create_pyramid(self, base_x: int, base_y: int, base_z: int, base_width: int, base_depth: int, 
                     height: int, color_index: int = 1, hollow: bool = False):
        """Create a pyramid with rectangular base"""
        for y in range(height):
            current_width = int(base_width * (1 - y / height))
            current_depth = int(base_depth * (1 - y / height))
            if current_width < 1:
                current_width = 1
            if current_depth < 1:
                current_depth = 1
            
            offset_x = (base_width - current_width) // 2
            offset_z = (base_depth - current_depth) // 2
            
            if hollow and y < height - 1:
                # Hollow: only outline
                for x in range(base_x + offset_x, base_x + offset_x + current_width):
                    self.set_voxel(x, base_y + y, base_z + offset_z, color_index)
                    self.set_voxel(x, base_y + y, base_z + offset_z + current_depth - 1, color_index)
                for z in range(base_z + offset_z, base_z + offset_z + current_depth):
                    self.set_voxel(base_x + offset_x, base_y + y, z, color_index)
                    self.set_voxel(base_x + offset_x + current_width - 1, base_y + y, z, color_index)
            else:
                # Solid: fill the layer
                for x in range(base_x + offset_x, base_x + offset_x + current_width):
                    for z in range(base_z + offset_z, base_z + offset_z + current_depth):
                        self.set_voxel(x, base_y + y, z, color_index)
    
    def replace_color(self, old_color: int, new_color: int):
        """Replace all voxels of one color with another"""
        for pos in list(self.voxels.keys()):
            if self.voxels[pos] == old_color:
                self.voxels[pos] = new_color
    
    def set_palette_color(self, color_index: int, r: int, g: int, b: int, a: int = 255):
        """Set a specific palette color"""
        if 0 <= color_index < 256:
            self.palette[color_index] = (r, g, b, a)
    
    def count_colors(self) -> dict:
        """Count voxels by color index"""
        color_counts = {}
        for color_idx in self.voxels.values():
            color_counts[color_idx] = color_counts.get(color_idx, 0) + 1
        return color_counts
    
    def copy_region(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int, 
                   target_x: int, target_y: int, target_z: int, overwrite: bool = True):
        """Copy a region to another location"""
        source_voxels = {}
        for x in range(min(x1, x2), max(x1, x2) + 1):
            for y in range(min(y1, y2), max(y1, y2) + 1):
                for z in range(min(z1, z2), max(z1, z2) + 1):
                    if (x, y, z) in self.voxels:
                        source_voxels[(x, y, z)] = self.voxels[(x, y, z)]
        
        # Calculate offset
        offset_x = target_x - min(x1, x2)
        offset_y = target_y - min(y1, y2)
        offset_z = target_z - min(z1, z2)
        
        # Copy voxels
        for (x, y, z), color_idx in source_voxels.items():
            new_x = x + offset_x
            new_y = y + offset_y
            new_z = z + offset_z
            if overwrite or (new_x, new_y, new_z) not in self.voxels:
                self.set_voxel(new_x, new_y, new_z, color_idx)
    
    def create_stairs(self, start_x: int, start_y: int, start_z: int, width: int, depth: int, 
                     num_steps: int, step_height: int = 1, color_index: int = 1):
        """Create a staircase"""
        for step in range(num_steps):
            step_y = start_y + (step * step_height)
            step_z = start_z + (step * depth)
            self.fill_box(start_x, step_y, step_z, 
                         start_x + width - 1, step_y + step_height - 1, step_z + depth - 1, 
                         color_index)
    
    def create_wall(self, start_x: int, start_y: int, start_z: int, length: int, height: int, 
                   direction: str = 'x', thickness: int = 1, color_index: int = 1):
        """Create a wall. Direction can be 'x' or 'z'"""
        if direction == 'x':
            self.fill_box(start_x, start_y, start_z, 
                         start_x + length - 1, start_y + height - 1, start_z + thickness - 1, 
                         color_index)
        else:  # direction == 'z'
            self.fill_box(start_x, start_y, start_z, 
                         start_x + thickness - 1, start_y + height - 1, start_z + length - 1, 
                         color_index)
    
    def clear_region(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int):
        """Remove all voxels in a box region"""
        for x in range(min(x1, x2), max(x1, x2) + 1):
            for y in range(min(y1, y2), max(y1, y2) + 1):
                for z in range(min(z1, z2), max(z1, z2) + 1):
                    if (x, y, z) in self.voxels:
                        del self.voxels[(x, y, z)]
    
    def create_torus(self, center_x: int, center_y: int, center_z: int, 
                     major_radius: int, minor_radius: int, 
                     axis: str = 'y', color_index: int = 1, hollow: bool = False):
        """Create a torus (donut). Major radius is distance from center to tube center,
        minor radius is tube radius. Axis can be 'x', 'y', or 'z'."""
        major_r_sq = major_radius * major_radius
        minor_r_sq = minor_radius * minor_radius
        
        # Bounding box
        max_r = major_radius + minor_radius
        
        if axis == 'y':
            for x in range(center_x - max_r, center_x + max_r + 1):
                for y in range(center_y - minor_radius, center_y + minor_radius + 1):
                    for z in range(center_z - max_r, center_z + max_r + 1):
                        dx = x - center_x
                        dz = z - center_z
                        dist_from_center = (dx*dx + dz*dz) ** 0.5
                        if dist_from_center == 0:
                            continue
                        
                        # Distance from torus center circle
                        dist_from_torus_center = abs(dist_from_center - major_radius)
                        dy = y - center_y
                        
                        dist_sq = dist_from_torus_center * dist_from_torus_center + dy * dy
                        
                        if hollow:
                            if abs(dist_sq - minor_r_sq) <= minor_radius:
                                self.set_voxel(x, y, z, color_index)
                        else:
                            if dist_sq <= minor_r_sq:
                                self.set_voxel(x, y, z, color_index)
        elif axis == 'x':
            for x in range(center_x - minor_radius, center_x + minor_radius + 1):
                for y in range(center_y - max_r, center_y + max_r + 1):
                    for z in range(center_z - max_r, center_z + max_r + 1):
                        dy = y - center_y
                        dz = z - center_z
                        dist_from_center = (dy*dy + dz*dz) ** 0.5
                        if dist_from_center == 0:
                            continue
                        
                        dist_from_torus_center = abs(dist_from_center - major_radius)
                        dx = x - center_x
                        
                        dist_sq = dist_from_torus_center * dist_from_torus_center + dx * dx
                        
                        if hollow:
                            if abs(dist_sq - minor_r_sq) <= minor_radius:
                                self.set_voxel(x, y, z, color_index)
                        else:
                            if dist_sq <= minor_r_sq:
                                self.set_voxel(x, y, z, color_index)
        else:  # axis == 'z'
            for x in range(center_x - max_r, center_x + max_r + 1):
                for y in range(center_y - max_r, center_y + max_r + 1):
                    for z in range(center_z - minor_radius, center_z + minor_radius + 1):
                        dx = x - center_x
                        dy = y - center_y
                        dist_from_center = (dx*dx + dy*dy) ** 0.5
                        if dist_from_center == 0:
                            continue
                        
                        dist_from_torus_center = abs(dist_from_center - major_radius)
                        dz = z - center_z
                        
                        dist_sq = dist_from_torus_center * dist_from_torus_center + dz * dz
                        
                        if hollow:
                            if abs(dist_sq - minor_r_sq) <= minor_radius:
                                self.set_voxel(x, y, z, color_index)
                        else:
                            if dist_sq <= minor_r_sq:
                                self.set_voxel(x, y, z, color_index)
    
    def create_cone(self, base_x: int, base_y: int, base_z: int,
                    base_radius: int, height: int,
                    axis: str = 'y', color_index: int = 1, hollow: bool = False):
        """Create a cone. Axis can be 'x', 'y', or 'z'."""
        if axis == 'y':
            for y in range(height):
                current_radius = int(base_radius * (1 - y / height))
                if current_radius < 1:
                    current_radius = 1
                
                radius_sq = current_radius * current_radius
                
                for x in range(base_x - base_radius, base_x + base_radius + 1):
                    for z in range(base_z - base_radius, base_z + base_radius + 1):
                        dx = x - base_x
                        dz = z - base_z
                        dist_sq = dx*dx + dz*dz
                        
                        if hollow and y < height - 1:
                            # Only surface
                            if abs(dist_sq - radius_sq) <= current_radius:
                                self.set_voxel(x, base_y + y, z, color_index)
                        else:
                            if dist_sq <= radius_sq:
                                self.set_voxel(x, base_y + y, z, color_index)
        elif axis == 'x':
            for x in range(height):
                current_radius = int(base_radius * (1 - x / height))
                if current_radius < 1:
                    current_radius = 1
                
                radius_sq = current_radius * current_radius
                
                for y in range(base_y - base_radius, base_y + base_radius + 1):
                    for z in range(base_z - base_radius, base_z + base_radius + 1):
                        dy = y - base_y
                        dz = z - base_z
                        dist_sq = dy*dy + dz*dz
                        
                        if hollow and x < height - 1:
                            if abs(dist_sq - radius_sq) <= current_radius:
                                self.set_voxel(base_x + x, y, z, color_index)
                        else:
                            if dist_sq <= radius_sq:
                                self.set_voxel(base_x + x, y, z, color_index)
        else:  # axis == 'z'
            for z in range(height):
                current_radius = int(base_radius * (1 - z / height))
                if current_radius < 1:
                    current_radius = 1
                
                radius_sq = current_radius * current_radius
                
                for x in range(base_x - base_radius, base_x + base_radius + 1):
                    for y in range(base_y - base_radius, base_y + base_radius + 1):
                        dx = x - base_x
                        dy = y - base_y
                        dist_sq = dx*dx + dy*dy
                        
                        if hollow and z < height - 1:
                            if abs(dist_sq - radius_sq) <= current_radius:
                                self.set_voxel(x, y, base_z + z, color_index)
                        else:
                            if dist_sq <= radius_sq:
                                self.set_voxel(x, y, base_z + z, color_index)
    
    def rotate_region(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int,
                      center_x: int, center_y: int, center_z: int,
                      axis: str, degrees: int):
        """Rotate a region around a center point. Degrees: 90, 180, or 270."""
        # Extract region voxels
        region_voxels = {}
        for x in range(min(x1, x2), max(x1, x2) + 1):
            for y in range(min(y1, y2), max(y1, y2) + 1):
                for z in range(min(z1, z2), max(z1, z2) + 1):
                    if (x, y, z) in self.voxels:
                        region_voxels[(x, y, z)] = self.voxels[(x, y, z)]
        
        # Clear original region
        for pos in region_voxels:
            del self.voxels[pos]
        
        # Rotate and place
        for (x, y, z), color in region_voxels.items():
            # Translate to origin
            dx = x - center_x
            dy = y - center_y
            dz = z - center_z
            
            # Rotate based on axis and degrees
            if axis == 'x':
                if degrees == 90:
                    new_x, new_y, new_z = dx, -dz, dy
                elif degrees == 180:
                    new_x, new_y, new_z = dx, -dy, -dz
                elif degrees == 270:
                    new_x, new_y, new_z = dx, dz, -dy
                else:
                    continue
            elif axis == 'y':
                if degrees == 90:
                    new_x, new_y, new_z = dz, dy, -dx
                elif degrees == 180:
                    new_x, new_y, new_z = -dx, dy, -dz
                elif degrees == 270:
                    new_x, new_y, new_z = -dz, dy, dx
                else:
                    continue
            else:  # axis == 'z'
                if degrees == 90:
                    new_x, new_y, new_z = -dy, dx, dz
                elif degrees == 180:
                    new_x, new_y, new_z = -dx, -dy, dz
                elif degrees == 270:
                    new_x, new_y, new_z = dy, -dx, dz
                else:
                    continue
            
            # Translate back
            new_x += center_x
            new_y += center_y
            new_z += center_z
            
            self.set_voxel(new_x, new_y, new_z, color)
    
    def mirror_region(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int,
                     plane: str, position: int):
        """Mirror a region across a plane. Plane: 'x', 'y', or 'z'. Position is the plane coordinate."""
        # Extract region voxels
        region_voxels = {}
        for x in range(min(x1, x2), max(x1, x2) + 1):
            for y in range(min(y1, y2), max(y1, y2) + 1):
                for z in range(min(z1, z2), max(z1, z2) + 1):
                    if (x, y, z) in self.voxels:
                        region_voxels[(x, y, z)] = self.voxels[(x, y, z)]
        
        # Mirror and place (set_voxel already checks bounds 0-255)
        for (x, y, z), color in region_voxels.items():
            if plane == 'x':
                new_x = 2 * position - x
                new_y, new_z = y, z
            elif plane == 'y':
                new_y = 2 * position - y
                new_x, new_z = x, z
            else:  # plane == 'z'
                new_z = 2 * position - z
                new_x, new_y = x, y
            
            # set_voxel checks bounds (0-255), so this is safe
            self.set_voxel(new_x, new_y, new_z, color)
    
    def find_connected_components(self) -> List[Dict]:
        """Find all connected components (separate pieces) in the model.
        Returns list of components, each with voxel count and bounding box."""
        visited = set()
        components = []
        
        for pos in self.voxels.keys():
            if pos in visited:
                continue
            
            # BFS to find connected component
            component_voxels = []
            queue = [pos]
            visited.add(pos)
            
            while queue:
                x, y, z = queue.pop(0)
                component_voxels.append((x, y, z))
                
                # Check 6 neighbors
                for dx, dy, dz in [(1,0,0), (-1,0,0), (0,1,0), (0,-1,0), (0,0,1), (0,0,-1)]:
                    neighbor = (x+dx, y+dy, z+dz)
                    if neighbor in self.voxels and neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)
            
            # Calculate bounding box
            xs = [x for x, y, z in component_voxels]
            ys = [y for x, y, z in component_voxels]
            zs = [z for x, y, z in component_voxels]
            
            components.append({
                "voxel_count": len(component_voxels),
                "bounds": {
                    "min_x": min(xs), "max_x": max(xs),
                    "min_y": min(ys), "max_y": max(ys),
                    "min_z": min(zs), "max_z": max(zs)
                }
            })
        
        return components
    
    def get_surface_voxels(self) -> List[Tuple[int, int, int]]:
        """Get all surface voxels (voxels with at least one exposed face)"""
        surface = []
        for (x, y, z) in self.voxels.keys():
            # Check 6 neighbors
            is_surface = False
            for dx, dy, dz in [(1,0,0), (-1,0,0), (0,1,0), (0,-1,0), (0,0,1), (0,0,-1)]:
                neighbor = (x+dx, y+dy, z+dz)
                if neighbor not in self.voxels:
                    is_surface = True
                    break
            if is_surface:
                surface.append((x, y, z))
        return surface
    
    def subtract_region(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int):
        """Remove all voxels in a region (boolean subtract)"""
        for x in range(min(x1, x2), max(x1, x2) + 1):
            for y in range(min(y1, y2), max(y1, y2) + 1):
                for z in range(min(z1, z2), max(z1, z2) + 1):
                    if (x, y, z) in self.voxels:
                        del self.voxels[(x, y, z)]
    
    def union_with_model(self, other_model: 'VoxelModel', offset_x: int = 0, offset_y: int = 0, offset_z: int = 0):
        """Combine this model with another model (boolean union)"""
        for (x, y, z), color in other_model.voxels.items():
            self.set_voxel(x + offset_x, y + offset_y, z + offset_z, color)
    
    def intersect_region(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int):
        """Keep only voxels within the specified region (boolean intersect)"""
        to_remove = []
        for (x, y, z) in self.voxels.keys():
            if not (min(x1, x2) <= x <= max(x1, x2) and
                    min(y1, y2) <= y <= max(y1, y2) and
                    min(z1, z2) <= z <= max(z1, z2)):
                to_remove.append((x, y, z))
        for pos in to_remove:
            del self.voxels[pos]
    
    def scale_model(self, factor_x: float = 1.0, factor_y: float = 1.0, factor_z: float = 1.0):
        """Scale the model by factors (can be non-uniform)"""
        if factor_x == 1.0 and factor_y == 1.0 and factor_z == 1.0:
            return
        
        new_voxels = {}
        for (x, y, z), color in self.voxels.items():
            new_x = int(x * factor_x)
            new_y = int(y * factor_y)
            new_z = int(z * factor_z)
            new_voxels[(new_x, new_y, new_z)] = color
        
        self.voxels = new_voxels
        self.size_x = int(self.size_x * factor_x)
        self.size_y = int(self.size_y * factor_y)
        self.size_z = int(self.size_z * factor_z)
    
    def dilate(self, iterations: int = 1):
        """Dilate: expand surface voxels outward (adds layers)"""
        for _ in range(iterations):
            new_voxels = dict(self.voxels)
            for (x, y, z) in self.voxels.keys():
                # Add neighbors
                for dx, dy, dz in [(1,0,0), (-1,0,0), (0,1,0), (0,-1,0), (0,0,1), (0,0,-1)]:
                    nx, ny, nz = x + dx, y + dy, z + dz
                    if (nx, ny, nz) not in self.voxels:
                        new_voxels[(nx, ny, nz)] = self.voxels[(x, y, z)]
            self.voxels = new_voxels
    
    def erode(self, iterations: int = 1):
        """Erode: remove surface voxels (shrinks model)"""
        for _ in range(iterations):
            to_remove = []
            for (x, y, z) in self.voxels.keys():
                # Check if all neighbors exist (not a surface voxel)
                all_neighbors = True
                for dx, dy, dz in [(1,0,0), (-1,0,0), (0,1,0), (0,-1,0), (0,0,1), (0,0,-1)]:
                    if (x + dx, y + dy, z + dz) not in self.voxels:
                        all_neighbors = False
                        break
                if all_neighbors:
                    to_remove.append((x, y, z))
            for pos in to_remove:
                del self.voxels[pos]
    
    def flood_fill(self, color_index: int = 0):
        """Fill all hollow interior spaces with color (or remove if color_index=0)"""
        if not self.voxels:
            return
        
        bounds = self.get_bounds()
        # Find all empty spaces that are completely enclosed
        visited = set()
        to_fill = []
        
        # Start from all surface voxels and flood fill outward
        surface = self.get_surface_voxels()
        for (x, y, z) in surface:
            # Check each empty neighbor
            for dx, dy, dz in [(1,0,0), (-1,0,0), (0,1,0), (0,-1,0), (0,0,1), (0,0,-1)]:
                nx, ny, nz = x + dx, y + dy, z + dz
                if (nx, ny, nz) not in self.voxels and (nx, ny, nz) not in visited:
                    # Check if this empty space is enclosed
                    if 0 <= nx < bounds[0] and 0 <= ny < bounds[1] and 0 <= nz < bounds[2]:
                        # Simple flood fill to check if enclosed
                        enclosed = True
                        fill_region = []
                        stack = [(nx, ny, nz)]
                        local_visited = set()
                        
                        while stack:
                            cx, cy, cz = stack.pop()
                            if (cx, cy, cz) in local_visited:
                                continue
                            local_visited.add((cx, cy, cz))
                            fill_region.append((cx, cy, cz))
                            
                            # Check boundaries
                            if not (0 <= cx < bounds[0] and 0 <= cy < bounds[1] and 0 <= cz < bounds[2]):
                                enclosed = False
                                break
                            
                            # Add neighbors
                            for ndx, ndy, ndz in [(1,0,0), (-1,0,0), (0,1,0), (0,-1,0), (0,0,1), (0,0,-1)]:
                                nnx, nny, nnz = cx + ndx, cy + ndy, cz + ndz
                                if (nnx, nny, nnz) not in self.voxels and (nnx, nny, nnz) not in local_visited:
                                    stack.append((nnx, nny, nnz))
                        
                        if enclosed:
                            to_fill.extend(fill_region)
                            visited.update(local_visited)
        
        # Fill or remove
        for pos in to_fill:
            if color_index == 0:
                # Already empty, skip
                pass
            else:
                self.set_voxel(pos[0], pos[1], pos[2], color_index)
    
    def shell(self):
        """Remove all interior voxels, keep only surface (hull)"""
        surface = self.get_surface_voxels()
        surface_set = set(surface)
        to_remove = [pos for pos in self.voxels.keys() if pos not in surface_set]
        for pos in to_remove:
            del self.voxels[pos]
    
    def invert(self):
        """Invert: swap solid and empty space within bounds"""
        bounds = self.get_bounds()
        new_voxels = {}
        for x in range(bounds[0]):
            for y in range(bounds[1]):
                for z in range(bounds[2]):
                    if (x, y, z) not in self.voxels:
                        # Was empty, make solid (use color 1)
                        new_voxels[(x, y, z)] = 1
                    # Was solid, becomes empty (don't add)
        self.voxels = new_voxels
    
    def shrink(self):
        """Resize model bounds to fit actual voxels (remove empty space)"""
        if not self.voxels:
            self.size_x = self.size_y = self.size_z = 0
            return
        
        bounds = self.get_bounds()
        self.size_x = bounds[0]
        self.size_y = bounds[1]
        self.size_z = bounds[2]
    
    def repeat_pattern(self, count_x: int = 1, count_y: int = 1, count_z: int = 1, mirror: bool = False):
        """Repeat/tile the model pattern across axes"""
        if count_x == 1 and count_y == 1 and count_z == 1:
            return
        
        bounds = self.get_bounds()
        original_voxels = dict(self.voxels)
        
        for tx in range(count_x):
            for ty in range(count_y):
                for tz in range(count_z):
                    if tx == 0 and ty == 0 and tz == 0:
                        continue  # Skip original
                    
                    offset_x = tx * bounds[0] if not mirror or tx % 2 == 0 else tx * bounds[0]
                    offset_y = ty * bounds[1] if not mirror or ty % 2 == 0 else ty * bounds[1]
                    offset_z = tz * bounds[2] if not mirror or tz % 2 == 0 else tz * bounds[2]
                    
                    for (x, y, z), color in original_voxels.items():
                        new_x = x + offset_x
                        new_y = y + offset_y
                        new_z = z + offset_z
                        
                        if mirror and (tx % 2 == 1 or ty % 2 == 1 or tz % 2 == 1):
                            # Mirror on odd repetitions
                            if tx % 2 == 1:
                                new_x = offset_x + bounds[0] - 1 - x
                            if ty % 2 == 1:
                                new_y = offset_y + bounds[1] - 1 - y
                            if tz % 2 == 1:
                                new_z = offset_z + bounds[2] - 1 - z
                        
                        self.set_voxel(new_x, new_y, new_z, color)
        
        self.size_x = bounds[0] * count_x
        self.size_y = bounds[1] * count_y
        self.size_z = bounds[2] * count_z
    
    def apply_noise(self, seed: int = 0, scale: float = 0.1, min_val: float = 0.0, max_val: float = 1.0):
        """Apply procedural noise to voxel colors"""
        import random
        random.seed(seed)
        
        # Simple noise: randomize colors within range
        for (x, y, z) in list(self.voxels.keys()):
            noise_val = random.uniform(min_val, max_val)
            if noise_val > 0.5:  # Threshold for applying noise
                current_color = self.voxels[(x, y, z)]
                # Slightly modify color index
                new_color = max(1, min(255, int(current_color + (noise_val - 0.5) * 10)))
                self.voxels[(x, y, z)] = new_color
    
    def randomize_colors(self, min_index: int = 1, max_index: int = 255):
        """Randomize voxel colors within palette range"""
        import random
        for (x, y, z) in self.voxels.keys():
            self.voxels[(x, y, z)] = random.randint(min_index, max_index)
    
    def optimize_palette(self):
        """Remove unused palette colors and remap"""
        used_colors = set(self.voxels.values())
        if 0 in used_colors:
            used_colors.remove(0)  # Keep transparent
        
        # Create mapping from old to new indices
        color_mapping = {0: 0}  # Keep transparent
        new_index = 1
        for old_color in sorted(used_colors):
            color_mapping[old_color] = new_index
            new_index += 1
        
        # Remap voxels
        new_voxels = {}
        for (x, y, z), old_color in self.voxels.items():
            new_voxels[(x, y, z)] = color_mapping.get(old_color, old_color)
        self.voxels = new_voxels
        
        # Remap palette
        new_palette = [self.palette[0]]  # Keep transparent
        for old_color in sorted(used_colors):
            new_palette.append(self.palette[old_color])
        # Fill rest
        while len(new_palette) < 256:
            new_palette.append((128, 128, 128, 255))
        self.palette = new_palette
    
    def extrude_region(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int,
                       direction: str, distance: int, color_index: Optional[int] = None):
        """Extrude a region in a direction. Direction: 'x+', 'x-', 'y+', 'y-', 'z+', 'z-'"""
        # Get original region
        original_voxels = {}
        for x in range(min(x1, x2), max(x1, x2) + 1):
            for y in range(min(y1, y2), max(y1, y2) + 1):
                for z in range(min(z1, z2), max(z1, z2) + 1):
                    if (x, y, z) in self.voxels:
                        original_voxels[(x, y, z)] = self.voxels[(x, y, z)]
        
        # Determine offset direction
        if direction == 'x+':
            offset = (1, 0, 0)
        elif direction == 'x-':
            offset = (-1, 0, 0)
        elif direction == 'y+':
            offset = (0, 1, 0)
        elif direction == 'y-':
            offset = (0, -1, 0)
        elif direction == 'z+':
            offset = (0, 0, 1)
        else:  # 'z-'
            offset = (0, 0, -1)
        
        # Extrude
        for step in range(distance):
            for (x, y, z), color in list(original_voxels.items()):
                new_x = x + offset[0] * (step + 1)
                new_y = y + offset[1] * (step + 1)
                new_z = z + offset[2] * (step + 1)
                use_color = color_index if color_index is not None else color
                self.set_voxel(new_x, new_y, new_z, use_color)


def read_vox_file(filepath: Path) -> VoxelModel:
    """Read a .vox file and return a VoxelModel"""
    with open(filepath, 'rb') as f:
        # Read header
        magic = f.read(4)
        if magic != b'VOX ':
            raise ValueError("Invalid .vox file format")
        
        version = struct.unpack('<I', f.read(4))[0]
        
        # Read MAIN chunk
        chunk_id = f.read(4)
        if chunk_id != b'MAIN':
            raise ValueError("Expected MAIN chunk")
        
        chunk_size = struct.unpack('<I', f.read(4))[0]
        child_chunks = struct.unpack('<I', f.read(4))[0]
        
        # Read SIZE chunk
        size_id = f.read(4)
        if size_id != b'SIZE':
            raise ValueError("Expected SIZE chunk")
        
        size_chunk_size = struct.unpack('<I', f.read(4))[0]
        size_child_chunks = struct.unpack('<I', f.read(4))[0]
        
        size_x = struct.unpack('<I', f.read(4))[0]
        size_y = struct.unpack('<I', f.read(4))[0]
        size_z = struct.unpack('<I', f.read(4))[0]
        
        # Create model with the size from file, but we'll allow placing voxels beyond it
        model = VoxelModel(size_x, size_y, size_z)
        
        # Read XYZI chunk (voxel data)
        xyzi_id = f.read(4)
        if xyzi_id == b'XYZI':
            xyzi_chunk_size = struct.unpack('<I', f.read(4))[0]
            xyzi_child_chunks = struct.unpack('<I', f.read(4))[0]
            
            num_voxels = struct.unpack('<I', f.read(4))[0]
            
            for _ in range(num_voxels):
                x = struct.unpack('<B', f.read(1))[0]
                y = struct.unpack('<B', f.read(1))[0]
                z = struct.unpack('<B', f.read(1))[0]
                color_index = struct.unpack('<B', f.read(1))[0]
                model.set_voxel(x, y, z, color_index)
        
        # Try to read RGBA palette if present
        rgba_id = f.read(4)
        if rgba_id == b'RGBA':
            rgba_chunk_size = struct.unpack('<I', f.read(4))[0]
            rgba_child_chunks = struct.unpack('<I', f.read(4))[0]
            
            palette = []
            for _ in range(256):
                r = struct.unpack('<B', f.read(1))[0]
                g = struct.unpack('<B', f.read(1))[0]
                b = struct.unpack('<B', f.read(1))[0]
                a = struct.unpack('<B', f.read(1))[0]
                palette.append((r, g, b, a))
            model.palette = palette
    
    return model


def check_connection(model: VoxelModel, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int) -> tuple[bool, Optional[tuple[int, int, int]]]:
    """Check if a box region connects to existing voxels.
    Returns (connects, nearest_point) where nearest_point is the closest existing voxel if not connected."""
    connects = False
    nearest_point = None
    min_distance = float('inf')
    
    # Check all positions in the box
    for x in range(min(x1, x2), max(x1, x2) + 1):
        for y in range(min(y1, y2), max(y1, y2) + 1):
            for z in range(min(z1, z2), max(z1, z2) + 1):
                # Check 6 neighbors
                for dx, dy, dz in [(1,0,0), (-1,0,0), (0,1,0), (0,-1,0), (0,0,1), (0,0,-1)]:
                    neighbor = (x+dx, y+dy, z+dz)
                    if neighbor in model.voxels:
                        connects = True
                        return (True, None)
                    # Track nearest existing voxel
                    for existing_pos in model.voxels:
                        dist = abs(x - existing_pos[0]) + abs(y - existing_pos[1]) + abs(z - existing_pos[2])
                        if dist < min_distance:
                            min_distance = dist
                            nearest_point = existing_pos
    
    return (connects, nearest_point)


def detect_gaps(model: VoxelModel, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int) -> list[int]:
    """Detect gaps in Y direction between the box and existing parts.
    Returns list of Y coordinates where gaps exist."""
    gaps = []
    
    # Get Y range of the box
    box_y_min = min(y1, y2)
    box_y_max = max(y1, y2)
    
    # Check for gaps above the box
    if model.voxels:
        existing_y_max = max(y for (x, y, z) in model.voxels if x1 <= x <= x2 and z1 <= z <= z2)
        if existing_y_max < box_y_min - 1:
            # Gap detected
            for gap_y in range(existing_y_max + 1, box_y_min):
                gaps.append(gap_y)
    
    # Check for gaps below the box
    if model.voxels:
        existing_y_min = min(y for (x, y, z) in model.voxels if x1 <= x <= x2 and z1 <= z <= z2)
        if existing_y_min > box_y_max + 1:
            # Gap detected
            for gap_y in range(box_y_max + 1, existing_y_min):
                gaps.append(gap_y)
    
    return gaps


def calculate_human_proportions(total_height: int, style: str = "standard") -> Dict[str, int]:
    """Calculate proper human body proportions based on the 8-heads-tall rule.
    
    Args:
        total_height: Total height of the character in voxels
        style: "standard" (8 heads), "minecraft" (Minecraft player), "heroic" (9 heads), "chibi" (4-5 heads)
    
    Returns:
        Dictionary with body part dimensions in voxels
    """
    if style == "minecraft":
        # Minecraft player: ~1.875 blocks tall, but model is 32 voxels
        # Head: 8 voxels, Torso: 12, Legs: 12
        head_height = max(1, total_height // 4)  # Head is 1/4 of height in Minecraft
        neck_height = max(1, total_height // 32)
        torso_height = max(1, total_height * 3 // 8)
        leg_height = max(1, total_height * 3 // 8)
        arm_length = max(1, total_height * 3 // 8)
    elif style == "heroic":
        # Heroic proportions: 9 heads tall
        head_height = max(1, total_height // 9)
        neck_height = max(1, total_height // 36)
        torso_height = max(1, total_height * 3 // 9)
        leg_height = max(1, total_height * 4 // 9)
        arm_length = max(1, total_height * 3 // 9)
    elif style == "chibi":
        # Chibi/cute style: 4-5 heads tall
        head_height = max(1, total_height // 4)
        neck_height = max(1, total_height // 20)
        torso_height = max(1, total_height // 4)
        leg_height = max(1, total_height // 4)
        arm_length = max(1, total_height // 4)
    else:  # standard
        # Standard human: 8 heads tall
        head_height = max(1, total_height // 8)
        neck_height = max(1, total_height // 32)
        torso_height = max(1, total_height * 3 // 8)  # 3 heads
        leg_height = max(1, total_height // 2)  # 4 heads
        arm_length = max(1, total_height * 3 // 8)  # 3 heads
    
    return {
        'head': head_height,
        'neck': neck_height,
        'torso': torso_height,
        'legs': leg_height,
        'arms': arm_length,
        'total': total_height
    }


def calculate_minecraft_proportions() -> Dict[str, float]:
    """Calculate Minecraft-specific proportions based on official measurements.
    
    Returns:
        Dictionary with Minecraft measurements in blocks/meters
    """
    return {
        'player_height_standing': 1.8,  # blocks (1.8 meters)
        'player_height_sneaking': 1.5,  # blocks
        'player_height_swimming': 0.6,  # blocks
        'player_width': 0.6,  # blocks
        'eye_height_standing': 1.62,  # meters above base
        'eye_height_sneaking': 1.27,  # meters above base
        'block_size': 1.0,  # 1 block = 1 meter
        'pixels_per_block': 16,  # texture resolution
        'meters_per_pixel': 0.0625,  # 1/16 meter per pixel
        'player_model_height_voxels': 32,  # standard Minecraft skin height
        'head_voxels': 8,
        'torso_voxels': 12,
        'legs_voxels': 12
    }


def check_proportions(model: VoxelModel, part_name: str, dimensions: Tuple[int, int, int], 
                     model_height: Optional[int] = None, style: str = "standard") -> Optional[str]:
    """Check if body part dimensions are proportional to the overall model.
    
    Args:
        model: The voxel model
        part_name: Name of the body part ("head", "torso", "legs", "arms", etc.)
        dimensions: (width, height, depth) of the part
        model_height: Total model height in voxels (if None, calculated from model)
        style: Proportion style ("standard", "minecraft", "heroic", "chibi")
    
    Returns:
        Warning string if disproportionate, None if OK
    """
    # Calculate model height if not provided
    if model_height is None:
        if not model.voxels:
            return None  # Can't check proportions of empty model
        all_y = [y for (x, y, z) in model.voxels.keys()]
        if not all_y:
            return None
        model_height = max(all_y) - min(all_y) + 1
    
    if model_height < 4:
        return None  # Too small to check proportions
    
    # Get expected proportions
    proportions = calculate_human_proportions(model_height, style)
    
    part_width, part_height, part_depth = dimensions
    
    # Check specific body parts
    if part_name.lower() == "head":
        expected_height = proportions['head']
        if part_height > expected_height * 1.5:
            return (f"Warning: {part_name} height ({part_height} voxels) is too large. "
                   f"Expected ~{expected_height} voxels for {model_height}-voxel {style} character "
                   f"({part_height/expected_height:.1f}x expected size).")
        elif part_height < expected_height * 0.5:
            return (f"Warning: {part_name} height ({part_height} voxels) is too small. "
                   f"Expected ~{expected_height} voxels for {model_height}-voxel {style} character.")
    
    elif part_name.lower() == "torso":
        expected_height = proportions['torso']
        if part_height > expected_height * 1.5:
            return (f"Warning: {part_name} height ({part_height} voxels) is too large. "
                   f"Expected ~{expected_height} voxels for {model_height}-voxel {style} character.")
        elif part_height < expected_height * 0.5:
            return (f"Warning: {part_name} height ({part_height} voxels) is too small. "
                   f"Expected ~{expected_height} voxels for {model_height}-voxel {style} character.")
    
    elif part_name.lower() in ["legs", "leg"]:
        expected_height = proportions['legs']
        if part_height > expected_height * 1.5:
            return (f"Warning: {part_name} height ({part_height} voxels) is too large. "
                   f"Expected ~{expected_height} voxels for {model_height}-voxel {style} character.")
        elif part_height < expected_height * 0.5:
            return (f"Warning: {part_name} height ({part_height} voxels) is too small. "
                   f"Expected ~{expected_height} voxels for {model_height}-voxel {style} character.")
    
    elif part_name.lower() in ["arms", "arm"]:
        expected_length = proportions['arms']
        # For arms, check the longest dimension (could be width, height, or depth)
        max_dim = max(part_width, part_height, part_depth)
        if max_dim > expected_length * 1.5:
            return (f"Warning: {part_name} length ({max_dim} voxels) is too long. "
                   f"Expected ~{expected_length} voxels for {model_height}-voxel {style} character.")
        elif max_dim < expected_length * 0.5:
            return (f"Warning: {part_name} length ({max_dim} voxels) is too short. "
                   f"Expected ~{expected_length} voxels for {model_height}-voxel {style} character.")
    
    return None  # Proportions are OK


def suggest_proportions(model_height: int, style: str = "standard") -> Dict[str, Dict[str, int]]:
    """Suggest proper proportions for a character model.
    
    Args:
        model_height: Total height of the character in voxels
        style: Proportion style ("standard", "minecraft", "heroic", "chibi")
    
    Returns:
        Dictionary with suggested dimensions for each body part
    """
    proportions = calculate_human_proportions(model_height, style)
    
    return {
        'head': {
            'height': proportions['head'],
            'width': proportions['head'],
            'depth': proportions['head'],
            'radius': proportions['head'] // 2
        },
        'neck': {
            'height': proportions['neck'],
            'width': max(1, proportions['head'] * 2 // 3),
            'depth': max(1, proportions['head'] * 2 // 3)
        },
        'torso': {
            'height': proportions['torso'],
            'width': max(1, proportions['head'] * 2),
            'depth': max(1, proportions['head'] * 1.5)
        },
        'legs': {
            'height': proportions['legs'],
            'width': max(1, proportions['head'] * 1.5),
            'depth': max(1, proportions['head'] * 1.5)
        },
        'arms': {
            'length': proportions['arms'],
            'width': max(1, proportions['head'] * 3 // 4),
            'depth': max(1, proportions['head'] * 3 // 4)
        }
    }


def suggest_connection_fix(model: VoxelModel, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int) -> Optional[str]:
    """Suggest how to fix a connection issue.
    Returns a suggestion string or None if no fix needed."""
    connects, nearest = check_connection(model, x1, y1, z1, x2, y2, z2)
    
    if connects:
        return None
    
    if nearest:
        nx, ny, nz = nearest
        # Suggest adjusting coordinates to connect
        if abs(nx - x1) < abs(nx - x2):
            if x1 < nx:
                return f"Adjust x1 to {nx} to connect to nearest part at ({nx},{ny},{nz})"
            else:
                return f"Adjust x2 to {nx} to connect to nearest part at ({nx},{ny},{nz})"
        else:
            if x2 < nx:
                return f"Adjust x1 to {nx} to connect to nearest part at ({nx},{ny},{nz})"
            else:
                return f"Adjust x2 to {nx} to connect to nearest part at ({nx},{ny},{nz})"
    
    return "No existing parts found to connect to"


def validate_item_size(model: VoxelModel, item_type: str = "item") -> List[str]:
    """Validate item dimensions against Minecraft scale.
    
    Args:
        model: The voxel model to validate
        item_type: Type of item ("item", "weapon", "tool", "container", etc.)
    
    Returns:
        List of warning strings (empty if no issues)
    """
    warnings = []
    
    if not model.voxels:
        return warnings
    
    bounds = model.get_bounds()
    width, height, depth = bounds[0], bounds[1], bounds[2]
    mc = calculate_minecraft_proportions()
    player_height = mc['player_height_standing']
    
    # Check height relative to player
    if height > player_height * 2:
        warnings.append(f"Item is very tall ({height} voxels = {height/player_height:.1f}x player height). "
                       f"Most items should be 1-2 blocks tall.")
    elif height < 2:
        warnings.append(f"Item is very short ({height} voxels). Consider if this is intentional.")
    
    # Check for thin items (likely 2D sprites, but might be unintentional)
    if width < 3 and depth < 3:
        warnings.append(f"Item is very thin ({width}x{depth} cross-section). "
                       f"This might be intended for a 2D sprite, but consider adding depth.")
    
    # Check aspect ratio
    max_dim = max(width, height, depth)
    min_dim = min(width, height, depth)
    if max_dim > 0 and min_dim > 0:
        aspect_ratio = max_dim / min_dim
        if aspect_ratio > 10:
            warnings.append(f"Item has extreme aspect ratio ({aspect_ratio:.1f}:1). "
                           f"Consider if this is intentional for the item type.")
    
    return warnings


def validate_item_connectivity(model: VoxelModel) -> List[str]:
    """Check if all parts of an item are connected.
    
    Returns:
        List of warning strings about disconnected components
    """
    warnings = []
    
    if not model.voxels:
        return warnings
    
    components = model.find_connected_components()
    
    if len(components) > 1:
        warnings.append(f"Item has {len(components)} disconnected pieces (should be 1).")
        
        # Find the main component (largest)
        main_component = max(components, key=lambda c: c['voxel_count'])
        main_size = main_component['voxel_count']
        
        # Report small disconnected pieces
        small_pieces = [c for c in components if c['voxel_count'] < main_size * 0.1 and c['voxel_count'] < 5]
        if small_pieces:
            warnings.append(f"Found {len(small_pieces)} small disconnected pieces that might be accidental.")
            for i, piece in enumerate(small_pieces, 1):
                b = piece['bounds']
                warnings.append(f"  Small piece {i}: {piece['voxel_count']} voxels at "
                              f"({b['min_x']},{b['min_y']},{b['min_z']})")
    
    return warnings


def validate_item_density(model: VoxelModel) -> List[str]:
    """Check voxel density and suggest improvements.
    
    Returns:
        List of suggestion strings
    """
    suggestions = []
    
    if not model.voxels:
        return suggestions
    
    bounds = model.get_bounds()
    width, height, depth = bounds[0], bounds[1], bounds[2]
    total_volume = width * height * depth
    voxel_count = len(model.voxels)
    
    if total_volume == 0:
        return suggestions
    
    density = voxel_count / total_volume
    
    # For items, very low density might indicate missing details
    if density < 0.1 and voxel_count > 10:
        suggestions.append(f"Low voxel density ({density:.1%}). "
                          f"Consider adding more detail or filling hollow spaces.")
    elif density > 0.9:
        suggestions.append(f"Very high density ({density:.1%}). "
                          f"Item might be too solid - consider hollowing for efficiency.")
    
    return suggestions


def write_vox_file(filepath: Path, model: VoxelModel):
    """Write a VoxelModel to a .vox file"""
    with open(filepath, 'wb') as f:
        # Write header
        f.write(b'VOX ')
        f.write(struct.pack('<I', 150))  # Version 150
        
        # Calculate chunk sizes
        # Use the model's declared size, but ensure it's at least as large as the bounds
        if model.voxels:
            actual_bounds = model.get_bounds()
            # Use the larger of declared size or actual bounds
            size_x = max(model.size_x, actual_bounds[0])
            size_y = max(model.size_y, actual_bounds[1])
            size_z = max(model.size_z, actual_bounds[2])
        else:
            # Use specified size
            size_x, size_y, size_z = model.size_x, model.size_y, model.size_z
        
        num_voxels = len(model.voxels)
        
        # SIZE chunk
        size_chunk_size = 12  # 3 * 4 bytes
        size_chunk_child = 0
        
        # XYZI chunk
        xyzi_chunk_size = 4 + (num_voxels * 4)  # 4 bytes for count + 4 bytes per voxel
        xyzi_chunk_child = 0
        
        # RGBA chunk
        rgba_chunk_size = 256 * 4  # 256 colors * 4 bytes
        rgba_chunk_child = 0
        
        # MAIN chunk
        main_chunk_size = 0  # MAIN chunk contains child chunks
        main_chunk_child = 8 + size_chunk_size + 8 + xyzi_chunk_size + 8 + rgba_chunk_size
        
        # Write MAIN chunk header
        f.write(b'MAIN')
        f.write(struct.pack('<I', main_chunk_size))
        f.write(struct.pack('<I', main_chunk_child))
        
        # Write SIZE chunk
        f.write(b'SIZE')
        f.write(struct.pack('<I', size_chunk_size))
        f.write(struct.pack('<I', size_chunk_child))
        f.write(struct.pack('<I', size_x))
        f.write(struct.pack('<I', size_y))
        f.write(struct.pack('<I', size_z))
        
        # Write XYZI chunk
        f.write(b'XYZI')
        f.write(struct.pack('<I', xyzi_chunk_size))
        f.write(struct.pack('<I', xyzi_chunk_child))
        f.write(struct.pack('<I', num_voxels))
        
        for (x, y, z), color_index in model.voxels.items():
            f.write(struct.pack('<B', x))
            f.write(struct.pack('<B', y))
            f.write(struct.pack('<B', z))
            f.write(struct.pack('<B', color_index))
        
        # Write RGBA chunk
        f.write(b'RGBA')
        f.write(struct.pack('<I', rgba_chunk_size))
        f.write(struct.pack('<I', rgba_chunk_child))
        
        for r, g, b, a in model.palette:
            f.write(struct.pack('<B', r))
            f.write(struct.pack('<B', g))
            f.write(struct.pack('<B', b))
            f.write(struct.pack('<B', a))


def render_model_to_image(model: VoxelModel, angle: str, output_path: Path) -> bool:
    """
    Render a voxel model to an image from a specific angle.
    
    Args:
        model: The VoxelModel to render
        angle: One of 'front', 'back', 'left', 'right', 'top', 'bottom'
        output_path: Path to save the image
    
    Returns:
        True if successful, False otherwise
    """
    if not PIL_AVAILABLE:
        return False
    
    if not model.voxels:
        return False
    
    bounds = model.get_bounds()
    
    # Determine image dimensions and projection based on angle
    if angle == "front":  # Looking along -Z axis (X, Y visible)
        width, height = bounds[0], bounds[1]
        def project(x, y, z):
            return (x, y)
    elif angle == "back":  # Looking along +Z axis (X, Y visible, X flipped)
        width, height = bounds[0], bounds[1]
        def project(x, y, z):
            return (bounds[0] - 1 - x, y)
    elif angle == "left":  # Looking along -X axis (Z, Y visible)
        width, height = bounds[2], bounds[1]
        def project(x, y, z):
            return (z, y)
    elif angle == "right":  # Looking along +X axis (Z, Y visible, Z flipped)
        width, height = bounds[2], bounds[1]
        def project(x, y, z):
            return (bounds[2] - 1 - z, y)
    elif angle == "top":  # Looking along -Y axis (X, Z visible)
        width, height = bounds[0], bounds[2]
        def project(x, y, z):
            return (x, z)
    elif angle == "bottom":  # Looking along +Y axis (X, Z visible, Y flipped)
        width, height = bounds[0], bounds[2]
        def project(x, y, z):
            return (x, bounds[2] - 1 - z)
    else:
        return False
    
    # Create image with transparent background
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    pixels = img.load()
    
    # Project voxels onto 2D plane (use the closest voxel for each pixel)
    # For each pixel, find the voxel that projects to it and is closest to camera
    pixel_voxels = {}  # (px, py) -> (x, y, z, color_index, depth)
    
    for (x, y, z), color_index in model.voxels.items():
        if color_index == 0:  # Skip transparent
            continue
        
        px, py = project(x, y, z)
        if 0 <= px < width and 0 <= py < height:
            # Calculate depth for z-buffering
            if angle in ["front", "back"]:
                depth = z
            elif angle in ["left", "right"]:
                depth = x
            else:  # top, bottom
                depth = y
            
            key = (px, py)
            if key not in pixel_voxels or depth > pixel_voxels[key][4]:
                r, g, b, a = model.palette[color_index]
                pixel_voxels[key] = (px, py, x, y, z, r, g, b, a, depth)
    
    # Draw pixels
    for (px, py, _, _, _, r, g, b, a, _) in pixel_voxels.values():
        pixels[px, py] = (r, g, b, a)
    
    # Save image
    try:
        img.save(output_path, 'PNG')
        return True
    except Exception:
        return False


def render_model_all_angles(model: VoxelModel, base_output_path: Path) -> Dict[str, Path]:
    """
    Render a voxel model to images from all 6 angles.
    
    Args:
        model: The VoxelModel to render
        base_output_path: Base path (without extension) for output images
    
    Returns:
        Dictionary mapping angle names to output file paths
    """
    angles = ["front", "back", "left", "right", "top", "bottom"]
    results = {}
    
    for angle in angles:
        output_path = base_output_path.parent / f"{base_output_path.stem}_{angle}.png"
        if render_model_to_image(model, angle, output_path):
            results[angle] = output_path
    
    return results
