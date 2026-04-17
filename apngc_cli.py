#!/usr/bin/env python3
"""
APNGC CLI - Command-line interface for APNGC Library
Phase 2 Implementation

Usage:
  apngc process <input> <output> [OPTIONS]
  apngc batch <inputs...> [OPTIONS]
  apngc config <action> [OPTIONS]
  apngc list-presets
"""

import click
import json
from pathlib import Path
from typing import Optional, List
from tqdm import tqdm
import sys

from apngc_lib import APNGCConfig, APNGCProcessor, PRESETS


# ============================================================================
# CONFIG FILE MANAGEMENT
# ============================================================================

def get_config_path() -> Path:
    """Get .apngc.json config file path (project root)"""
    return Path.cwd() / ".apngc.json"


def load_config() -> APNGCConfig:
    """Load config from .apngc.json if it exists"""
    config_file = get_config_path()
    
    if config_file.exists():
        try:
            return APNGCConfig.from_json(str(config_file))
        except Exception as e:
            click.echo(f"⚠ Warning: Could not load config: {e}", err=True)
            return APNGCConfig()
    
    return APNGCConfig()


def save_config(config: APNGCConfig) -> None:
    """Save config to .apngc.json"""
    try:
        config.to_json(str(get_config_path()))
        click.echo(f"✓ Config saved to {get_config_path()}")
    except Exception as e:
        click.echo(f"✗ Failed to save config: {e}", err=True)


# ============================================================================
# CLI GROUP & SHARED OPTIONS
# ============================================================================

@click.group()
@click.version_option(version="1.0.0", prog_name="apngc")
def cli():
    """APNGC - Animated PNG Converter CLI
    
    Complete 5-stage pipeline for APNG creation and optimization.
    
    Examples:
      apngc process ./frames output.png --preset profile_effects
      apngc batch ./seq1 ./seq2 ./seq3 --preset avatar_decorations --optimize
      apngc config save --preset custom --width 400 --height 600
      apngc list-presets
    """
    pass


# ============================================================================
# COMMAND: PROCESS (Single Sequence)
# ============================================================================

