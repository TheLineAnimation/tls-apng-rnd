# APNGC Phase 1 - Complete Parameter Reference

## Stage-by-Stage Parameter Mapping

### STAGE 1: RESIZE
**Input**: PNG sequences (2304x1296 by default, variable)  
**Output**: Resized PNG sequences (configurable dimensions)  
**Tool**: Pillow (lightweight, fast, sufficient for resizing)

| Parameter | Type | Source | Range | Default | Notes |
|-----------|------|--------|-------|---------|-------|
| `width` | int | UI Input | 32-4096 | 450 | Output frame width |
| `height` | int | UI Input | 32-4096 | 880 | Output frame height |
| `quality` | enum | Config | high/medium/fast | high | Resampling filter: LANCZOS/BILINEAR/NEAREST |

**Pillow vs FFmpeg Decision:**
- ✓ **Use Pillow** for Stage 1
  - Simpler, faster, no subprocess overhead
  - Pure Python, no external dependency
  - Sufficient quality for animation frames
  - Lower memory overhead
- FFmpeg is reserved for Stage 2 (sequence encoding if needed)

---

### STAGE 2: FFMPEG (Optional)
**Input**: Resized PNG sequences  
**Output**: Encoded PNG frames (temp directory)  
**Status**: Optional - may be skipped if direct APNGASM assembly works

| Parameter | Type | Source | Notes |
|-----------|------|--------|-------|
| `codec` | enum | UI | Not directly exposed in current APNGC.exe |
| `framerate` | int | UI Input | From FRAMERATE field |

**Current UI Shows**: FRAMERATE = 12 fps

---

### STAGE 3: APNGASM
**Input**: PNG sequences (resized)  
**Output**: APNG file  

| Parameter | Type | Source | Default | UI Control |
|-----------|------|--------|---------|-----------|
| `width` | int | Inherited from Stage 1 | 450 | WIDTH input |
| `height` | int | Inherited from Stage 1 | 880 | HEIGHT input |
| `framerate` | int | UI Input | 12 | FRAMERATE field |
| `loop_count` | int | UI Input | 0 | LOOPS (0=forever) |
| `hold_last_frame_ms` | int | UI Input | 0 | HOLD LAST FRAME field |
| `compression` | enum | Config | 7zip (-z1) | Fixed in current impl |
| `iterations` | int | Config | 15 | Fixed in current impl |

**APNGASM CLI Arguments**:
```bash
apngasm.exe output.png frame1.png frame2.png ...
  [delay as "numerator denominator"]
  [-l{loop_count}]
  [-z{compression}]
  [-i{iterations}]
```

**Frame Delay Calculation**:
- Given framerate (12 fps from UI)
- Frame duration = 1000ms / framerate
- Example: 12 fps → ~83ms per frame → `5 60` format

---

### STAGE 4: TINIFY API
**Input**: APNG file (unoptimized)  
**Output**: APNG file (optimized)

| Parameter | Type | Source | Required | UI Control |
|-----------|------|--------|----------|-----------|
| `api_key` | string | UI Input | YES | TINIFY KEY field |
| `enable_optimize` | bool | UI Toggle | NO | OPTIMIZE checkbox |
| `input_file` | path | From Stage 3 | YES | Auto from prev stage |
| `output_file` | path | Derived | YES | Auto generated |

**Current UI**: 
- TINIFY KEY: `3c9qxnDMXCybR9hJNP9SwNfXK2hs`
- OPTIMIZE: ✓ (checked)

**API Integration**:
- Uses Tinify SDK via `tinify.key = api_key`
- Compresses file: `tinify.from_file(input).to_file(output)`
- Error handling for invalid key, rate limits

---

### STAGE 5: CLEANUP
**Input**: Temp directories  
**Output**: Deleted files

| Parameter | Type | Handling | Notes |
|-----------|------|----------|-------|
| `temp_dir` | path | Auto managed | /temp/apngasm_* |
| `keep_temp` | bool | Config | For debugging |
| `error_tolerance` | bool | Graceful | Ignore WinError 3 |

**Current Issue**: Race condition on cleanup  
**Solution**: Use try/except with logging, don't fail on temp cleanup errors

---

## UI Control Mapping

