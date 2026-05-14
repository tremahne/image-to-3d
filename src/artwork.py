"""
Flat image → bas-relief STL pipeline.

Converts a 2D image to a heightmap and extrudes it into a printable
bas-relief mesh scaled to the Flashforge Adventurer 5M build volume.
"""
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
import trimesh
from src.mesh_utils import scale_to_build_volume, center_mesh, clean_mesh, export_stl


def image_to_heightmap(image_path: str, resolution: int = 200, smoothing: float = 1.0,
                        invert: bool = False) -> np.ndarray:
    """Convert an image to a normalized 2D heightmap array."""
    img = Image.open(image_path).convert("L")
    img = img.resize((resolution, resolution), Image.LANCZOS)
    arr = np.array(img, dtype=np.float32) / 255.0
    if invert:
        arr = 1.0 - arr
    if smoothing > 0:
        arr = gaussian_filter(arr, sigma=smoothing)
    return arr


def heightmap_to_mesh(heightmap: np.ndarray, max_depth_mm: float = 10.0,
                       base_thickness_mm: float = 2.0) -> trimesh.Trimesh:
    """
    Build a solid bas-relief mesh from a heightmap.

    The XY plane represents the image surface. Z axis is the extrusion depth.
    A flat base is added beneath the lowest point.
    """
    rows, cols = heightmap.shape
    # Scale factor so the mesh is in millimetres before final resize
    x = np.linspace(0, cols - 1, cols, dtype=np.float32)
    y = np.linspace(0, rows - 1, rows, dtype=np.float32)
    xx, yy = np.meshgrid(x, y)
    zz = heightmap * max_depth_mm + base_thickness_mm  # top surface Z

    # Flatten arrays
    top_verts = np.column_stack([xx.ravel(), yy.ravel(), zz.ravel()])
    base_verts = np.column_stack([xx.ravel(), yy.ravel(),
                                   np.zeros(xx.size, dtype=np.float32)])

    n_verts = len(top_verts)
    vertices = np.vstack([top_verts, base_verts])  # top first, then base

    # Build triangles for top surface
    top_faces = []
    for r in range(rows - 1):
        for c in range(cols - 1):
            i = r * cols + c
            top_faces.append([i,       i + 1,     i + cols])
            top_faces.append([i + 1,   i + cols + 1, i + cols])

    # Bottom surface (reversed winding for outward normals)
    bot_faces = []
    for r in range(rows - 1):
        for c in range(cols - 1):
            i = n_verts + r * cols + c
            bot_faces.append([i,       i + cols,   i + 1])
            bot_faces.append([i + 1,   i + cols,   i + cols + 1])

    # Side walls — 4 edges of the grid
    side_faces = []

    def _side_strip(top_indices, bot_indices):
        for k in range(len(top_indices) - 1):
            t0, t1 = top_indices[k], top_indices[k + 1]
            b0, b1 = bot_indices[k], bot_indices[k + 1]
            side_faces.append([t0, b0, t1])
            side_faces.append([t1, b0, b1])

    top_row_t = [r * cols + 0 for r in range(rows)]
    top_row_b = [n_verts + r * cols + 0 for r in range(rows)]
    _side_strip(top_row_t, top_row_b)

    bot_row_t = [r * cols + (cols - 1) for r in range(rows)]
    bot_row_b = [n_verts + r * cols + (cols - 1) for r in range(rows)]
    _side_strip(list(reversed(bot_row_t)), list(reversed(bot_row_b)))

    left_col_t = list(range(cols))
    left_col_b = [n_verts + c for c in range(cols)]
    _side_strip(list(reversed(left_col_t)), list(reversed(left_col_b)))

    right_col_t = [(rows - 1) * cols + c for c in range(cols)]
    right_col_b = [n_verts + (rows - 1) * cols + c for c in range(cols)]
    _side_strip(right_col_t, right_col_b)

    all_faces = np.array(top_faces + bot_faces + side_faces, dtype=np.int64)
    mesh = trimesh.Trimesh(vertices=vertices, faces=all_faces, process=False)
    return mesh


def process_artwork(image_path: str, output_path: str, resolution: int = 200,
                    max_depth_mm: float = 10.0, base_thickness_mm: float = 2.0,
                    smoothing: float = 1.0, invert: bool = False,
                    progress_cb=None) -> str:
    """Full pipeline: image → STL."""

    def _log(msg):
        if progress_cb:
            progress_cb(msg)

    _log("Loading image and generating heightmap...")
    heightmap = image_to_heightmap(image_path, resolution=resolution,
                                   smoothing=smoothing, invert=invert)

    _log("Building 3D mesh from heightmap...")
    mesh = heightmap_to_mesh(heightmap, max_depth_mm=max_depth_mm,
                              base_thickness_mm=base_thickness_mm)

    _log("Cleaning mesh...")
    mesh = clean_mesh(mesh)

    _log("Scaling to Flashforge Adventurer 5M build volume...")
    mesh = scale_to_build_volume(mesh)
    mesh = center_mesh(mesh)

    _log("Exporting STL...")
    export_stl(mesh, output_path)
    _log(f"Done → {output_path}")
    return output_path