@cli.command()
@click.argument("input_dir", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.argument("output_file", type=click.Path())
@click.option(
    "--preset",
    type=click.Choice(["profile_effects", "avatar_decorations", "custom"], case_sensitive=False),
    default=None,
    help="Use preset configuration"
)
@click.option(
    "--mode",
    type=click.Choice(["animated", "static"], case_sensitive=False),
    default=None,
    help="Processing mode (overrides preset)"
)
@click.option(
    "--width",
    type=int,
    default=None,
    help="Frame width in pixels"
)
@click.option(
    "--height",
    type=int,
    default=None,
    help="Frame height in pixels"
)
@click.option(
    "--framerate",
    type=int,
    default=None,
    help="Frames per second (animated mode only)"
)
@click.option(
    "--optimize/--no-optimize",
    default=True,
    help="Enable/disable Tinify compression (default: enabled)"
)
@click.option(
    "--tinify-key",
    type=str,
    default=None,
    help="Custom Tinify API key"
)
@click.option(
    "--compression",
    type=click.Choice(["zlib", "7zip", "zopfli"], case_sensitive=False),
    default=None,
    help="APNG compression method"
)
@click.option(
    "--save-config",
    is_flag=True,
    help="Save settings to .apngc.json for next run"
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Verbose output"
)
def process(input_dir, output_file, preset, mode, width, height, framerate, optimize, tinify_key, compression, save_config, verbose):
    """Process PNG sequence through APNGC pipeline
    
    INPUT_DIR: Directory containing PNG frames
    OUTPUT_FILE: Output APNG/PNG filename
    
    Examples:
      apngc process ./frames output.png --preset profile_effects
      apngc process ./frames frame.png --mode static
      apngc process ./frames anim.png --width 640 --height 480 --framerate 24
    """
    try:
        # Start with preset or defaults
        if preset:
            config = APNGCConfig.from_preset(preset)
            click.echo(f"📋 Using preset: {preset}")
        else:
            config = load_config() if get_config_path().exists() else APNGCConfig()
        
        # Override with CLI arguments
        if mode:
            config.mode = mode
        
        if width:
            config.width = width
        if height:
            config.height = height
        if framerate:
            config.framerate = framerate
        if tinify_key:
            config.tinify_key = tinify_key
        if compression:
            config.compression = compression
        
        config.optimize = optimize
        config.log_level = "DEBUG" if verbose else "INFO"
        
        # Initialize processor
        processor = APNGCProcessor(config)
        
        # Progress callback
        def progress_cb(current, total, stage):
            if verbose:
                click.echo(f"  {stage}: {current}/{total}")
        
        # Process sequence
        click.echo(f"🔄 Processing: {Path(input_dir).name}")
        success, output_path = processor.process_sequence(
            input_dir,
            output_file,
            progress_callback=progress_cb if verbose else None
        )
        
        if success:
            output_size = Path(output_path).stat().st_size / (1024 * 1024)
            click.echo(f"✓ Complete: {Path(output_path).name} ({output_size:.2f} MB)")
            
            if save_config:
                config.save_settings = True
                save_config_to_file(config)
            
            return 0
        else:
            click.echo(f"✗ Processing failed", err=True)
            return 1
    
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        return 1


# ============================================================================
# COMMAND: BATCH (Multiple Sequences)
# ============================================================================

@cli.command()
@click.argument("input_dirs", nargs=-1, required=True, type=click.Path(exists=True, file_okay=False))
@click.option(
    "--preset",
    type=click.Choice(["profile_effects", "avatar_decorations", "custom"], case_sensitive=False),
    default=None,
    help="Use preset configuration"
)
@click.option(
    "--mode",
    type=click.Choice(["animated", "static"], case_sensitive=False),
    default=None,
    help="Processing mode"
)
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False),
    default="./output",
    help="Output directory (default: ./output)"
)
@click.option(
    "--parallel",
    type=int,
    default=3,
    help="Number of parallel workers (default: 3)"
)
@click.option(
    "--optimize/--no-optimize",
    default=True,
    help="Enable/disable Tinify compression"
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Verbose output"
)
def batch(input_dirs, preset, mode, output_dir, parallel, optimize, verbose):
    """Process multiple PNG sequences in parallel
    
    INPUT_DIRS: One or more directories containing PNG frames
    
    Examples:
      apngc batch ./seq1 ./seq2 ./seq3 --preset profile_effects
      apngc batch ./frames/* --mode static --parallel 4
    """
    try:
        if not input_dirs:
            click.echo("✗ No input directories provided", err=True)
            return 1
        
        # Validate all directories exist
        valid_dirs = []
        for d in input_dirs:
            if Path(d).is_dir():
                valid_dirs.append(d)
            else:
                click.echo(f"⚠ Skipping non-existent: {d}", err=True)
        
        if not valid_dirs:
            click.echo("✗ No valid input directories", err=True)
            return 1
        
        # Load config
        if preset:
            config = APNGCConfig.from_preset(preset)
        else:
            config = load_config() if get_config_path().exists() else APNGCConfig()
        
        if mode:
            config.mode = mode
        
        config.optimize = optimize
        config.export_path = output_dir
        config.log_level = "DEBUG" if verbose else "INFO"
        
        # Initialize processor
        processor = APNGCProcessor(config)
        
        # Batch process
        click.echo(f"🔄 Batch processing {len(valid_dirs)} sequences (workers={parallel})...")
        results = processor.process_batch(valid_dirs, max_workers=parallel)
        
        # Summary
        passed = sum(1 for s, _ in results.values() if s)
        failed = len(results) - passed
        
        click.echo(f"\n{'='*60}")
        click.echo(f"✓ Batch complete: {passed}/{len(results)} succeeded")
        if failed > 0:
            click.echo(f"✗ {failed} failed")
        click.echo(f"{'='*60}")
        
        return 0 if failed == 0 else 1
    
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        return 1


# ============================================================================
# COMMAND: CONFIG (Configuration Management)
# ============================================================================

def save_config_to_file(config: APNGCConfig) -> None:
    """Helper to save config"""
    save_config(config)


