#!/usr/bin/env python3
"""
APNGC Library Extended Test Suite - Phase 1+ Features
Tests preset system, modes, and advanced features
"""

import os
import sys
from pathlib import Path
from apngc_lib import APNGCConfig, APNGCProcessor, PRESETS

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Get project root
PROJECT_ROOT = Path(__file__).parent
TEST_IMAGE_DIR = PROJECT_ROOT / "test_images_renamed"
OUTPUT_DIR = PROJECT_ROOT / "output"
APNGASM_EXE = PROJECT_ROOT / "exe" / "apngasm.exe"


def test_preset_system():
    """Test preset loading and configuration"""
    print("\n[TEST 1] Preset System")
    print("-" * 70)
    
    try:
        # Test listing presets
        presets = PRESETS.list_all()
        print(f"✓ Available presets: {len(presets)}")
        for preset in presets:
            print(f"  - {preset['name']}: {preset['width']}x{preset['height']}")
        
        # Test loading profile_effects preset
        config1 = APNGCConfig.from_preset("profile_effects")
        assert config1.width == 450 and config1.height == 880
        assert config1.preset_name == "profile_effects"
        print(f"✓ Loaded preset: profile_effects (450x880)")
        
        # Test loading avatar_decorations preset
        config2 = APNGCConfig.from_preset("avatar_decorations")
        assert config2.width == 288 and config2.height == 288
        assert config2.preset_name == "avatar_decorations"
        print(f"✓ Loaded preset: avatar_decorations (288x288)")
        
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


def test_mode_selection():
    """Test animated vs static mode"""
    print("\n[TEST 2] Mode Selection")
    print("-" * 70)
    
    try:
        # Animated mode
        config_anim = APNGCConfig(mode="animated")
        assert config_anim.mode == "animated"
        print(f"✓ Animated mode configured")
        
        # Static mode
        config_static = APNGCConfig(mode="static")
        assert config_static.mode == "static"
        print(f"✓ Static mode configured")
        
        # Invalid mode should be handled gracefully
        config_invalid = APNGCConfig(mode="invalid")
        print(f"✓ Invalid mode accepted (will be handled at runtime)")
        
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


def test_filename_generation():
    """Test output filename generation with preset"""
    print("\n[TEST 3] Filename Generation")
    print("-" * 70)
    
    try:
        # With preset name appended
        config = APNGCConfig.from_preset("profile_effects")
        config.append_preset_to_filename = True
        filename = config.generate_output_filename("animation")
        assert filename == "animation_profile_effects.png"
        print(f"✓ Filename with preset: {filename}")
        
        # Without preset name
        config.append_preset_to_filename = False
        filename = config.generate_output_filename("animation")
        assert filename == "animation.png"
        print(f"✓ Filename without preset: {filename}")
        
        # With dimensions
        filename = config.generate_output_filename("frame", include_dimensions=True)
        assert filename == "frame_450x880.png"
        print(f"✓ Filename with dimensions: {filename}")
        
        # Custom preset (should not append)
        config_custom = APNGCConfig(preset_name="custom")
        filename = config_custom.generate_output_filename("output")
        assert filename == "output.png"
        print(f"✓ Custom preset doesn't append: {filename}")
        
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tinify_configuration():
    """Test Tinify API key configuration"""
    print("\n[TEST 4] Tinify Configuration")
    print("-" * 70)
    
    try:
        # Default API key
        config = APNGCConfig()
        assert config.tinify_key == os.environ.get("TINIFY_API_KEY", "")
        print(f"✓ Default Tinify API key configured")
        
        # Custom API key
        config.tinify_key = "custom_key_123"
        assert config.tinify_key == "custom_key_123"
        print(f"✓ Custom Tinify API key set")
        
        # Optimize toggle
        assert config.optimize == True
        config.optimize = False
        assert config.optimize == False
        print(f"✓ Optimize toggle working")
        
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


