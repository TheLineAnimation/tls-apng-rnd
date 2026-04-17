"""
APNGC Library - Phase 1
Animated PNG Converter Python Implementation

Complete 5-stage pipeline:
1. Resize (Pillow)
2. FFmpeg (optional)
3. APNGASM (CLI)
4. Tinify API (optimization)
5. Cleanup (temp files)
"""

import os
import sys
import json
import shutil
import subprocess
import tempfile
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import re

try:
    from PIL import Image
except ImportError:
    raise ImportError("Pillow required: pip install Pillow")

try:
    import tinify
except ImportError:
    tinify = None

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed; set TINIFY_API_KEY in environment manually


class PRESETS:
    """Built-in preset configurations"""
    
    PROFILE_EFFECTS = {
        "name": "profile_effects",
        "mode": "animated",
        "modes_supported": ["animated"],
        "width": 450,
        "height": 880,
        "framerate": 12,
        "description": "Profile animation effects"
    }
    
    AVATAR_DECORATIONS = {
        "name": "avatar_decorations",
        "mode": "animated",
        "modes_supported": ["animated"],
        "width": 288,
        "height": 288,
        "framerate": 12,
        "description": "Square avatar decorations"
    }
    
    CUSTOM = {
        "name": "custom",
        "mode": "animated",
        "modes_supported": ["animated", "static"],
        "width": 512,
        "height": 512,
        "framerate": 25,
        "description": "Custom configuration"
    }
    
    @classmethod
    def get(cls, preset_name: str) -> Optional[Dict]:
        """Get preset by name"""
        presets = {
            "profile_effects": cls.PROFILE_EFFECTS,
            "avatar_decorations": cls.AVATAR_DECORATIONS,
            "custom": cls.CUSTOM,
        }
        return presets.get(preset_name.lower())
    
    @classmethod
    def list_all(cls) -> List[Dict]:
        """List all available presets"""
        return [
            cls.PROFILE_EFFECTS,
            cls.AVATAR_DECORATIONS,
            cls.CUSTOM,
        ]


@dataclass
class APNGCConfig:
    """Complete APNGC configuration"""
    
    # Mode selection
    mode: str = "animated"  # "animated" or "static"
    
    # Stage 1: Resize
    width: int = 450
    height: int = 880
    resize_quality: str = "high"  # high=LANCZOS, medium=BILINEAR, fast=NEAREST
    
    # Stage 2: FFmpeg (optional)
    framerate: int = 12
    
    # Stage 3: APNGASM (animated only)
    loop_count: int = 0  # 0 = forever
    hold_last_frame_ms: int = 0
    compression: str = "7zip"  # zlib, 7zip, zopfli
    iterations: int = 15  # 1-30
    
    # Stage 4: Tinify
    optimize: bool = True
    tinify_key: str = os.environ.get("TINIFY_API_KEY", "")
    
    # Stage 5: Cleanup & Output
    keep_temp: bool = False
    export_path: str = "./output"
    
    # Metadata
    preset_name: str = "custom"
    append_preset_to_filename: bool = True
    save_settings: bool = True
    
    # Logging
    log_level: str = "INFO"

    
    @classmethod
    def from_preset(cls, preset_name: str) -> "APNGCConfig":
        """Create config from preset"""
        preset = PRESETS.get(preset_name)
        if not preset:
            raise ValueError(f"Unknown preset: {preset_name}")
        
        config = cls(
            preset_name=preset["name"],
            mode=preset["mode"],
            width=preset["width"],
            height=preset["height"],
            framerate=preset["framerate"]
        )
        return config

    @classmethod
    def from_json(cls, filepath: str) -> "APNGCConfig":
        """Load configuration from JSON file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls(**data)
    
    def to_json(self, filepath: str) -> None:
        """Save configuration to JSON file"""
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(asdict(self), f, indent=2)
    
    def generate_output_filename(self, base_name: str, include_dimensions: bool = False) -> str:
        """
        Generate output filename with optional preset name
        
        Examples:
            "animation.png" with preset="profile_effects" → "animation_profile_effects.png"
            "frame.png" with include_dimensions=True → "frame_450x880.png"
        """
        if not base_name.endswith('.png'):
            base_name += '.png'
        
        name_parts = base_name.rsplit('.png', 1)[0]
        
        if self.append_preset_to_filename and self.preset_name != "custom":
            name_parts = f"{name_parts}_{self.preset_name}"
        
        if include_dimensions:
            name_parts = f"{name_parts}_{self.width}x{self.height}"
        
        return f"{name_parts}.png"


# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configure logging for APNGC operations"""
    logger = logging.getLogger("APNGC")
    logger.setLevel(getattr(logging, level))
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    formatter = logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger


