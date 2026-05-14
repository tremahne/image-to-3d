"""
image-to-3d — local Gradio app
Converts images to STL files for the Flashforge Adventurer 5M.

Two pipelines:
  • Photo Mode  — multiple photos of the same object from different angles
                  → full 3D reconstruction via COLMAP + surface meshing
  • Artwork Mode — a single flat image (logo, drawing, photo)
                  → bas-relief STL via heightmap extrusion
"""
import os
import time
import threading
from pathlib import Path

import gradio as gr

from src.photogrammetry import process_photos
from src.artwork import process_artwork

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def _timestamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S")


# ---------------------------------------------------------------------------
# Photo Mode
# ---------------------------------------------------------------------------

def run_photo_mode(files, progress=gr.Progress(track_tqdm=False)):
    if not files:
        return None, "No images uploaded."

    log_lines = []

    def _log(msg):
        log_lines.append(msg)

    image_paths = [f.name for f in files]
    out_path = str(OUTPUT_DIR / f"photo_{_timestamp()}.stl")

    try:
        progress(0, desc="Starting COLMAP pipeline...")
        process_photos(image_paths, out_path, progress_cb=_log)
        progress(1.0, desc="Done")
        return out_path, "\n".join(log_lines)
    except Exception as e:
        log_lines.append(f"ERROR: {e}")
        return None, "\n".join(log_lines)


# ---------------------------------------------------------------------------
# Artwork Mode
# ---------------------------------------------------------------------------

def run_artwork_mode(file, resolution, max_depth, base_thickness,
                     smoothing, invert, progress=gr.Progress(track_tqdm=False)):
    if file is None:
        return None, "No image uploaded."

    log_lines = []

    def _log(msg):
        log_lines.append(msg)

    out_path = str(OUTPUT_DIR / f"artwork_{_timestamp()}.stl")

    try:
        progress(0, desc="Processing image...")
        process_artwork(
            image_path=file.name,
            output_path=out_path,
            resolution=int(resolution),
            max_depth_mm=float(max_depth),
            base_thickness_mm=float(base_thickness),
            smoothing=float(smoothing),
            invert=bool(invert),
            progress_cb=_log,
        )
        progress(1.0, desc="Done")
        return out_path, "\n".join(log_lines)
    except Exception as e:
        log_lines.append(f"ERROR: {e}")
        return None, "\n".join(log_lines)


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

DESCRIPTION = """
# image-to-3d
Convert images to STL files sized for the **Flashforge Adventurer 5M** (220×220×220 mm build volume).

- **Photo Mode** — upload multiple photos of the same object taken from different angles.
  COLMAP reconstructs the full 3D shape.
- **Artwork Mode** — upload a single flat image (logo, sketch, photo).
  The image is extruded into a bas-relief STL.
"""

with gr.Blocks(title="image-to-3d", theme=gr.themes.Soft()) as app:
    gr.Markdown(DESCRIPTION)

    with gr.Tabs():

        # ------------------------------------------------------------------
        with gr.TabItem("Photo Mode (Multi-angle → Full 3D)"):
            gr.Markdown(
                "Upload **multiple photos** of the same object taken from different angles. "
                "More photos (10–30) and good coverage produce better results. "
                "Requires [COLMAP](https://colmap.github.io/) to be installed (`setup.sh` handles this)."
            )
            with gr.Row():
                with gr.Column():
                    photo_input = gr.File(
                        label="Upload Photos",
                        file_count="multiple",
                        file_types=["image"],
                    )
                    photo_btn = gr.Button("Generate STL", variant="primary")
                with gr.Column():
                    photo_stl = gr.File(label="Download STL")
                    photo_log = gr.Textbox(label="Progress Log", lines=20,
                                           interactive=False, show_copy_button=True)

            photo_btn.click(
                fn=run_photo_mode,
                inputs=[photo_input],
                outputs=[photo_stl, photo_log],
            )

        # ------------------------------------------------------------------
        with gr.TabItem("Artwork Mode (Single Image → Bas-Relief)"):
            gr.Markdown(
                "Upload a **single image** — a logo, drawing, or photograph. "
                "It will be converted into a raised bas-relief you can print flat on the bed."
            )
            with gr.Row():
                with gr.Column():
                    art_input = gr.File(
                        label="Upload Image",
                        file_count="single",
                        file_types=["image"],
                    )
                    with gr.Accordion("Settings", open=True):
                        art_resolution = gr.Slider(
                            50, 400, value=200, step=10,
                            label="Resolution (mesh density — higher = slower)",
                        )
                        art_depth = gr.Slider(
                            1.0, 30.0, value=10.0, step=0.5,
                            label="Max relief depth (mm)",
                        )
                        art_base = gr.Slider(
                            0.5, 10.0, value=2.0, step=0.5,
                            label="Base plate thickness (mm)",
                        )
                        art_smooth = gr.Slider(
                            0.0, 5.0, value=1.0, step=0.5,
                            label="Smoothing",
                        )
                        art_invert = gr.Checkbox(
                            label="Invert heightmap (dark areas raised instead of light)",
                            value=False,
                        )
                    art_btn = gr.Button("Generate STL", variant="primary")

                with gr.Column():
                    art_stl = gr.File(label="Download STL")
                    art_log = gr.Textbox(label="Progress Log", lines=12,
                                         interactive=False, show_copy_button=True)

            art_btn.click(
                fn=run_artwork_mode,
                inputs=[art_input, art_resolution, art_depth,
                        art_base, art_smooth, art_invert],
                outputs=[art_stl, art_log],
            )

if __name__ == "__main__":
    app.launch(server_name="0.0.0.0", server_port=7860, inbrowser=True)
