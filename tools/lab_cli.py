#!/usr/bin/env python3
"""
tools/lab_cli.py - Incident Report & Infrastructure Lab Manager CLI
Standard library only. Manages INC-xxx.md scaffolding, verification, and index stats.
"""

import argparse
import datetime
import os
import re
import string
import sys
from pathlib import Path

INC_TEMPLATE = string.Template("""# INC-$num : $title
**DATE** $date
**Environment:** $environment
## What i did 
$what_i_did
## Output 
```bash
$output
```
## What i learned :
$what_i_learned
""")

RE_INC_FILE = re.compile(r"^INC-(\d{3})\.md$", re.IGNORECASE)
RE_INC_HEADER = re.compile(r"^#\s+INC-(\d{3})\s*:\s*(.+)$")
RE_DATE = re.compile(r"^\*\*DATE\*\*\s*(.+)$", re.IGNORECASE)
RE_ENV = re.compile(r"^\*\*Environment:\*\*\s*(.+)$", re.IGNORECASE)


def get_repo_root(root_arg=None) -> Path:
    if root_arg:
        p = Path(root_arg).resolve()
        if not p.is_dir():
            raise FileNotFoundError(f"Provided root directory does not exist: {p}")
        return p
    # Default: assume script is in <root>/tools/
    return Path(__file__).resolve().parent.parent


def find_inc_files(root: Path):
    inc_files = []
    for f in root.glob("INC-*.md"):
        m = RE_INC_FILE.match(f.name)
        if m:
            inc_files.append((int(m.group(1)), f))
    inc_files.sort(key=lambda x: x[0])
    return inc_files


def get_next_inc_num(root: Path) -> int:
    files = find_inc_files(root)
    if not files:
        return 0
    return files[-1][0] + 1


def cmd_new(args) -> int:
    root = get_repo_root(args.root)
    num = args.num
    if num is None:
        num = get_next_inc_num(root)
    
    num_str = f"{num:03d}"
    filename = f"INC-{num_str}.md"
    target_path = root / filename
    
    if target_path.exists():
        sys.stderr.write(f"Error: Target file already exists: {target_path}\n")
        return 1

    today_str = datetime.date.today().isoformat()
    content = INC_TEMPLATE.substitute(
        num=num_str,
        title=args.title.strip(),
        date=today_str,
        environment=args.env.strip(),
        what_i_did="TODO: Describe scenario setup and what was executed.",
        output="root@ubuntu:~$ # Paste raw terminal output here",
        what_i_learned="TODO: Root-cause takeaway, command takeaways, preventive measures."
    )

    try:
        with open(target_path, "x", encoding="utf-8") as f:
            f.write(content)
        print(f"[OK] Created new incident report: {target_path.name}")
        return 0
    except FileExistsError:
        sys.stderr.write(f"Error: File already exists: {target_path}\n")
        return 1
    except OSError as e:
        sys.stderr.write(f"Error writing file: {e}\n")
        return 1


def validate_file(file_path: Path) -> list:
    errors = []
    fname = file_path.name
    m = RE_INC_FILE.match(fname)
    if not m:
        errors.append((1, f"Filename does not match standard pattern 'INC-xxx.md'"))
        return errors
    
    expected_num = m.group(1)
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        errors.append((1, f"Failed to read file: {e}"))
        return errors

    has_h1 = False
    has_date = False
    has_env = False
    has_what_did = False
    has_output = False
    has_learned = False

    for idx, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        
        # Check header
        h_match = RE_INC_HEADER.match(line)
        if h_match:
            has_h1 = True
            header_num = h_match.group(1)
            if header_num != expected_num:
                errors.append((idx, f"Header incident number '{header_num}' does not match filename '{expected_num}'"))
        
        if RE_DATE.match(line):
            has_date = True
        
        if RE_ENV.match(line):
            has_env = True
            
        if line.lower().startswith("## what i did"):
            has_what_did = True
            
        if line.lower().startswith("## output") or line.lower().startswith("##output"):
            has_output = True
            
        if line.lower().startswith("## what i learned"):
            has_learned = True

    if not has_h1:
        errors.append((1, "Missing top-level header (# INC-xxx : <title>)"))
    if not has_date:
        errors.append((2, "Missing date metadata (**DATE** YYYY-MM-DD)"))
    if not has_env:
        errors.append((3, "Missing environment metadata (**Environment:** <env>)"))
    if not has_what_did:
        errors.append((len(lines), "Missing section '## What i did'"))
    if not has_output:
        errors.append((len(lines), "Missing section '## Output'"))
    if not has_learned:
        errors.append((len(lines), "Missing section '## What i learned'"))

    return errors


def cmd_validate(args) -> int:
    root = get_repo_root(args.root)
    total_errors = 0
    total_files = 0

    if args.file:
        target = Path(args.file).resolve()
        targets = [target]
    else:
        targets = [f for _, f in find_inc_files(root)]

    if not targets:
        print("No incident files found to validate.")
        return 0

    for fpath in targets:
        total_files += 1
        errs = validate_file(fpath)
        if errs:
            for line_no, msg in errs:
                sys.stderr.write(f"{fpath.name}:{line_no}: {msg}\n")
                total_errors += 1
        else:
            print(f"[OK] {fpath.name}: Valid")

    if total_errors > 0:
        sys.stderr.write(f"\nValidation failed: {total_errors} issue(s) across {total_files} file(s).\n")
        return 1

    print(f"\nAll {total_files} incident report(s) passed validation.")
    return 0


def cmd_list(args) -> int:
    root = get_repo_root(args.root)
    files = find_inc_files(root)
    if not files:
        print("No incident reports found.")
        return 0

    print(f"{'File':<14} | {'Title':<45} | {'Date':<12}")
    print("-" * 76)
    for num, path in files:
        title = "Unknown"
        date_str = "-"
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    hm = RE_INC_HEADER.match(line.strip())
                    if hm:
                        title = hm.group(2).strip()
                    dm = RE_DATE.match(line.strip())
                    if dm:
                        date_str = dm.group(1).strip()
                    if title != "Unknown" and date_str != "-":
                        break
        except Exception:
            pass
        if len(title) > 42:
            title = title[:41] + "…"
        print(f"{path.name:<14} | {title:<45} | {date_str:<12}")
    print("-" * 76)
    print(f"Total: {len(files)} incident(s)")
    return 0


def main():
    parser = argparse.ArgumentParser(
        prog="lab_cli",
        description="Infrastructure Lab incident reporter and validator"
    )
    parser.add_argument("--root", help="Repository root directory (defaults to parent of tools/)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: new
    parser_new = subparsers.add_parser("new", help="Scaffold a new INC-xxx.md report")
    parser_new.add_argument("-t", "--title", required=True, help="Incident report title")
    parser_new.add_argument("-e", "--env", default="Killercoda Ubuntu Playground", help="Target environment")
    parser_new.add_argument("-n", "--num", type=int, help="Incident number (auto-increments if omitted)")
    parser_new.set_defaults(func=cmd_new)

    # Subcommand: validate
    parser_val = subparsers.add_parser("validate", help="Validate incident reports for format and structure")
    parser_val.add_argument("-f", "--file", help="Specific INC file to validate")
    parser_val.set_defaults(func=cmd_validate)

    # Subcommand: list
    parser_list = subparsers.add_parser("list", help="List all tracked incident reports")
    parser_list.set_defaults(func=cmd_list)

    parsed = parser.parse_args()
    return parsed.func(parsed)


if __name__ == "__main__":
    sys.exit(main())