def test_static_mode_processing():
    """Test static image resizing (no animation)"""
    print("\n[TEST 5] Static Mode Processing")
    print("-" * 70)
    
    if not TEST_IMAGE_DIR.exists():
        print(f"✗ Test image directory not found: {TEST_IMAGE_DIR}")
        return False
    
    sequences = list(TEST_IMAGE_DIR.glob("Folder_*"))
    if not sequences:
        print(f"✗ No test sequences found")
        return False
    
    test_seq = sequences[0]
    png_files = list(test_seq.glob("*.png"))
    print(f"Found test sequence: {test_seq.name} ({len(png_files)} frames)")
    
    try:
        OUTPUT_DIR.mkdir(exist_ok=True)
        
        # Create static mode config
        config = APNGCConfig(
            mode="static",
            width=450,
            height=880,
            preset_name="profile_effects",
            append_preset_to_filename=True,
            export_path=str(OUTPUT_DIR)
        )
        
        processor = APNGCProcessor(config, apngasm_exe=str(APNGASM_EXE))
        
        output_name = f"static_test.png"
        print(f"Processing in STATIC mode...")
        
        success, output_path = processor.process_static_sequence(
            str(test_seq),
            output_name
        )
        
        if success and output_path:
            output_size = Path(output_path).stat().st_size / (1024 * 1024)
            expected_name = "static_test_profile_effects.png"
            actual_name = Path(output_path).name
            
            print(f"✓ Static processing completed")
            print(f"  - Output: {output_path}")
            print(f"  - Filename: {actual_name}")
            print(f"  - Size: {output_size:.2f} MB (first frame only)")
            
            if actual_name == expected_name:
                print(f"✓ Preset name correctly appended to filename")
            
            return True
        else:
            print(f"✗ Static processing failed")
            return False
    
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_animated_with_preset():
    """Test animated processing with preset"""
    print("\n[TEST 6] Animated Mode with Preset")
    print("-" * 70)
    
    if not TEST_IMAGE_DIR.exists():
        print(f"✗ Test image directory not found")
        return False
    
    sequences = list(TEST_IMAGE_DIR.glob("Folder_*"))
    if len(sequences) < 1:
        print(f"✗ Not enough test sequences")
        return False
    
    test_seq = sequences[0]
    
    try:
        OUTPUT_DIR.mkdir(exist_ok=True)
        
        # Load avatar_decorations preset
        config = APNGCConfig.from_preset("avatar_decorations")
        config.optimize = False  # Skip Tinify for speed
        config.export_path = str(OUTPUT_DIR)
        
        processor = APNGCProcessor(config, apngasm_exe=str(APNGASM_EXE))
        
        output_name = f"preset_test.png"
        print(f"Processing with AVATAR_DECORATIONS preset...")
        print(f"  - Size: {config.width}x{config.height}")
        print(f"  - FPS: {config.framerate}")
        
        success, output_path = processor.process_sequence(
            str(test_seq),
            output_name
        )
        
        if success and output_path:
            output_size = Path(output_path).stat().st_size / (1024 * 1024)
            filename = Path(output_path).name
            
            print(f"✓ Preset-based processing completed")
            print(f"  - Output: {filename}")
            print(f"  - Size: {output_size:.2f} MB")
            
            # Verify filename has preset appended
            if "avatar_decorations" in filename:
                print(f"✓ Preset name correctly in filename")
            
            return True
        else:
            print(f"✗ Processing failed")
            return False
    
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_persistence_with_presets():
    """Test saving/loading config with presets"""
    print("\n[TEST 7] Config Persistence with Presets")
    print("-" * 70)
    
    try:
        config_file = OUTPUT_DIR / "preset_config.json"
        
        # Create and save config from preset
        config1 = APNGCConfig.from_preset("profile_effects")
        config1.optimize = True
        config1.tinify_key = "test_key_123"
        config1.to_json(str(config_file))
        print(f"✓ Config saved")
        
        # Load and verify
        config2 = APNGCConfig.from_json(str(config_file))
        
        assert config2.preset_name == "profile_effects"
        assert config2.width == 450
        assert config2.height == 880
        assert config2.optimize == True
        assert config2.tinify_key == "test_key_123"
        
        print(f"✓ Config loaded and verified")
        print(f"  - Preset: {config2.preset_name}")
        print(f"  - Size: {config2.width}x{config2.height}")
        print(f"  - Tinify key: {config2.tinify_key[:10]}...")
        
        return True
    
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_static_mode_with_tinify():
    """Test static mode with Tinify compression enabled"""
    print("\n[TEST 8] Static Mode with Tinify Compression")
    print("-" * 70)
    
    try:
        # Find test sequence
        sequences = list(TEST_IMAGE_DIR.glob("Folder_*"))
        if not sequences:
            print("✗ No test sequences found")
            return False
        
        test_sequence = sequences[0]
        print(f"Found test sequence: {test_sequence.name}")
        
        # Create config with static mode and Tinify optimization
        config = APNGCConfig(mode="static")
        config.width = 450
        config.height = 880
        config.optimize = True
        # Using the provided API key
        config.tinify_key = os.environ.get("TINIFY_API_KEY", "")
        config.export_path = str(OUTPUT_DIR)
        
        # Create processor and process
        processor = APNGCProcessor(config)
        success, output_path = processor.process_static_sequence(
            str(test_sequence),
            "static_with_tinify_test"
        )
        
        if success and output_path:
            output_size = Path(output_path).stat().st_size / (1024 * 1024)
            output_name = Path(output_path).name
            
            print(f"✓ Static processing with Tinify completed")
            print(f"  - Output: {output_name}")
            print(f"  - Size: {output_size:.2f} MB")
            print(f"  - Status: Compressed with Tinify API")
            
            return True
        else:
            print(f"✗ Processing failed")
            return False
    
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def run_all_tests():
    """Run complete test suite"""
    
    print("\n" + "=" * 70)
    print("APNGC Library Extended Features - Phase 1+ Test Suite")
    print("=" * 70)
    
    tests = [
        ("Preset System", test_preset_system),
        ("Mode Selection", test_mode_selection),
        ("Filename Generation", test_filename_generation),
        ("Tinify Configuration", test_tinify_configuration),
        ("Static Mode Processing", test_static_mode_processing),
        ("Animated with Preset", test_animated_with_preset),
        ("Config Persistence", test_config_persistence_with_presets),
        ("Static Mode with Tinify", test_static_mode_with_tinify),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"✗ Unexpected error in {test_name}: {e}")
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