# ============================================================================
# STAGE 1: RESIZE (Pillow)
# ============================================================================

class ResizeStage:
    """Stage 1: Resize PNG sequences using Pillow"""
    
    QUALITY_FILTERS = {
        "high": Image.Resampling.LANCZOS,
        "medium": Image.Resampling.BILINEAR,
        "fast": Image.Resampling.NEAREST,
    }
    
    def __init__(self, config: APNGCConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.filter = self.QUALITY_FILTERS.get(config.resize_quality, Image.Resampling.LANCZOS)
    
    def resize_image(self, input_path: str, output_path: str) -> bool:
        """Resize single image"""
        try:
            img = Image.open(input_path)
            original_size = img.size
            
            # Resize with quality filter
            resized = img.resize(
                (self.config.width, self.config.height),
                self.filter
            )
            
            # Save as PNG
            resized.save(output_path, 'PNG', quality=95)
            
            self.logger.debug(
                f"Resized {Path(input_path).name}: "
                f"{original_size} → {self.config.width}x{self.config.height}"
            )
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to resize {input_path}: {e}")
            return False
    
    def process_sequence(
        self,
        input_dir: str,
        output_dir: str,
        progress_callback: Optional[Callable] = None
    ) -> Tuple[bool, List[str]]:
        """
        Process PNG sequence: resize all frames
        
        Returns: (success, list_of_resized_paths)
        """
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Find all PNG files
        png_files = sorted(input_path.glob("*.png"))
        if not png_files:
            self.logger.error(f"No PNG files found in {input_dir}")
            return False, []
        
        self.logger.info(f"Stage 1: Resizing {len(png_files)} frames...")
        
        resized_paths = []
        for i, png_file in enumerate(png_files):
            output_file = output_path / png_file.name
            success = self.resize_image(str(png_file), str(output_file))
            
            if success:
                resized_paths.append(str(output_file))
            
            if progress_callback:
                progress_callback(i + 1, len(png_files), "Resizing")
        
        if len(resized_paths) == len(png_files):
            self.logger.info(f"Stage 1: ✓ Resized {len(resized_paths)} frames")
            return True, resized_paths
        else:
            self.logger.error(f"Stage 1: ✗ Only {len(resized_paths)}/{len(png_files)} frames resized")
            return False, resized_paths


# ============================================================================
# STAGE 3: APNGASM (CLI)
# ============================================================================

class APNGASMStage:
    """Stage 3: Assemble PNG frames into APNG using APNGASM CLI"""
    
    COMPRESSION = {
        "zlib": "-z0",
        "7zip": "-z1",
        "zopfli": "-z2",
    }
    
    def __init__(self, config: APNGCConfig, apngasm_exe: str, logger: logging.Logger):
        self.config = config
        self.apngasm_exe = Path(apngasm_exe)
        self.logger = logger
        
        if not self.apngasm_exe.exists():
            raise FileNotFoundError(f"APNGASM not found: {apngasm_exe}")
    
    def calculate_frame_delay(self) -> Tuple[int, int]:
        """
        Convert framerate to APNGASM delay format
        
        APNGASM uses: "numerator denominator" format
        Example: 12 fps = 83.33ms = "5 60" format
        
        Returns: (numerator, denominator)
        """
        framerate = self.config.framerate
        
        # Common mappings
        common_rates = {
            10: (1, 10),
            12: (5, 60),  # 83.33ms
            15: (1, 15),
            24: (1, 24),
            25: (1, 25),
            30: (1, 30),
            60: (1, 60),
        }
        
        if framerate in common_rates:
            return common_rates[framerate]
        
        # Fallback: approximate with denominator 100
        numerator = round(100 / framerate)
        return (numerator, 100)
    
    def assemble_apng(
        self,
        output_file: str,
        input_files: List[str],
        progress_callback: Optional[Callable] = None
    ) -> bool:
        """Assemble PNG frames into APNG"""
        try:
            # Build command
            cmd = [str(self.apngasm_exe), output_file] + input_files
            
            # Add frame delay
            numerator, denominator = self.calculate_frame_delay()
            cmd.extend([str(numerator), str(denominator)])
            
            # Add loop option
            if self.config.loop_count >= 0:
                cmd.append(f"-l{self.config.loop_count}")
            
            # Add compression method
            compression_opt = self.COMPRESSION.get(self.config.compression, "-z1")
            cmd.append(compression_opt)
            
            # Add iterations
            cmd.append(f"-i{self.config.iterations}")
            
            self.logger.debug(f"APNGASM command: {' '.join(cmd[:3])} ... {' '.join(cmd[-4:])}")
            
            # Run APNGASM
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                stdin=subprocess.DEVNULL,
                timeout=120
            )
            
            if result.returncode == 0:
                out_size = Path(output_file).stat().st_size / (1024 * 1024)  # MB
                self.logger.info(
                    f"Stage 3: ✓ APNG assembled: {out_size:.2f} MB "
                    f"({len(input_files)} frames, {self.config.framerate}fps)"
                )
                return True
            else:
                self.logger.error(f"Stage 3: ✗ APNGASM failed: {result.stderr[:200]}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error("Stage 3: ✗ APNGASM timeout (>120s)")
            return False
        except Exception as e:
            self.logger.error(f"Stage 3: ✗ APNGASM error: {e}")
            return False


# ============================================================================
# STAGE 4: TINIFY (API)
# ============================================================================

class TinifyStage:
    """Stage 4: Optimize APNG using Tinify compression API"""
    
    def __init__(self, config: APNGCConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
        
        if config.optimize and not config.tinify_key:
            self.logger.warning("Stage 4: Optimize enabled but no Tinify API key provided")
        
        if tinify and config.tinify_key:
            tinify.key = config.tinify_key
    
    def compress_apng(
        self,
        input_file: str,
        output_file: str,
        progress_callback: Optional[Callable] = None
    ) -> bool:
        """Compress APNG using Tinify API"""
        
        if not self.config.optimize:
            self.logger.info("Stage 4: Skipped (optimize disabled)")
            return True
        
        if not tinify:
            self.logger.warning("Stage 4: Skipped (tinify not installed: pip install tinify)")
            return True
        
        if not self.config.tinify_key:
            self.logger.warning("Stage 4: Skipped (no Tinify API key)")
            return True
        
        try:
            input_size = Path(input_file).stat().st_size / (1024 * 1024)
            
            self.logger.info(f"Stage 4: Uploading to Tinify API ({input_size:.2f} MB)...")
            
            source = tinify.from_file(input_file)
            source.to_file(output_file)
            
            output_size = Path(output_file).stat().st_size / (1024 * 1024)
            compression = (1 - output_size / input_size) * 100
            
            self.logger.info(
                f"Stage 4: ✓ Compressed: {input_size:.2f}MB → {output_size:.2f}MB "
                f"({compression:.1f}% reduction)"
            )
            return True
            
        except tinify.Error as e:
            self.logger.error(f"Stage 4: ✗ Tinify error: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Stage 4: ✗ Unexpected error: {e}")
            return False


# ============================================================================
# STAGE 5: CLEANUP
# ============================================================================

class CleanupStage:
    """Stage 5: Clean up temporary files"""
    
    def __init__(self, config: APNGCConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
    
    def cleanup_temp_dirs(self, temp_dirs: List[str]) -> bool:
        """Remove temporary directories"""
        
        if self.config.keep_temp:
            self.logger.info("Stage 5: Keeping temp files (keep_temp=True)")
            return True
        
        errors = []
        for temp_dir in temp_dirs:
            try:
                if Path(temp_dir).exists():
                    shutil.rmtree(temp_dir)
                    self.logger.debug(f"Removed temp dir: {temp_dir}")
            except Exception as e:
                errors.append((temp_dir, str(e)))
                self.logger.debug(f"Could not remove {temp_dir}: {e}")
        
        if errors:
            self.logger.warning(f"Stage 5: Cleanup completed with {len(errors)} minor errors (non-fatal)")
            return True  # Non-fatal
        
        self.logger.info("Stage 5: ✓ Temp files cleaned up")
        return True


# ============================================================================
# MAIN PROCESSOR
# ============================================================================

class APNGCProcessor:
    """
    Complete APNGC Pipeline Processor
    Handles all 5 stages in sequence
    """
    
    def __init__(
        self,
        config: Optional[APNGCConfig] = None,
        apngasm_exe: str = "./exe/apngasm.exe",
        log_level: str = "INFO"
    ):
        self.config = config or APNGCConfig()
        self.logger = setup_logging(self.config.log_level)
        
        # Initialize stages
        self.resize = ResizeStage(self.config, self.logger)
        self.apngasm = APNGASMStage(self.config, apngasm_exe, self.logger)
        self.tinify = TinifyStage(self.config, self.logger)
        self.cleanup = CleanupStage(self.config, self.logger)
        
        self.logger.info("=" * 70)
        self.logger.info(f"APNGC Processor Initialized")
        self.logger.info(f"Mode: {self.config.mode.upper()} | "
                        f"Preset: {self.config.preset_name} | "
                        f"Size: {self.config.width}x{self.config.height}")
        if self.config.mode == "animated":
            self.logger.info(f"Framerate: {self.config.framerate}fps | "
                            f"Compression: {self.config.compression}")
        self.logger.info("=" * 70)
    
    
    def process_static_sequence(
        self,
        input_dir: str,
        output_filename: str,
        progress_callback: Optional[Callable] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Process PNG sequence for STATIC output (just resize, no animation)
        
        Returns: (success, output_filepath or None)
        """
        try:
            start_time = datetime.now()
            
            # Generate filename with preset if enabled
            if not output_filename.endswith('.png'):
                output_filename += '.png'
            output_filename_full = self.config.generate_output_filename(
                output_filename.replace('.png', ''),
                include_dimensions=False
            )
            
            # Create output directory
            output_dir = Path(self.config.export_path)
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = str(output_dir / output_filename_full)
            
            sequence_name = Path(input_dir).name
            self.logger.info(f"\n▶ Processing static sequence: {sequence_name}")
            self.logger.info(f"  Mode: STATIC (resize only)")
            
            # STAGE 1: RESIZE
            temp_work = tempfile.mkdtemp(prefix="apngasm_resize_")
            try:
                success, resized_files = self.resize.process_sequence(
                    input_dir, temp_work, progress_callback
                )
                if not success or not resized_files:
                    raise Exception("Stage 1 failed: resize")
                
                # For static mode, take first resized frame
                if resized_files:
                    first_frame = Path(resized_files[0])
                    shutil.copy(str(first_frame), output_file)
                    self.logger.info(f"  Copied first frame to output")
            finally:
                # Cleanup temp directory
                if Path(temp_work).exists():
                    shutil.rmtree(temp_work)
            
            # STAGE 4: TINIFY (optional compression for static mode)
            if self.config.optimize and self.tinify:
                success = self.tinify.compress_apng(output_file, output_file, progress_callback)
                if not success:
                    self.logger.warning("  Tinify compression failed, continuing with uncompressed output")
            
            elapsed = (datetime.now() - start_time).total_seconds()
            final_size = Path(output_file).stat().st_size / (1024 * 1024)
            
            self.logger.info(f"✓ Complete: {sequence_name}")
            self.logger.info(f"  Output: {output_file}")
            self.logger.info(f"  Size: {final_size:.2f} MB | Time: {elapsed:.1f}s")
            
            return True, output_file
            
        except Exception as e:
            self.logger.error(f"✗ Static processing failed: {e}")
            return False, None
    
    def process_sequence(
        self,
        input_dir: str,
        output_filename: str,
        progress_callback: Optional[Callable] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Process PNG sequence through pipeline
        
        Routes to static or animated processing based on mode config
        
        Args:
            input_dir: Directory containing PNG frames
            output_filename: Output filename (e.g., "animation.png")
            progress_callback: Optional callback(current, total, stage_name)
        
        Returns:
            (success, output_filepath or None)
        """
        
        if self.config.mode == "static":
            return self.process_static_sequence(input_dir, output_filename, progress_callback)
        
        elif self.config.mode != "animated":
            self.logger.error(f"Unknown mode: {self.config.mode}")
            return False, None
        
        # ANIMATED MODE
        
        
        try:
            start_time = datetime.now()
            temp_dirs = []
            
            # Generate filename with preset if enabled
            output_filename_full = self.config.generate_output_filename(
                output_filename.replace('.png', ''),
                include_dimensions=False
            )
            
            # Create output directory
            output_dir = Path(self.config.export_path)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Create temp directory for resized frames
            temp_work = tempfile.mkdtemp(prefix="apngasm_resize_")
            temp_dirs.append(temp_work)
            
            sequence_name = Path(input_dir).name
            self.logger.info(f"\n▶ Processing sequence: {sequence_name}")
            self.logger.info(f"  Mode: ANIMATED | Preset: {self.config.preset_name}")
            
            # STAGE 1: RESIZE
            success, resized_files = self.resize.process_sequence(
                input_dir, temp_work, progress_callback
            )
            if not success or not resized_files:
                raise Exception("Stage 1 failed: resize")
            
            # STAGE 3: APNGASM (skip Stage 2 for now - optional FFmpeg)
            output_file = str(output_dir / output_filename_full)
            success = self.apngasm.assemble_apng(output_file, resized_files, progress_callback)
            if not success:
                raise Exception("Stage 3 failed: APNGASM assembly")
            
            # STAGE 4: TINIFY
            tinify_output = output_file.replace(".png", "_optimized.png")
            success = self.tinify.compress_apng(output_file, tinify_output, progress_callback)
            
            if success and Path(tinify_output).exists():
                # Use optimized version
                Path(tinify_output).replace(output_file)
                self.logger.info(f"Using Tinify-optimized output")
            
            # STAGE 5: CLEANUP
            self.cleanup.cleanup_temp_dirs(temp_dirs)
            
            elapsed = (datetime.now() - start_time).total_seconds()
            final_size = Path(output_file).stat().st_size / (1024 * 1024)
            
            self.logger.info(f"✓ Complete: {sequence_name}")
            self.logger.info(f"  Output: {output_file}")
            self.logger.info(f"  Size: {final_size:.2f} MB | Time: {elapsed:.1f}s")
            
            return True, output_file
            
        except Exception as e:
            self.logger.error(f"✗ Processing failed: {e}")
            # Attempt cleanup on error
            try:
                self.cleanup.cleanup_temp_dirs(temp_dirs)
            except:
                pass
            return False, None
    
    def process_batch(
        self,
        input_dirs: List[str],
        output_filenames: Optional[List[str]] = None,
        max_workers: int = 5,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Tuple[bool, Optional[str]]]:
        """
        Process multiple sequences in parallel
        
        Returns:
            {sequence_name: (success, output_path), ...}
        """
        
        if not output_filenames:
            output_filenames = [f"{Path(d).name}.png" for d in input_dirs]
        
        results = {}
        
        self.logger.info(f"▶ Batch processing {len(input_dirs)} sequences (workers={max_workers})")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    self.process_sequence,
                    input_dir,
                    output_file,
                    progress_callback
                ): (input_dir, output_file)
                for input_dir, output_file in zip(input_dirs, output_filenames)
            }
            
            completed = 0
            for future in as_completed(futures):
                completed += 1
                input_dir, output_file = futures[future]
                seq_name = Path(input_dir).name
                
                try:
                    success, output_path = future.result()
                    results[seq_name] = (success, output_path)
                    status = "✓" if success else "✗"
                    self.logger.info(f"{status} {seq_name} ({completed}/{len(input_dirs)})")
                except Exception as e:
                    self.logger.error(f"✗ {seq_name}: {e}")
                    results[seq_name] = (False, None)
        
        # Summary
        passed = sum(1 for s, _ in results.values() if s)
        self.logger.info(f"\n{'='*70}")
        self.logger.info(f"Batch complete: {passed}/{len(input_dirs)} sequences successful")
        self.logger.info(f"{'='*70}\n")
        
        return results


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def quick_process(
    input_dir: str,
    output_file: str = "output.png",
    width: int = 450,
    height: int = 880,
    framerate: int = 12,
    tinify_key: str = ""
) -> Tuple[bool, Optional[str]]:
    """Quick conversion with common settings"""
    
    config = APNGCConfig(
        width=width,
        height=height,
        framerate=framerate,
        tinify_key=tinify_key,
        optimize=bool(tinify_key)
    )
    
    processor = APNGCProcessor(config)
    return processor.process_sequence(input_dir, output_file)


if __name__ == "__main__":
    # Example usage
    config = APNGCConfig(
        width=450,
        height=880,
        framerate=12,
        optimize=False
    )
    
    processor = APNGCProcessor(config)
    
    # Test with sample data
    test_dir = Path("./test_images_renamed/Folder_01")
    if test_dir.exists():
        success, output = processor.process_sequence(str(test_dir), "test_output.png")
        print(f"Result: {success}, Output: {output}")
