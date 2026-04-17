#!/usr/bin/env python3
"""
APNGC CLI Test Suite - Phase 2
Tests all CLI commands and functionality
"""

import sys
from pathlib import Path
from click.testing import CliRunner
from apngc_cli import cli, get_config_path
from apngc_lib import APNGCConfig
import json

PROJECT_ROOT = Path(__file__).parent
TEST_IMAGE_DIR = PROJECT_ROOT / "test_images_renamed"
OUTPUT_DIR = PROJECT_ROOT / "output"


def test_help():
    """Test help commands"""
    print("\n[TEST 1] Help Commands")
    print("-" * 70)
    
    runner = CliRunner()
    
    # Main help
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "APNGC" in result.output
    print("✓ Main help works")
    
    # Command help
    result = runner.invoke(cli, ["process", "--help"])
    assert result.exit_code == 0
    assert "Process PNG sequence" in result.output
    print("✓ Process help works")
    
    # List presets help
    result = runner.invoke(cli, ["list-presets", "--help"])
    assert result.exit_code == 0
    print("✓ List-presets help works")
    
    return True


def test_list_presets():
    """Test list-presets command"""
    print("\n[TEST 2] List Presets Command")
    print("-" * 70)
    
    runner = CliRunner()
    
    # Basic list
    result = runner.invoke(cli, ["list-presets"])
    assert result.exit_code == 0
    assert "profile_effects" in result.output
    assert "avatar_decorations" in result.output
    assert "custom" in result.output
    print("✓ List presets works")
    print(result.output[:200])
    
    # Detailed list
    result = runner.invoke(cli, ["list-presets", "--detailed"])
    assert result.exit_code == 0
    assert "Description" in result.output
    print("✓ Detailed list works")
    
    return True


def test_process_command():
    """Test process command with preset"""
    print("\n[TEST 3] Process Command")
    print("-" * 70)
    
    runner = CliRunner()
    
    # Find test sequence
    test_folders = list(TEST_IMAGE_DIR.glob("Folder_*"))
    if not test_folders:
        print("✗ No test sequences found")
        return False
    
    test_folder = test_folders[0]
    
    # Process with preset
    with runner.isolated_filesystem():
        # Copy test data
        import shutil
        shutil.copytree(str(test_folder), "test_frames")
        
        result = runner.invoke(cli, [
            "process",
            "test_frames",
            "output.png",
            "--preset", "avatar_decorations",
            "--mode", "static",
            "--no-optimize"
        ])
        
        if result.exit_code == 0:
            print("✓ Process command succeeded")
            print(f"  Output: {Path('output.png').exists()}")
            return True
        else:
            print(f"✗ Process command failed: {result.output[:200]}")
            return False


def test_config_commands():
    """Test config management commands"""
    print("\n[TEST 4] Config Commands")
    print("-" * 70)
    
    runner = CliRunner()
    
    with runner.isolated_filesystem():
        # Test config show (no file)
        result = runner.invoke(cli, ["config", "show"])
        assert result.exit_code == 0
        assert "Preset" in result.output or "Mode" in result.output
        print("✓ Config show (default) works")
        
        # Test config save
        result = runner.invoke(cli, [
            "config", "save",
            "--preset", "profile_effects",
            "--optimize"
        ])
        assert result.exit_code == 0
        assert "Config saved" in result.output
        print("✓ Config save works")
        
        # Test config show (saved file)
        result = runner.invoke(cli, ["config", "show"])
        assert result.exit_code == 0
        assert "profile_effects" in result.output
        print("✓ Config show (saved) works")
        
        # Test config reset
        result = runner.invoke(cli, ["config", "reset"])
        assert result.exit_code == 0
        print("✓ Config reset works")
        
        return True


def test_version():
    """Test version output"""
    print("\n[TEST 5] Version Output")
    print("-" * 70)
    
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "apngc" in result.output
    print(f"✓ Version: {result.output.strip()}")
    
    return True


def test_preset_validation():
    """Test that presets are loaded correctly"""
    print("\n[TEST 6] Preset Validation")
    print("-" * 70)
    
    runner = CliRunner()
    
    # List presets and verify structure
    from apngc_lib import PRESETS
    
    for preset in PRESETS.list_all():
        name = preset["name"]
        mode = preset.get("mode")
        modes_supported = preset.get("modes_supported")
        
        assert mode in ["animated", "static"], f"Invalid mode for {name}"
        assert isinstance(modes_supported, list), f"modes_supported not list for {name}"
        assert mode in modes_supported, f"Mode not in supported for {name}"
        
        print(f"✓ {name}: mode={mode}, supports={modes_supported}")
    
    return True


def test_help_topics():
    """Test individual help topics"""
    print("\n[TEST 7] Help Topics")
    print("-" * 70)
    
    runner = CliRunner()
    
    topics = ["process", "batch", "config", "list-presets"]
    for topic in topics:
        result = runner.invoke(cli, [topic, "--help"])
        if result.exit_code == 0:
            print(f"✓ Help for '{topic}' works")
        else:
            print(f"✗ Help for '{topic}' failed")
            return False
    
    return True


# ============================================================================
# TEST RUNNER
# ============================================================================

def run_all_tests():
    """Run all CLI tests"""
    
    print("\n" + "=" * 70)
    print("APNGC CLI Test Suite - Phase 2")
    print("=" * 70)
    
    tests = [
        ("Help Commands", test_help),
        ("List Presets", test_list_presets),
        ("Process Command", test_process_command),
        ("Config Commands", test_config_commands),
        ("Version Output", test_version),
        ("Preset Validation", test_preset_validation),
        ("Help Topics", test_help_topics),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except AssertionError as e:
            print(f"✗ Assertion failed: {e}")
            results[test_name] = False
        except Exception as e:
            print(f"✗ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print("=" * 70)
    print(f"Result: {passed}/{total} tests passed")
    print("=" * 70 + "\n")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
