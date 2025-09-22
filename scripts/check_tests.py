#!/usr/bin/env python3
"""
Test verification and execution script for HomeTube.
This script verifies that all tests work correctly after refactoring.
"""

import sys
import subprocess
import os
from pathlib import Path


def run_command(cmd, description=""):
    """Executes a command and returns the result."""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"Command: {cmd}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=300
        )

        print("STDOUT:")
        print(result.stdout)

        if result.stderr:
            print("STDERR:")
            print(result.stderr)

        if result.returncode == 0:
            print(f"✅ {description} - SUCCESS")
            return True
        else:
            print(f"❌ {description} - FAILED (code: {result.returncode})")
            return False

    except subprocess.TimeoutExpired:
        print(f"⏰ {description} - TIMEOUT")
        return False
    except Exception as e:
        print(f"💥 {description} - ERROR: {e}")
        return False


def check_test_files():
    """Checks that all test files exist."""
    test_dir = Path("tests")
    expected_files = [
        "conftest.py",
        "test_core_functions.py",
        "test_translations.py",
        "test_utils.py",
    ]

    print("\n📁 Checking test files...")
    missing_files = []

    for file_name in expected_files:
        file_path = test_dir / file_name
        if file_path.exists():
            print(f"✅ {file_name}")
        else:
            print(f"❌ {file_name} - MISSING")
            missing_files.append(file_name)

    if missing_files:
        print(f"\n💥 Missing files: {missing_files}")
        return False

    print("\n✅ All test files are present")
    return True


def main():
    """Main function."""
    print("🧪 HomeTube - Refactored test suite verification")
    print("=" * 80)

    # Check that we are in the right directory
    if not Path("app/main.py").exists():
        print("❌ Error: Please run this script from the HomeTube project root")
        sys.exit(1)

    # Check test files
    if not check_test_files():
        sys.exit(1)

    # List of tests to execute
    test_commands = [
        # Basic tests to check configuration
        ("python -m pytest --version", "Pytest verification"),
        ("python -m pytest --collect-only tests/", "Test collection"),
        # Tests by category
        (
            "python -m pytest tests/test_core_functions.py -v",
            "Core function tests",
        ),
        ("python -m pytest tests/test_utils.py -v", "Utility tests"),
        ("python -m pytest tests/test_translations.py -v", "Translation tests"),
        # Fast global test
        (
            "python -m pytest tests/ -v -m 'not slow and not external'",
            "Complete tests (without slow tests)",
        ),
    ]

    results = []

    for cmd, description in test_commands:
        success = run_command(cmd, description)
        results.append((description, success))

    # Final summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)

    success_count = 0
    total_count = len(results)

    for description, success in results:
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"{status:<12} {description}")
        if success:
            success_count += 1

    print(f"\n📈 Score: {success_count}/{total_count} tests passed")

    if success_count == total_count:
        print("\n🎉 ALL TESTS PASSED SUCCESSFULLY!")
        print("Test refactoring is complete and functional.")
        return_code = 0
    else:
        print(f"\n⚠️  {total_count - success_count} test(s) failed.")
        print("Please examine the errors above.")
        return_code = 1

    # Instructions for future use
    print("\n" + "=" * 80)
    print("📖 NEW TESTS USAGE")
    print("=" * 80)
    print("• Fast tests:              make test-fast")
    print("• Unit tests:              make test-unit")
    print("• Integration tests:       make test-integration")
    print("• Performance tests:       make test-performance")
    print("• Tests with coverage:     make test-coverage")
    print("• All tests:               make test")
    print("• Help:                    make help")

    sys.exit(return_code)


if __name__ == "__main__":
    main()
