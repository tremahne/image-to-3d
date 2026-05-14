# image-to-3d — Running Instructions

**GitHub:** https://github.com/tremahne/image-to-3d
**Printer:** Flashforge Adventurer 5M (220×220×220 mm build volume)

---

## First-time setup (run once)

```bash
cd ~/image-to-3d
bash setup.sh
```

This installs COLMAP (requires sudo password) and all Python dependencies.

---

## Launch the app

```bash
cd ~/image-to-3d
python3 app.py
```

Opens automatically in your browser at `http://localhost:7860`.

---

## Using the app

### Artwork Mode (Single Image → Bas-Relief STL)
1. Click the **Artwork Mode** tab
2. Upload any flat image — logo, drawing, or photograph
3. Adjust settings:
   - **Resolution** — mesh density (higher = slower but more detail; 150–200 recommended)
   - **Max relief depth** — how tall the raised areas are in mm (default 10 mm)
   - **Base plate thickness** — flat bottom layer thickness (default 2 mm)
   - **Smoothing** — reduces jagged edges (default 1.0)
   - **Invert heightmap** — makes dark areas raised instead of light areas
4. Click **Generate STL**
5. Download the STL file when complete

### Photo Mode (Multi-angle Photos → Full 3D STL)
> Requires COLMAP installed via `setup.sh`

1. Click the **Photo Mode** tab
2. Upload 10–30 photos of the same object taken from different angles
3. Click **Generate STL**
4. Monitor progress in the log panel — this can take 15–40 minutes on CPU
5. Download the STL file when complete

**Photo tips for best results:**
- Walk around the object taking overlapping shots (~70% overlap)
- Shoot from high, mid, and low angles to cover the full shape
- Use diffuse, consistent lighting — avoid harsh shadows and reflections
- Avoid transparent or reflective objects (glass, mirrors, chrome)
- Keep the object in sharp focus throughout

---

## Printing the STL

1. Open the downloaded `.stl` file in **FlashPrint** (Flashforge's slicer)
2. The model is pre-scaled to fit the Adventurer 5M's 220×220×220 mm build volume
3. Slice and send to printer as normal

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `colmap not installed` error | Run `bash setup.sh` |
| Photo mode produces no model | Need more image overlap; shoot more angles |
| STL looks blocky | Increase Resolution slider in Artwork Mode |
| App won't start | Run `pip3 install -r requirements.txt --break-system-packages` |

---

## Open-source tools used

| Tool | Purpose |
|------|---------|
| [COLMAP](https://colmap.github.io/) | Structure-from-Motion + Multi-View Stereo |
| [trimesh](https://trimsh.org/) | Mesh processing and STL export |
| [Gradio](https://gradio.app/) | Local web GUI |
| [Pillow](https://python-pillow.org/) | Image loading and preprocessing |
| [SciPy](https://scipy.org/) | Heightmap smoothing |
