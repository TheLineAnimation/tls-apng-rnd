#!/usr/bin/env python3
"""
Tinify Compression Comparison Test Suite
Tests all folders with and without Tinify optimization for both static and animated modes
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from apngc_lib import APNGCConfig, APNGCProcessor, PRESETS
import shutil

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

# API key for Tinify — loaded from .env / environment variable
TINIFY_API_KEY = os.environ.get("TINIFY_API_KEY", "")


def get_file_size_mb(filepath):
    """Get file size in MB"""
    if Path(filepath).exists():
        return Path(filepath).stat().st_size / (1024 * 1024)
    return None


def test_static_mode_comparison():
    """Compare static mode outputs with and without Tinify across all folders"""
    print("\n" + "=" * 90)
    print("TEST 1: STATIC MODE - TINIFY COMPRESSION COMPARISON")
    print("=" * 90)
    
    results = []
    
    # Get all test folders
    test_folders = sorted([d for d in TEST_IMAGE_DIR.iterdir() if d.is_dir()])
    
    for folder_idx, test_folder in enumerate(test_folders, 1):
        print(f"\n[Folder {folder_idx}/{len(test_folders)}] {test_folder.name}")
        print("-" * 90)
        
        folder_name = test_folder.name
        
        # Test 1: Without Tinify
        print(f"\n  Testing WITHOUT Tinify...")
        config_no_tinify = APNGCConfig(mode="static")
        config_no_tinify.width = 450
        config_no_tinify.height = 880
        config_no_tinify.optimize = False  # Disable Tinify
        config_no_tinify.export_path = str(OUTPUT_DIR)
        
        processor = APNGCProcessor(config_no_tinify)
        start_time = datetime.now()
        success1, output1 = processor.process_static_sequence(
            str(test_folder),
            f"static_notin_{folder_name}"
        )
        time1 = (datetime.now() - start_time).total_seconds()
        
        if success1:
            size1 = get_file_size_mb(output1)
            name1 = Path(output1).name
            print(f"    ✓ Output: {name1} ({size1:.2f} MB) - {time1:.1f}s")
        else:
            print(f"    ✗ Failed")
            continue
        
        # Test 2: With Tinify
        print(f"\n  Testing WITH Tinify...")
        config_with_tinify = APNGCConfig(mode="static")
        config_with_tinify.width = 450
        config_with_tinify.height = 880
        config_with_tinify.optimize = True  # Enable Tinify
        config_with_tinify.tinify_key = TINIFY_API_KEY
        config_with_tinify.export_path = str(OUTPUT_DIR)
        
        processor = APNGCProcessor(config_with_tinify)
        start_time = datetime.now()
        success2, output2 = processor.process_static_sequence(
            str(test_folder),
            f"static_tinify_{folder_name}"
        )
        time2 = (datetime.now() - start_time).total_seconds()
        
        if success2:
            size2 = get_file_size_mb(output2)
            name2 = Path(output2).name
            reduction = ((size1 - size2) / size1) * 100 if size1 > 0 else 0
            print(f"    ✓ Output: {name2} ({size2:.2f} MB) - {time2:.1f}s")
        else:
            print(f"    ✗ Failed")
            continue
        
        # Store comparison
        result = {
            "folder": folder_name,
            "mode": "static",
            "no_tinify_size": size1,
            "no_tinify_time": time1,
            "with_tinify_size": size2,
            "with_tinify_time": time2,
            "size_reduction_mb": size1 - size2,
            "size_reduction_pct": reduction,
        }
        results.append(result)
        
        print(f"\n  COMPARISON:")
        print(f"    Without Tinify: {size1:.2f} MB")
        print(f"    With Tinify:    {size2:.2f} MB")
        print(f"    Reduction:      {size2:.2f} MB ({reduction:.1f}%)")
        print(f"    Time Impact:    {time1:.1f}s → {time2:.1f}s (+{time2-time1:.1f}s)")
    
    return results


def test_animated_mode_comparison():
    """Compare animated mode outputs with and without Tinify across all folders"""
    print("\n" + "=" * 90)
    print("TEST 2: ANIMATED MODE - TINIFY COMPRESSION COMPARISON")
    print("=" * 90)
    
    results = []
    
    # Get all test folders
    test_folders = sorted([d for d in TEST_IMAGE_DIR.iterdir() if d.is_dir()])
    
    for folder_idx, test_folder in enumerate(test_folders, 1):
        print(f"\n[Folder {folder_idx}/{len(test_folders)}] {test_folder.name}")
        print("-" * 90)
        
        folder_name = test_folder.name
        
        # Test 1: Without Tinify
        print(f"\n  Testing WITHOUT Tinify...")
        config_no_tinify = APNGCConfig(mode="animated")
        config_no_tinify.width = 450
        config_no_tinify.height = 880
        config_no_tinify.framerate = 12
        config_no_tinify.optimize = False  # Disable Tinify
        config_no_tinify.export_path = str(OUTPUT_DIR)
        
        processor = APNGCProcessor(config_no_tinify)
        start_time = datetime.now()
        success1, output1 = processor.process_sequence(
            str(test_folder),
            f"anim_notin_{folder_name}"
        )
        time1 = (datetime.now() - start_time).total_seconds()
        
        if success1:
            size1 = get_file_size_mb(output1)
            name1 = Path(output1).name
            print(f"    ✓ Output: {name1} ({size1:.2f} MB) - {time1:.1f}s")
        else:
            print(f"    ✗ Failed")
            continue
        
        # Test 2: With Tinify
        print(f"\n  Testing WITH Tinify...")
        config_with_tinify = APNGCConfig(mode="animated")
        config_with_tinify.width = 450
        config_with_tinify.height = 880
        config_with_tinify.framerate = 12
        config_with_tinify.optimize = True  # Enable Tinify
        config_with_tinify.tinify_key = TINIFY_API_KEY
        config_with_tinify.export_path = str(OUTPUT_DIR)
        
        processor = APNGCProcessor(config_with_tinify)
        start_time = datetime.now()
        success2, output2 = processor.process_sequence(
            str(test_folder),
            f"anim_tinify_{folder_name}"
        )
        time2 = (datetime.now() - start_time).total_seconds()
        
        if success2:
            size2 = get_file_size_mb(output2)
            name2 = Path(output2).name
            reduction = ((size1 - size2) / size1) * 100 if size1 > 0 else 0
            print(f"    ✓ Output: {name2} ({size2:.2f} MB) - {time2:.1f}s")
        else:
            print(f"    ✗ Failed")
            continue
        
        # Store comparison
        result = {
            "folder": folder_name,
            "mode": "animated",
            "no_tinify_size": size1,
            "no_tinify_time": time1,
            "with_tinify_size": size2,
            "with_tinify_time": time2,
            "size_reduction_mb": size1 - size2,
            "size_reduction_pct": reduction,
        }
        results.append(result)
        
        print(f"\n  COMPARISON:")
        print(f"    Without Tinify: {size1:.2f} MB")
        print(f"    With Tinify:    {size2:.2f} MB")
        print(f"    Reduction:      {size2:.2f} MB ({reduction:.1f}%)")
        print(f"    Time Impact:    {time1:.1f}s → {time2:.1f}s (+{time2-time1:.1f}s)")
    
    return results


def print_summary_table(static_results, animated_results):
    """Print comprehensive summary tables"""
    
    print("\n" + "=" * 90)
    print("SUMMARY: STATIC MODE - TINIFY COMPRESSION IMPACT")
    print("=" * 90)
    print(f"\n{'Folder':<15} {'Without Tinify':<20} {'With Tinify':<20} {'Reduction':<20} {'Time Impact':<20}")
    print("-" * 90)
    
    total_saved_static = 0
    for result in static_results:
        size_reduction = f"{result['size_reduction_mb']:.2f} MB ({result['size_reduction_pct']:.1f}%)"
        time_impact = f"+{result['with_tinify_time'] - result['no_tinify_time']:.1f}s"
        print(f"{result['folder']:<15} {result['no_tinify_size']:.2f} MB             {result['with_tinify_size']:.2f} MB             {size_reduction:<20} {time_impact:<20}")
        total_saved_static += result['size_reduction_mb']
    
    avg_reduction_static = sum(r['size_reduction_pct'] for r in static_results) / len(static_results) if static_results else 0
    print("-" * 90)
    print(f"{'TOTAL SAVED:':<15} {total_saved_static:.2f} MB across {len(static_results)} files | Average reduction: {avg_reduction_static:.1f}%")
    
    print("\n" + "=" * 90)
    print("SUMMARY: ANIMATED MODE - TINIFY COMPRESSION IMPACT")
    print("=" * 90)
    print(f"\n{'Folder':<15} {'Without Tinify':<20} {'With Tinify':<20} {'Reduction':<20} {'Time Impact':<20}")
    print("-" * 90)
    
    total_saved_animated = 0
    for result in animated_results:
        size_reduction = f"{result['size_reduction_mb']:.2f} MB ({result['size_reduction_pct']:.1f}%)"
        time_impact = f"+{result['with_tinify_time'] - result['no_tinify_time']:.1f}s"
        print(f"{result['folder']:<15} {result['no_tinify_size']:.2f} MB             {result['with_tinify_size']:.2f} MB             {size_reduction:<20} {time_impact:<20}")
        total_saved_animated += result['size_reduction_mb']
    
    avg_reduction_animated = sum(r['size_reduction_pct'] for r in animated_results) / len(animated_results) if animated_results else 0
    print("-" * 90)
    print(f"{'TOTAL SAVED:':<15} {total_saved_animated:.2f} MB across {len(animated_results)} files | Average reduction: {avg_reduction_animated:.1f}%")
    
    print("\n" + "=" * 90)
    print("OVERALL STATISTICS")
    print("=" * 90)
    total_files = len(static_results) + len(animated_results)
    total_saved = total_saved_static + total_saved_animated
    avg_reduction_overall = (sum(r['size_reduction_pct'] for r in static_results) + sum(r['size_reduction_pct'] for r in animated_results)) / total_files if total_files > 0 else 0
    
    print(f"\nTotal files processed: {total_files}")
    print(f"Total data saved: {total_saved:.2f} MB")
    print(f"Average compression: {avg_reduction_overall:.1f}%")
    print(f"\nStatic mode: {total_saved_static:.2f} MB saved ({avg_reduction_static:.1f}% avg)")
    print(f"Animated mode: {total_saved_animated:.2f} MB saved ({avg_reduction_animated:.1f}% avg)")


def run_all_tests():
    """Run complete comparison test suite"""
    
    print("\n" + "=" * 90)
    print("APNGC TINIFY COMPRESSION COMPARISON TEST SUITE")
    print("Testing all folders with and without Tinify optimization")
    print("=" * 90)
    
    try:
        # Run tests
        static_results = test_static_mode_comparison()
        animated_results = test_animated_mode_comparison()
        
        # Print summary
        print_summary_table(static_results, animated_results)
        
        return True
    
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