```
┌─────────────────────────────────────────┐
│ SETTINGS                                │
├─────────────────────────────────────────┤
│ ├─ profile_effects (dropdown)           │
│ ├─ WIDTH: 450                           │ → STAGE 1, STAGE 3
│ ├─ HEIGHT: 880                          │ → STAGE 1, STAGE 3
│ ├─ FRAMERATE: 12                        │ → STAGE 3 (frame delay calc)
│ ├─ OPTIMIZE: ✓ (checkbox)               │ → STAGE 4 (enable Tinify)
│ ├─ TINIFY KEY: [api_key]                │ → STAGE 4 (compression)
│ ├─ LOOPS (0=FOREVER): 0                 │ → STAGE 3 (-l parameter)
│ ├─ HOLD LAST FRAME (MS): 0              │ → STAGE 3 (animation timing)
│ ├─ EXPORT PATH: /profile_effects/...    │ → STAGE 5 (output location)
│ └─ Save settings on convert: ✓          │ → Config persistence
└─────────────────────────────────────────┘
```

---

## Complete Parameter Structure (Python Class)

```python
class APNGCConfig:
    # Stage 1: Resize
    width: int = 450
    height: int = 880
    resize_quality: str = "high"  # LANCZOS
    
    # Stage 2: FFmpeg (optional)
    framerate: int = 12
    
    # Stage 3: APNGASM
    loop_count: int = 0  # 0 = forever
    hold_last_frame_ms: int = 0
    compression: str = "7zip"  # -z1
    iterations: int = 15  # -i15
    
    # Stage 4: Tinify
    optimize: bool = True
    tinify_key: str = ""
    
    # Stage 5: Cleanup
    keep_temp: bool = False
    export_path: str = "./output"
    
    # Metadata
    profile_effects: str = "non-optimised"
    save_settings: bool = True
```

---

## Missing Parameters to Add

Based on analysis of APNGC.exe vs complete pipeline:

| Feature | Current | Status | Needed? |
|---------|---------|--------|---------|
| **Input validation** | ✓ Drag & drop support | Basic | ✓ Add path validation |
| **Batch processing** | ✓ Parallel (5 sequences) | Present | ✓ Keep concurrent support |
| **Progress tracking** | ✓ Progress bar (0%) | UI element | ✓ Implement callbacks |
| **Error handling** | Partial | Needs work | ✓ Comprehensive try/except |
| **Config persistence** | ✓ Save settings checkbox | Present | ✓ JSON config file |
| **Temp directory** | Not visible | Hidden | ✓ Make configurable |
| **Frame delay mode** | Fixed | Fixed | ✗ Not configurable in UI |
| **Compression level** | Fixed (-z1) | Fixed | ○ Consider adding option |
| **Iteration count** | Fixed (-i15) | Fixed | ○ Consider adding option |

---

## Framerate to APNGASM Delay Conversion

**Formula**: 
```
frame_delay_ms = 1000 / framerate
frame_delay_fraction = frame_delay_ms / 10  (in centiseconds)

Example:
- framerate = 12 fps
- frame_delay_ms = 1000 / 12 = 83.33 ms
- frame_delay_fraction = 83.33 / 10 = 8.333 centiseconds
- APNGASM format: "5 60" (≈ 83.33ms)

Common mappings:
- 10 fps → 100ms   → "1 10"   or "10 100"
- 12 fps → 83ms    → "5 60"   or "1 12" 
- 25 fps → 40ms    → "1 25"   or "4 100"
- 30 fps → 33ms    → "1 30"   or "3 100"
```

---

## Implementation Checklist

- [ ] **Stage 1 (Resize)**: Pillow implementation with quality presets
- [ ] **Stage 2 (FFmpeg)**: Optional, skip if direct APNGASM works
- [ ] **Stage 3 (APNGASM)**: Full CLI parameter support
- [ ] **Stage 4 (Tinify)**: API integration with error handling
- [ ] **Stage 5 (Cleanup)**: Graceful temp directory cleanup
- [ ] **Config System**: Save/load from JSON
- [ ] **Batch Processing**: Concurrent sequence handling
- [ ] **Progress Tracking**: Callback system for UI updates
- [ ] **Error Handling**: Comprehensive exception handling
- [ ] **Frame Delay**: Automatic fps → APNGASM format conversion
- [ ] **Validation**: Input path, API key, output directory

---

*Reference Version: 1.0 | Generated: 2026-03-05*
