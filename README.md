# image-to-3d

Convert images to 3D printable STL files for the **Flashforge Adventurer 5M**.

## Pipelines

### Photo Mode — Multi-angle Photogrammetry
Upload 10–30 photos of the same object taken from different angles. COLMAP
reconstructs the full 3D geometry using Structure-from-Motion and Multi-View
Stereo. Output is a watertight STL scaled to the printer's 220×220×220 mm
build volume.

**Photo tips for best results:**
- Walk around the object taking overlapping photos (~70% overlap between shots)
- Shoot from high, mid, and low angles
- Avoid reflective or transparent surfaces
- Use consistent, diffuse lighting (no harsh shadows)
- Keep the object in focus and avoid motion blur

### Artwork Mode — Bas-Relief
Upload a single flat image (logo, sketch, photograph). The image is converted
to a grayscale heightmap and extruded into a solid bas-relief STL. Light
pixels become raised areas; dark pixels recede (or invert this with the toggle).

## Requirements

- Python 3.10+
- [COLMAP](https://colmap.github.io/) (for Photo Mode)

## Setup

```bash
git clone https://github.com/tremahne/image-to-3d.git
cd image-to-3d
bash setup.sh
```

## Run

```bash
python3 app.py
```

Opens a local web interface at `http://localhost:7860`.

## Output

STL files are saved to the `output/` directory and available for download
from the interface. Load them into
[FlashPrint](https://www.flashforge.com/download-center) to slice and send
to your Adventurer 5M.

## Open-source tools used

| Tool | Purpose |
|------|---------|
| [COLMAP](https://colmap.github.io/) | Structure-from-Motion + Multi-View Stereo |
| [Open3D](http://www.open3d.org/) | Poisson surface reconstruction |
| [trimesh](https://trimsh.org/) | Mesh processing and STL export |
| [Gradio](https://gradio.app/) | Local web GUI |
| [Pillow](https://python-pillow.org/) | Image loading and preprocessing |
| [SciPy](https://scipy.org/) | Heightmap smoothing |