@cli.command()
@click.argument("action", type=click.Choice(["show", "save", "reset", "remove"]))
@click.option(
    "--preset",
    type=click.Choice(["profile_effects", "avatar_decorations", "custom"], case_sensitive=False),
    help="Set preset"
)
@click.option(
    "--mode",
    type=click.Choice(["animated", "static"], case_sensitive=False),
    help="Set mode"
)
@click.option("--width", type=int, help="Set width")
@click.option("--height", type=int, help="Set height")
@click.option("--framerate", type=int, help="Set framerate")
@click.option("--optimize/--no-optimize", type=bool, help="Set optimization")
@click.option("--tinify-key", type=str, help="Set Tinify API key")
@click.option("--compression", type=click.Choice(["zlib", "7zip", "zopfli"]), help="Set compression")
def config(action, preset, mode, width, height, framerate, optimize, tinify_key, compression):
    """Manage .apngc.json configuration
    
    Actions:
      show   - Display current config
      save   - Save config with options
      reset  - Reset to defaults
      remove - Delete config file
    
    Examples:
      apngc config show
      apngc config save --preset profile_effects --optimize
      apngc config reset
    """
    try:
        config_file = get_config_path()
        
        if action == "show":
            if config_file.exists():
                current = APNGCConfig.from_json(str(config_file))
                click.echo(f"Current config ({config_file}):")
                click.echo(f"  Preset:       {current.preset_name}")
                click.echo(f"  Mode:         {current.mode}")
                click.echo(f"  Size:         {current.width}x{current.height}")
                click.echo(f"  Framerate:    {current.framerate}fps")
                click.echo(f"  Optimize:     {'yes' if current.optimize else 'no'}")
                click.echo(f"  Compression:  {current.compression}")
                click.echo(f"  Tinify Key:   {current.tinify_key[:10]}...")
            else:
                click.echo("No config file found. Using defaults.")
                current = APNGCConfig()
                click.echo(f"  Preset:       {current.preset_name}")
                click.echo(f"  Mode:         {current.mode}")
                click.echo(f"  Size:         {current.width}x{current.height}")
        
        elif action == "save":
            current = load_config()
            
            # Apply options
            if preset:
                preset_config = APNGCConfig.from_preset(preset)
                current = preset_config
            if mode:
                current.mode = mode
            if width:
                current.width = width
            if height:
                current.height = height
            if framerate:
                current.framerate = framerate
            if optimize is not None:
                current.optimize = optimize
            if tinify_key:
                current.tinify_key = tinify_key
            if compression:
                current.compression = compression
            
            save_config(current)
        
        elif action == "reset":
            if config_file.exists():
                config_file.unlink()
                click.echo(f"✓ Config reset (removed {config_file})")
            else:
                click.echo("Config already at defaults")
        
        elif action == "remove":
            if config_file.exists():
                config_file.unlink()
                click.echo(f"✓ Config file removed")
            else:
                click.echo("No config file to remove")
    
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        return 1


# ============================================================================
# COMMAND: LIST-PRESETS (Show Available Presets)
# ============================================================================

@cli.command()
@click.option("--detailed", is_flag=True, help="Show detailed preset info")
def list_presets(detailed):
    """List all available presets
    
    Examples:
      apngc list-presets
      apngc list-presets --detailed
    """
    presets = PRESETS.list_all()
    
    click.echo("Available Presets:")
    click.echo("=" * 70)
    
    for preset in presets:
        name = preset["name"]
        mode = preset.get("mode", "animated")
        width = preset["width"]
        height = preset["height"]
        fps = preset.get("framerate", 0)
        desc = preset.get("description", "")
        
        if detailed:
            click.echo(f"\n📋 {name}")
            click.echo(f"   Type:        {mode}")
            click.echo(f"   Size:        {width}x{height}")
            click.echo(f"   Framerate:   {fps}fps" if fps > 0 else f"   Framerate:   N/A (static)")
            click.echo(f"   Description: {desc}")
            modes = preset.get("modes_supported", [mode])
            click.echo(f"   Supported:   {', '.join(modes)}")
        else:
            fps_str = f"{fps}fps" if fps > 0 else "static"
            click.echo(f"  {name:<25} {width}x{height:<8} {mode:<10} {fps_str:<8} {desc}")
    
    click.echo("\n" + "=" * 70)
    click.echo(f"Total: {len(presets)} presets available")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    cli()
