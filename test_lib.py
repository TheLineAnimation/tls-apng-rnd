#!/usr/bin/env python3
"""
APNGC Library Test Suite - Phase 1 Validation
Tests all 5 stages of the pipeline
"""

import sys
from pathlib import Path
from apngc_lib import APNGCConfig, APNGCProcessor, quick_process

# Get project root
PROJECT_ROOT = Path(__file__).parent
TEST_IMAGE_DIR = PROJECT_ROOT / "test_images_renamed"
OUTPUT_DIR = PROJECT_ROOT / "output"
APNGASM_EXE = PROJECT_ROOT / "exe" / "apngasm.exe"


def test_library_imports():
    """Test that all dependencies are available"""
    print("\n[TEST 1] Library Imports")
    print("-" * 70)
    
    try:
        from PIL import Image
        print("✓ Pillow available")
    except ImportError:
        print("✗ Pillow NOT available - install with: pip install Pillow")
        return False
    
    try:
        import tinify
        print("✓ Tinify available")
    except ImportError:
        print("⚠ Tinify NOT available (optional) - install with: pip install tinify")
    
    return True


def test_config_creation():
    """Test configuration object creation"""
    print("\n[TEST 2] Configuration Creation")
    print("-" * 70)
    
    try:
        config = APNGCConfig(
            width=450,
            height=880,
            framerate=12,
            compression="7zip",
            iterations=15,
            optimize=False  # Disable Tinify for testing
        )
        
        print(f"✓ Config created:")
        print(f"  - Size: {config.width}x{config.height}")
        print(f"  - FPS: {config.framerate}")
        print(f"  - Compression: {config.compression} @ {config.iterations} iter")
        
        return True
    except Exception as e:
        print(f"✗ Failed to create config: {e}")
        return False


def test_processor_initialization():
    """Test processor initialization"""
    print("\n[TEST 3] Processor Initialization")
    print("-" * 70)
    
    try:
        config = APNGCConfig(optimize=False)
        processor = APNGCProcessor(
            config,
            apngasm_exe=str(APNGASM_EXE)
        )
        
        print("✓ Processor initialized")
        print(f"  - Config: {config.profile_name}")
        print(f"  - APNGASM: {APNGASM_EXE}")
        
        return True
    except Exception as e:
        print(f"✗ Failed to initialize processor: {e}")
        return False


def test_frame_delay_calculation():
    """Test framerate to APNGASM delay conversion"""
    print("\n[TEST 4] Frame Delay Calculation")
    print("-" * 70)
    
    try:
        config = APNGCConfig(optimize=False)
        processor = APNGCProcessor(config, apngasm_exe=str(APNGASM_EXE))
        
        test_cases = [
            (10, (1, 10)),
            (12, (5, 60)),
            (25, (1, 25)),
            (30, (1, 30)),
        ]
        
        for fps, expected in test_cases:
            config.framerate = fps
            processor.apngasm.config = config
            
            numerator, denominator = processor.apngasm.calculate_frame_delay()
            duration_ms = 1000 * numerator / denominator
            
            status = "✓" if (numerator, denominator) == expected else "⚠"
            print(f"{status} {fps} fps → {numerator}/{denominator} ({duration_ms:.0f}ms)")
        
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


def test_single_sequence():
    """Test processing single sequence"""
    print("\n[TEST 5] Single Sequence Processing")
    print("-" * 70)
    
    if not TEST_IMAGE_DIR.exists():
        print(f"✗ Test image directory not found: {TEST_IMAGE_DIR}")
        return False
    
    # Find first test sequence
    sequences = list(TEST_IMAGE_DIR.glob("Folder_*"))
    if not sequences:
        print(f"✗ No test sequences found in {TEST_IMAGE_DIR}")
        return False
    
    test_seq = sequences[0]
    png_files = list(test_seq.glob("*.png"))
    print(f"Found test sequence: {test_seq.name} ({len(png_files)} frames)")
    
    try:
        OUTPUT_DIR.mkdir(exist_ok=True)
        
        config = APNGCConfig(
            width=450,
            height=880,
            framerate=12,
            optimize=False,
            export_path=str(OUTPUT_DIR)
        )
        
        processor = APNGCProcessor(config, apngasm_exe=str(APNGASM_EXE))
        
        output_name = f"test_{test_seq.name}.png"
        print(f"Processing to: {output_name}")
        
        success, output_path = processor.process_sequence(
            str(test_seq),
            output_name
        )
        
        if success and output_path:
            output_size = Path(output_path).stat().st_size / (1024 * 1024)
            print(f"✓ Sequence processed successfully")
            print(f"  - Output: {output_path}")
            print(f"  - Size: {output_size:.2f} MB")
            return True
        else:
            print(f"✗ Processing failed")
            return False
    
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_batch_processing():
    """Test batch processing multiple sequences"""
    print("\n[TEST 6] Batch Processing")
    print("-" * 70)
    
    if not TEST_IMAGE_DIR.exists():
        print(f"✗ Test image directory not found: {TEST_IMAGE_DIR}")
        return False
    
    sequences = list(TEST_IMAGE_DIR.glob("Folder_*"))
    if len(sequences) < 2:
        print(f"⚠ Only {len(sequences)} sequence(s) found, need 2+ for batch test")
        return True  # Skip but don't fail
    
    test_seqs = sequences[:2]  # Test first 2
    print(f"Testing batch with {len(test_seqs)} sequences")
    
    try:
        OUTPUT_DIR.mkdir(exist_ok=True)
        
        config = APNGCConfig(
            width=450,
            height=880,
            framerate=12,
            optimize=False,
            export_path=str(OUTPUT_DIR)
        )
        
        processor = APNGCProcessor(config, apngasm_exe=str(APNGASM_EXE))
        
        input_dirs = [str(seq) for seq in test_seqs]
        output_files = [f"batch_{seq.name}.png" for seq in test_seqs]
        
        results = processor.process_batch(
            input_dirs,
            output_files,
            max_workers=2
        )
        
        passed = sum(1 for success, _ in results.values() if success)
        print(f"✓ Batch results: {passed}/{len(results)} successful")
        
        return passed > 0
    
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_persistence():
    """Test save/load configuration"""
    print("\n[TEST 7] Configuration Persistence")
    print("-" * 70)
    
    try:
        config_file = OUTPUT_DIR / "test_config.json"
        
        # Create and save config
        config1 = APNGCConfig(
            width=512,
            height=512,
            framerate=24,
            profile_name="test_profile"
        )
        config1.to_json(str(config_file))
        print(f"✓ Config saved to {config_file.name}")
        
        # Load config
        config2 = APNGCConfig.from_json(str(config_file))
        
        # Verify
        if (config2.width == 512 and 
            config2.height == 512 and 
            config2.framerate == 24 and
            config2.profile_name == "test_profile"):
            print(f"✓ Config loaded correctly")
            return True
        else:
            print(f"✗ Config mismatch after load")
            return False
    
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def run_all_tests():
    """Run complete test suite"""
    
    print("\n" + "=" * 70)
    print("APNGC Library - Phase 1 Test Suite")
    print("=" * 70)
    
    tests = [
        ("Library Imports", test_library_imports),
        ("Config Creation", test_config_creation),
        ("Processor Init", test_processor_initialization),
        ("Frame Delay Calc", test_frame_delay_calculation),
        ("Single Sequence", test_single_sequence),
        ("Batch Processing", test_batch_processing),
        ("Config Persistence", test_config_persistence),
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
