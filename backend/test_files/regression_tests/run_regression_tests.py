"""Run portable or full notice-processing regression tests."""

import argparse
import os
import sys
import unittest

from pathlib import Path


TEST_DIR = Path(__file__).resolve().parent
BACKEND = TEST_DIR.parents[1]

sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(TEST_DIR))

os.chdir(BACKEND)

from generate_pdf_fixtures import generate_scanned_fixture


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--full",
        action="store_true",
        help="Include tests requiring local newspaper reports",
    )

    args = parser.parse_args()

    generate_scanned_fixture()

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    included = []
    excluded = []

    for path in sorted(TEST_DIR.glob("test_*.py")):

        source = path.read_text(encoding="utf-8")

        if not args.full and "results.json" in source:

            excluded.append(path.name)
            continue

        suite.addTests(
            loader.loadTestsFromName(path.stem)
        )

        included.append(path.name)

    print("Mode:", "FULL" if args.full else "PORTABLE")
    print("Included modules:", len(included))
    print("Excluded modules:", len(excluded))
    print("Selected tests:", suite.countTestCases())

    for name in excluded:
        print("Local fixture module excluded:", name)

    result = unittest.TextTestRunner(
        verbosity=1
    ).run(suite)

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
