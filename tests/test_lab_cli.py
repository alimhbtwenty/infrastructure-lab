#!/usr/bin/env python3
"""
tests/test_lab_cli.py - Unit tests for tools/lab_cli.py
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

# Add tools directory to path
import sys
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "tools"))

import lab_cli


class TestLabCli(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.root = Path(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_validate_valid_file(self):
        valid_content = """# INC-001 : Test Scenario
**DATE** 2026-10-11
**Environment:** Ubuntu 24.04 LTS
## What i did
Executed diagnostic steps.
## Output
```bash
echo hello
```
## What i learned :
Learned key root cause and prevention.
"""
        test_file = self.root / "INC-001.md"
        test_file.write_text(valid_content, encoding="utf-8")

        errs = lab_cli.validate_file(test_file)
        self.assertEqual(errs, [], f"Expected 0 errors, got: {errs}")

    def test_validate_mismatched_number(self):
        content = """# INC-002 : Mismatched Number
**DATE** 2026-10-11
**Environment:** TestEnv
## What i did
Foo
## Output
Bar
## What i learned :
Baz
"""
        test_file = self.root / "INC-001.md"
        test_file.write_text(content, encoding="utf-8")

        errs = lab_cli.validate_file(test_file)
        self.assertTrue(any("does not match filename" in msg for _, msg in errs))

    def test_validate_missing_section(self):
        content = """# INC-001 : Missing Section
**DATE** 2026-10-11
**Environment:** TestEnv
## What i did
Foo
## What i learned :
Baz
"""
        test_file = self.root / "INC-001.md"
        test_file.write_text(content, encoding="utf-8")

        errs = lab_cli.validate_file(test_file)
        self.assertTrue(any("Missing section '## Output'" in msg for _, msg in errs))

    def test_new_and_auto_increment(self):
        # Initial: no files, next should be 0
        self.assertEqual(lab_cli.get_next_inc_num(self.root), 0)

        # Create INC-000
        class DummyArgs:
            root = str(self.root)
            title = "First Incident"
            env = "Killercoda"
            num = None

        ret = lab_cli.cmd_new(DummyArgs())
        self.assertEqual(ret, 0)
        self.assertTrue((self.root / "INC-000.md").exists())

        # Next should be 1
        self.assertEqual(lab_cli.get_next_inc_num(self.root), 1)

        # Create INC-001
        DummyArgs.title = "Second Incident"
        ret = lab_cli.cmd_new(DummyArgs())
        self.assertEqual(ret, 0)
        self.assertTrue((self.root / "INC-001.md").exists())

        # Validate newly generated files
        self.assertEqual(lab_cli.validate_file(self.root / "INC-000.md"), [])
        self.assertEqual(lab_cli.validate_file(self.root / "INC-001.md"), [])

    def test_new_avoids_overwrite(self):
        class DummyArgs:
            root = str(self.root)
            title = "Collision test"
            env = "Local"
            num = 5

        ret = lab_cli.cmd_new(DummyArgs())
        self.assertEqual(ret, 0)

        # Attempt to create again with same num
        ret2 = lab_cli.cmd_new(DummyArgs())
        self.assertEqual(ret2, 1)


if __name__ == "__main__":
    unittest.main()
