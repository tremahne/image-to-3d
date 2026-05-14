"""
Multi-angle photo → full 3D STL pipeline.

Uses COLMAP for Structure-from-Motion and Multi-View Stereo to reconstruct
a dense point cloud from multiple photographs, then converts to a watertight
mesh for STL export.
"""
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import trimesh
from src.mesh_utils import scale_to_build_volume, center_mesh, clean_mesh, export_stl

try:
    import open3d as o3d
    _HAS_OPEN3D = True
except ImportError:
    _HAS_OPEN3D = False


def _run(cmd: list, log_cb=None) -> subprocess.CompletedProcess:
    """Run a subprocess and stream output to log_cb."""
    if log_cb:
        log_cb(f"  $ {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if log_cb and result.stdout:
        for line in result.stdout.splitlines()[-5:]:  # tail of output
            log_cb(f"    {line}")
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed (exit {result.returncode}):\n{result.stdout[-2000:]}"
        )
    return result


def _check_colmap():
    if shutil.which("colmap") is None:
        raise EnvironmentError(
            "COLMAP is not installed. Run setup.sh or: sudo apt-get install colmap"
        )


def _colmap_reconstruct(image_dir: Path, workspace: Path, log_cb=None) -> Path:
    """Run full COLMAP sparse + dense reconstruction pipeline."""
    db = workspace / "database.db"
    sparse_dir = workspace / "sparse"
    dense_dir = workspace / "dense"
    sparse_dir.mkdir(exist_ok=True)
    dense_dir.mkdir(exist_ok=True)

    if log_cb:
        log_cb("Step 1/5 — Feature extraction...")
    _run(["colmap", "feature_extractor",
          "--database_path", str(db),
          "--image_path", str(image_dir),
          "--ImageReader.single_camera", "1",
          "--SiftExtraction.use_gpu", "0"], log_cb)

    if log_cb:
        log_cb("Step 2/5 — Feature matching...")
    _run(["colmap", "exhaustive_matcher",
          "--database_path", str(db),
          "--SiftMatching.use_gpu", "0"], log_cb)

    if log_cb:
        log_cb("Step 3/5 — Sparse reconstruction (SfM)...")
    _run(["colmap", "mapper",
          "--database_path", str(db),
          "--image_path", str(image_dir),
          "--output_path", str(sparse_dir)], log_cb)

    # mapper outputs numbered subdirectories; use the largest (most images)
    sparse_models = sorted(sparse_dir.iterdir(), key=lambda p: p.name)
    if not sparse_models:
        raise RuntimeError("COLMAP sparse reconstruction produced no models. "
                           "Ensure images have sufficient overlap and texture.")
    best_model = sparse_models[0]

    if log_cb:
        log_cb("Step 4/5 — Dense depth maps (MVS)...")
    _run(["colmap", "image_undistorter",
          "--image_path", str(image_dir),
          "--input_path", str(best_model),
          "--output_path", str(dense_dir),
          "--output_type", "COLMAP"], log_cb)
    _run(["colmap", "patch_match_stereo",
          "--workspace_path", str(dense_dir),
          "--workspace_format", "COLMAP",
          "--PatchMatchStereo.geom_consistency", "true"], log_cb)

    if log_cb:
        log_cb("Step 5/5 — Stereo fusion (dense point cloud)...")
    fused_ply = workspace / "fused.ply"
    _run(["colmap", "stereo_fusion",
          "--workspace_path", str(dense_dir),
          "--workspace_format", "COLMAP",
          "--input_type", "geometric",
          "--output_path", str(fused_ply)], log_cb)

    return fused_ply


def _ply_to_mesh_open3d(ply_path: Path, log_cb=None) -> trimesh.Trimesh:
    """Poisson surface reconstruction via Open3D."""
    if log_cb:
        log_cb("Reconstructing surface with Open3D Poisson solver...")
    pcd = o3d.io.read_point_cloud(str(ply_path))
    pcd.estimate_normals(
        search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.1, max_nn=30)
    )
    pcd.orient_normals_consistent_tangent_plane(100)
    mesh_o3d, _ = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
        pcd, depth=9, width=0, scale=1.1, linear_fit=False
    )
    # Trim low-density vertices (outer shell artifacts)
    bbox = pcd.get_axis_aligned_bounding_box()
    mesh_o3d = mesh_o3d.crop(bbox)

    verts = np.asarray(mesh_o3d.vertices)
    faces = np.asarray(mesh_o3d.triangles)
    return trimesh.Trimesh(vertices=verts, faces=faces, process=False)


def _ply_to_mesh_trimesh(ply_path: Path, log_cb=None) -> trimesh.Trimesh:
    """Ball-pivot surface reconstruction via trimesh (fallback)."""
    if log_cb:
        log_cb("Reconstructing surface with trimesh ball-pivot (Open3D not available)...")
    cloud = trimesh.load(str(ply_path))
    if isinstance(cloud, trimesh.PointCloud):
        points = cloud.vertices
    else:
        points = np.array(cloud.vertices)

    # Estimate normals and run ball-pivot
    mesh = trimesh.voxel.ops.points_to_marching_cubes(points)
    return mesh


def process_photos(image_paths: list, output_path: str,
                   progress_cb=None) -> str:
    """Full pipeline: multiple angle photos → STL."""

    def _log(msg):
        if progress_cb:
            progress_cb(msg)

    _check_colmap()

    with tempfile.TemporaryDirectory(prefix="img2stl_") as tmp:
        workspace = Path(tmp)
        image_dir = workspace / "images"
        image_dir.mkdir()

        _log(f"Copying {len(image_paths)} images to workspace...")
        for i, src in enumerate(image_paths):
            ext = Path(src).suffix or ".jpg"
            dst = image_dir / f"image_{i:04d}{ext}"
            shutil.copy2(src, dst)

        _log("Starting COLMAP reconstruction pipeline...")
        fused_ply = _colmap_reconstruct(image_dir, workspace, log_cb=_log)

        _log("Converting point cloud to surface mesh...")
        if _HAS_OPEN3D:
            mesh = _ply_to_mesh_open3d(fused_ply, log_cb=_log)
        else:
            mesh = _ply_to_mesh_trimesh(fused_ply, log_cb=_log)

        _log("Cleaning mesh...")
        mesh = clean_mesh(mesh)

        _log("Scaling to Flashforge Adventurer 5M build volume...")
        mesh = scale_to_build_volume(mesh)
        mesh = center_mesh(mesh)

        _log("Exporting STL...")
        export_stl(mesh, output_path)

    _log(f"Done → {output_path}")
    return output_path
