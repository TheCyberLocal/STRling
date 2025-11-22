import re
import sys
import os


def strip_file(file_path):
    print(f"Stripping {file_path}...")
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    in_test_each = False
    in_manual_test = False
    start_indent = 0

    for line in lines:
        stripped = line.strip()
        current_indent = len(line) - len(line.lstrip())

        # Check for test.each
        if "test.each" in stripped and not in_test_each and not in_manual_test:
            in_test_each = True
            start_indent = current_indent
            # Check if it ends on the same line (unlikely for these tests but possible)
            if stripped.endswith(");"):
                in_test_each = False
            continue

        # Check for manual test
        if stripped.startswith("test(") and not in_test_each and not in_manual_test:
            in_manual_test = True
            start_indent = current_indent
            # Check if it ends on the same line
            if stripped.endswith("});"):
                in_manual_test = False
            continue

        if in_test_each:
            if stripped.endswith(");") and current_indent == start_indent:
                in_test_each = False
            continue

        if in_manual_test:
            if stripped.endswith("});") and current_indent == start_indent:
                in_manual_test = False
            continue

        new_lines.append(line)

    output = "".join(new_lines)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(output)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python strip_migrated_tests.py <file>")
        sys.exit(1)
    strip_file(sys.argv[1])
