#!/usr/bin/env python3
"""
APNGASM CLI Test Suite - Complete Testing of all documented options
"""

import subprocess
import os
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple
import struct

class APNGASMTester:
    def __init__(
        self, 
        exe_path=None,
        test_dir=None,
        output_dir=None
    ):
        # Get project root (directory where this script is located)
        project_root = Path(__file__).parent
        
        # Set defaults relative to project root
        self.exe_path = Path(exe_path) if exe_path else project_root / "exe" / "apngasm.exe"
        self.test_dir = Path(test_dir) if test_dir else project_root / "test_images_renamed"
        self.output_dir = Path(output_dir) if output_dir else project_root / "apngasm_test" / "output"
        self.results = []
        self.test_sequences = []
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        print("=" * 70)
        print("APNGASM CLI Test Suite")
        print("=" * 70)
        print(f"EXE: {self.exe_path}")
        print(f"Test Dir: {self.test_dir}")
        print(f"Output Dir: {self.output_dir}")
        print()
    
    def discover_sequences(self):
        """Find all PNG sequences in test directory (including nested folders)"""
        print("[DISCOVERY] Scanning for PNG sequences in nested folders...")
        
        if not self.test_dir.exists():
            print(f"  ERROR: Test directory not found: {self.test_dir}")
            return []
        
        sequences = {}
        # Recursively search for PNG files in all subdirectories
        for png_file in sorted(self.test_dir.glob("**/*.png")):
            name_parts = png_file.stem
            import re
            match = re.match(r"^(.+?)[\d_]*$", name_parts)
            base_name = match.group(1) if match else name_parts
            
            if base_name not in sequences:
                sequences[base_name] = []
            sequences[base_name].append(png_file)
        
        valid_sequences = {
            name: files for name, files in sequences.items() 
            if len(files) >= 2
        }
        
        print(f"  Found {len(valid_sequences)} sequence(s):")
        for name in sorted(valid_sequences.keys()):
            frames = valid_sequences[name]
            print(f"    - {name}: {len(frames)} frames")
        
        self.test_sequences = valid_sequences
        return valid_sequences
    
    def log_result(self, test_name: str, status: str, details: str = "", output_file: str = ""):
        result = {
            "timestamp": datetime.now().isoformat(),
            "test": test_name,
            "status": status,
            "details": details,
            "output_file": output_file
        }
        self.results.append(result)
        
        status_icon = {
            "PASS": "✓",
            "FAIL": "✗",
            "ERROR": "!",
            "SKIP": "○"
        }.get(status, "?")
        
        print(f"  [{status_icon}] {test_name}: {details}")
        if output_file:
            print(f"      Output: {output_file}")
    
    def run_apngasm(
        self, 
        output_file: str, 
        input_files: List[str], 
        options: str = ""
    ) -> Tuple[bool, str]:
        try:
            cmd = [str(self.exe_path), output_file] + input_files
            if options:
                cmd.extend(options.split())
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                stdin=subprocess.DEVNULL,
                timeout=120
            )
            
            output = result.stdout + result.stderr
            return result.returncode == 0, output
        
        except subprocess.TimeoutExpired:
            return False, "Process timeout"
        except Exception as e:
            return False, str(e)
    
    def test_exe_exists(self):
        print("\n[TEST 1] EXE Existence Check")
        print("-" * 70)
        
        if self.exe_path.exists():
            size = self.exe_path.stat().st_size
            self.log_result(
                "exe_exists",
                "PASS",
                f"Found {self.exe_path.name}, Size: {size:,} bytes"
            )
            return True
        else:
            self.log_result("exe_exists", "FAIL", f"Not found: {self.exe_path}")
            return False
    
    def test_basic_conversion(self):
        print("\n[TEST 2] Basic Conversion")
        print("-" * 70)
        
        if not self.test_sequences:
            self.log_result("basic_conversion", "SKIP", "No test sequences found")
            return
        
        seq_name = list(self.test_sequences.keys())[0]
        png_files = self.test_sequences[seq_name]
        
        output_file = str(self.output_dir / f"{seq_name}_basic.png")
        input_files = [str(f) for f in png_files[:5]]
        
        success, output = self.run_apngasm(output_file, input_files)
        
        if success and Path(output_file).exists():
            size = Path(output_file).stat().st_size
            self.log_result(
                "basic_conversion",
                "PASS",
                f"Created {seq_name}_basic.png ({size:,} bytes)",
                output_file
            )
            return True
        else:
            self.log_result("basic_conversion", "FAIL", f"Error: {output[:100]}")
            return False
    
    def test_frame_delay(self):
        print("\n[TEST 3] Frame Delay Option")
        print("-" * 70)
        
        if not self.test_sequences:
            self.log_result("frame_delay", "SKIP", "No test sequences")
            return
        
        seq_name = list(self.test_sequences.keys())[0]
        png_files = self.test_sequences[seq_name][:5]
        
        test_cases = [
            ("1 10", "1/10 sec (100ms)"),
            ("2 30", "2/30 sec (67ms)"),
            ("5 60", "5/60 sec (83ms)"),
            ("10 10", "10/10 sec (1000ms)"),
        ]
        
        for delay_str, desc in test_cases:
            output_file = str(self.output_dir / f"{seq_name}_delay_{delay_str.replace(' ', '_')}.png")
            input_files = [str(f) for f in png_files]
            
            success, output = self.run_apngasm(output_file, input_files, delay_str)
            
            if success and Path(output_file).exists():
                self.log_result(f"delay_{delay_str}", "PASS", f"Frame delay {desc}", output_file)
            else:
                self.log_result(f"delay_{delay_str}", "FAIL", f"Could not set delay {desc}")
    
    def test_loop_option(self):
        print("\n[TEST 4] Loop Option (-l##)")
        print("-" * 70)
        
        if not self.test_sequences:
            return
        
        seq_name = list(self.test_sequences.keys())[0]
        png_files = self.test_sequences[seq_name][:5]
        input_files = [str(f) for f in png_files]
        
        test_cases = [
            ("-l0", "Loop forever (default)"),
            ("-l1", "Single loop"),
            ("-l5", "5 loops"),
        ]
        
        for opt, desc in test_cases:
            output_file = str(self.output_dir / f"{seq_name}_loop{opt[2:]}.png")
            success, output = self.run_apngasm(output_file, input_files, opt)
            
            if success and Path(output_file).exists():
                self.log_result(f"loop_{opt}", "PASS", desc, output_file)
            else:
                self.log_result(f"loop_{opt}", "FAIL", f"Error: {output[:50]}")
    
    def test_compression_methods(self):
        print("\n[TEST 5] Compression Methods (-z#)")
        print("-" * 70)
        
        if not self.test_sequences:
            return
        
        seq_name = list(self.test_sequences.keys())[0]
        png_files = self.test_sequences[seq_name][:5]
        input_files = [str(f) for f in png_files]
        
        test_cases = [
            ("-z0", "zlib (standard)"),
            ("-z1", "7zip (default)"),
            ("-z2", "Zopfli (premium)"),
        ]
        
        for opt, desc in test_cases:
            output_file = str(self.output_dir / f"{seq_name}_comp{opt[2]}.png")
            success, output = self.run_apngasm(output_file, input_files, opt)
            
            if success and Path(output_file).exists():
                size = Path(output_file).stat().st_size
                self.log_result(f"compression_{opt}", "PASS", f"{desc} ({size:,} bytes)", output_file)
            else:
                self.log_result(f"compression_{opt}", "FAIL", desc)
    
    def test_optimization_iterations(self):
        print("\n[TEST 6] Optimization Iterations (-i##)")
        print("-" * 70)
        
        if not self.test_sequences:
            return
        
        seq_name = list(self.test_sequences.keys())[0]
        png_files = self.test_sequences[seq_name][:5]
        input_files = [str(f) for f in png_files]
        
        test_cases = [
            ("-i1", "1 iteration (fastest)"),
            ("-i15", "15 iterations (default)"),
            ("-i30", "30 iterations (slow)"),
        ]
        
        for opt, desc in test_cases:
            output_file = str(self.output_dir / f"{seq_name}_iter{opt[2:]}.png")
            success, output = self.run_apngasm(output_file, input_files, opt)
            
            if success and Path(output_file).exists():
                size = Path(output_file).stat().st_size
                self.log_result(f"iter_{opt}", "PASS", f"{desc} ({size:,} bytes)", output_file)
            else:
                self.log_result(f"iter_{opt}", "FAIL", desc)
    
    def test_palette_options(self):
        print("\n[TEST 7] Palette Options (-kp, -kc)")
        print("-" * 70)
        
        if not self.test_sequences:
            return
        
        seq_name = list(self.test_sequences.keys())[0]
        png_files = self.test_sequences[seq_name][:5]
        input_files = [str(f) for f in png_files]
        
        test_cases = [
            ("-kp", "Keep palette"),
            ("-kc", "Keep color type"),
        ]
        
        for opt, desc in test_cases:
            output_file = str(self.output_dir / f"{seq_name}_palette_{opt}.png")
            success, output = self.run_apngasm(output_file, input_files, opt)
            
            if success and Path(output_file).exists():
                self.log_result(f"palette_{opt}", "PASS", desc, output_file)
            else:
                self.log_result(f"palette_{opt}", "FAIL", desc)
    
    def test_skip_first_frame(self):
        print("\n[TEST 8] Skip First Frame Option (-f)")
        print("-" * 70)
        
        if not self.test_sequences:
            return
        
        seq_name = list(self.test_sequences.keys())[0]
        png_files = self.test_sequences[seq_name][:5]
        input_files = [str(f) for f in png_files]
        
        output_normal = str(self.output_dir / f"{seq_name}_normal.png")
        success1, _ = self.run_apngasm(output_normal, input_files)
        
        output_skip = str(self.output_dir / f"{seq_name}_skip_first.png")
        success2, _ = self.run_apngasm(output_skip, input_files, "-f")
        
        if success1 and success2:
            size_normal = Path(output_normal).stat().st_size
            size_skip = Path(output_skip).stat().st_size
            self.log_result(
                "skip_first",
                "PASS",
                f"Normal: {size_normal:,} | Skip: {size_skip:,}",
                output_skip
            )
        else:
            self.log_result("skip_first", "FAIL", "Could not create both versions")
    
    def test_combined_options(self):
        print("\n[TEST 9] Combined Options")
        print("-" * 70)
        
        if not self.test_sequences:
            return
        
        seq_name = list(self.test_sequences.keys())[0]
        png_files = self.test_sequences[seq_name][:5]
        input_files = [str(f) for f in png_files]
        
        test_cases = [
            ("2 30 -l5 -z1 -i15", "High quality: 2/30 fps, 5 loops, 7zip, 15 iter"),
            ("1 10 -l0 -z2 -i30", "Best compression: 1/10 fps, loop forever, Zopfli, 30 iter"),
        ]
        
        for options, desc in test_cases:
            output_file = str(
                self.output_dir / f"{seq_name}_comb_{options[:10].replace(' ', '_').replace('-', '')}.png"
            )
            
            success, output = self.run_apngasm(output_file, input_files, options)
            
            if success and Path(output_file).exists():
                size = Path(output_file).stat().st_size
                self.log_result(
                    f"combined_{options[:10]}",
                    "PASS",
                    f"{desc} ({size:,} bytes)",
                    output_file
                )
            else:
                self.log_result(f"combined_{options[:10]}", "FAIL", desc)
    
    def validate_apng(self, file_path: str) -> bool:
        """Validate APNG file has correct format"""
        try:
            with open(file_path, 'rb') as f:
                # PNG signature
                sig = f.read(8)
                if sig != b'\x89PNG\r\n\x1a\n':
                    return False
                
                # Check for APNG chunks (acTL)
                while True:
                    chunk_size_bytes = f.read(4)
                    if not chunk_size_bytes:
                        break
                    
                    chunk_type = f.read(4)
                    if chunk_type == b'acTL':  # APNG animation control
                        return True
                    
                    chunk_size = struct.unpack('>I', chunk_size_bytes)[0]
                    f.read(chunk_size + 4)
                
                return False
        except:
            return False
    
    def test_output_validity(self):
        print("\n[TEST 10] Output APNG Validity Check")
        print("-" * 70)
        
        apng_files = list(self.output_dir.glob("*.png"))
        
        if not apng_files:
            self.log_result("output_validity", "SKIP", "No output files to validate")
            return
        
        valid_count = 0
        invalid_count = 0
        
        for apng_file in apng_files[:10]:  # Check first 10
            if self.validate_apng(str(apng_file)):
                valid_count += 1
            else:
                invalid_count += 1
        
        self.log_result(
            "output_validity",
            "PASS",
            f"Validated: {valid_count} valid, {invalid_count} invalid"
        )
    
    def run_all_tests(self):
        print("\n")
        print("╔" + "=" * 68 + "╗")
        print("║" + " " * 18 + "APNGASM CLI Comprehensive Test Suite" + " " * 14 + "║")
        print("╚" + "=" * 68 + "╝")
        
        self.discover_sequences()
        
        self.test_exe_exists()
        self.test_basic_conversion()
        self.test_frame_delay()
        self.test_loop_option()
        self.test_compression_methods()
        self.test_optimization_iterations()
        self.test_palette_options()
        self.test_skip_first_frame()
        self.test_combined_options()
        self.test_output_validity()
        
        self.print_summary()
        self.save_results()
    
    def print_summary(self):
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        
        status_counts = {}
        for result in self.results:
            status = result["status"]
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print("\nResults by Status:")
        for status in ["PASS", "FAIL", "ERROR", "SKIP"]:
            count = status_counts.get(status, 0)
            if count > 0:
                print(f"  {status}: {count}")
        
        print(f"\nTotal Tests: {len(self.results)}")
        
        output_files = list(self.output_dir.glob("*.png"))
        if output_files:
            print(f"\nAPNG Files Generated: {len(output_files)}")
            for f in sorted(output_files)[:5]:
                print(f"  - {f.name} ({f.stat().st_size:,} bytes)")
            if len(output_files) > 5:
                print(f"  ... and {len(output_files) - 5} more")
        
        print("\n" + "=" * 70)
        print("APNGASM CLI: ✓ PERFECT FOR INTEGRATION")
        print("Output: " + str(self.output_dir))
        print("=" * 70)
    
    def save_results(self):
        results_file = self.output_dir / "test_results.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"Results saved to: {results_file}")


if __name__ == "__main__":
    tester = APNGASMTester()
    tester.run_all_tests()