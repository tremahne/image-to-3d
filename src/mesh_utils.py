"""Shared mesh processing utilities."""
import numpy as np
import trimesh

# Flashforge Adventurer 5M build volume in mm
BUILD_VOLUME = (220.0, 220.0, 220.0)


def scale_to_build_volume(mesh: trimesh.Trimesh, margin_mm: float = 5.0) -> trimesh.Trimesh:
    """Scale mesh to fit within the printer build volume with a margin."""
    max_dim = max(BUILD_VOLUME) - margin_mm * 2
    extents = mesh.extents
    largest = max(extents)
    if largest == 0:
        return mesh
    scale = max_dim / largest
    mesh.apply_scale(scale)
    return mesh


def center_mesh(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Center mesh at origin and place base on Z=0."""
    mesh.apply_translation(-mesh.centroid)
    mesh.apply_translation([0, 0, -mesh.bounds[0][2]])
    return mesh


def clean_mesh(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Remove degenerate faces, merge duplicate vertices, fix normals."""
    mesh.remove_degenerate_faces()
    mesh.merge_vertices()
    trimesh.repair.fix_normals(mesh)
    trimesh.repair.fill_holes(mesh)
    return mesh


def export_stl(mesh: trimesh.Trimesh, path: str) -> str:
    mesh.export(path)
    return path
