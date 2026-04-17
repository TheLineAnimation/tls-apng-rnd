# tls-apng-rnd

Python toolkit for converting PNG frame sequences into optimised Animated PNG (APNG) files. Wraps [apngasm](https://github.com/apngasm/apngasm), [Pillow](https://python-pillow.org/), FFmpeg and the [Tinify API](https://tinypng.com/developers) into a single configurable 5-stage pipeline with a CLI and importable library.

---

## Pipeline

| Stage | Tool | Purpose |
|-------|------|---------|
| 1 | Pillow | Resize frames to target dimensions |
| 2 | FFmpeg *(optional)* | Re-encode frames if needed |
| 3 | apngasm | Assemble frames into an APNG |
| 4 | Tinify API *(optional)* | Lossless compression |
| 5 | Cleanup | Remove temp files |

---

## Requirements

- Python 3.8+
- [Pillow](https://python-pillow.org/) — `pip install Pillow`
- [click](https://click.palletsprojects.com/) — `pip install click`
- [tqdm](https://github.com/tqdm/tqdm) — `pip install tqdm`
- [python-dotenv](https://github.com/theskumar/python-dotenv) — `pip install python-dotenv`
- [tinify](https://github.com/tinify/tinify-python) *(optional)* — `pip install tinify`
- FFmpeg on `PATH` *(optional)*
- `exe/apngasm.exe` — bundled in this repo (Windows)

Install all at once:

```bash
pip install Pillow click tqdm python-dotenv tinify
```

Copy `.env.example` to `.env` and add your Tinify API key:

```bash
cp .env.example .env
# then edit .env and set TINIFY_API_KEY
```

---

## Presets

Three built-in presets cover the most common output targets:

| Preset | Width | Height | FPS | Use case |
|--------|-------|--------|-----|----------|
| `profile_effects` | 450 | 880 | 12 | Profile animation effects |
| `avatar_decorations` | 288 | 288 | 12 | Square avatar decorations |
| `custom` | 512 | 512 | 25 | Arbitrary / fully configured |

---

## CLI Usage

### Single sequence

```bash
python apngc_cli.py process <INPUT_DIR> <OUTPUT_FILE> [OPTIONS]
```

```bash
# Use a preset
python apngc_cli.py process ./frames output.png --preset profile_effects

# Custom dimensions
python apngc_cli.py process ./frames anim.png --width 640 --height 480 --framerate 24

# Static (single-frame) export
python apngc_cli.py process ./frames frame.png --mode static

# Skip Tinify optimisation
python apngc_cli.py process ./frames output.png --no-optimize

# Save settings for next run
python apngc_cli.py process ./frames output.png --preset custom --save-config
```

### Batch (multiple sequences)

```bash
python apngc_cli.py batch <INPUT_DIR_1> <INPUT_DIR_2> ... [OPTIONS]
```

```bash
python apngc_cli.py batch ./seq1 ./seq2 ./seq3 --preset avatar_decorations --optimize
```

### Config file

```bash
# Save current options to .apngc.json
python apngc_cli.py config save --preset custom --width 400 --height 600

# Show current config
python apngc_cli.py config show
```

### List presets

```bash
python apngc_cli.py list-presets
```

---

## Library Usage

```python
from apngc_lib import APNGCConfig, APNGCProcessor, PRESETS

# From a preset
config = APNGCConfig.from_preset("profile_effects")

# Or fully custom
config = APNGCConfig(
    width=450,
    height=880,
    framerate=12,
    loop_count=0,          # 0 = loop forever
    hold_last_frame_ms=0,
    compression="7zip",
    optimize=True,
    tinify_key="YOUR_KEY",
    export_path="./output",
)

processor = APNGCProcessor(config)
success, output_path = processor.process_sequence("./frames", "output.png")
```

---

## Configuration

Settings can be stored in `.apngc.json` at the project root. The file is git-ignored by default because it may contain a Tinify API key.

Key options:

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `mode` | `animated` \| `static` | `animated` | Output mode |
| `width` | int | 450 | Frame width (px) |
| `height` | int | 880 | Frame height (px) |
| `framerate` | int | 12 | Frames per second |
| `loop_count` | int | 0 | Loop count (0 = forever) |
| `hold_last_frame_ms` | int | 0 | Extra hold on last frame (ms) |
| `compression` | `zlib` \| `7zip` \| `zopfli` | `7zip` | APNGASM compression method |
| `iterations` | int | 15 | Compression iterations (1–30) |
| `optimize` | bool | `true` | Run Tinify optimisation |
| `tinify_key` | string | — | Tinify API key |
| `keep_temp` | bool | `false` | Retain temp files after processing |
| `export_path` | string | `./output` | Output directory |

---

## Project Structure

```
tls-apng-rnd/
├── apngc_lib.py          # Core pipeline library
├── apngc_cli.py          # Click-based CLI
├── exe/
│   └── apngasm.exe       # Bundled apngasm binary (Windows)
├── output/               # Default output directory (git-ignored)
├── delivery/             # Delivery exports (git-ignored)
├── test_images_renamed/  # Sample frame sequences for testing
├── test_lib.py           # Library unit tests
├── test_lib_extended.py  # Extended library tests
├── test_cli.py           # CLI tests
├── test_apngasm.py       # apngasm integration tests
├── test_tinify_comparison.py  # Tinify optimisation comparison tests
├── PARAMETER_MAPPING.md  # Stage-by-stage parameter reference
└── APNGASM_CLI_REFERENCE.md   # apngasm CLI flag reference
```

---

## Running Tests

```bash
pytest test_lib.py test_cli.py test_apngasm.py -v
```

