import re
import os
import sys


def migrate_file(ts_file_path, output_dir):
    print(f"Migrating {ts_file_path}...")
    with open(ts_file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    print(f"Read {len(lines)} lines.")

    in_test_each = False
    in_negative_describe = False
    in_manual_test = False
    buffer = ""
    start_indent = 0
    count = 0
    current_test_id = ""

    for line in lines:
        stripped = line.strip()
        current_indent = len(line) - len(line.lstrip())

        if stripped.startswith("describe("):
            if "Negative" in stripped:
                in_negative_describe = True
            else:
                in_negative_describe = False

        if "test.each" in stripped:
            in_test_each = True
            continue

        if stripped.startswith("test("):
            in_manual_test = True
            # Extract test ID from description
            match = re.match(r'test\s*\(\s*(?:`|"|\')(.*?)(?:`|"|\')', stripped)
            if match:
                description = match.group(1)
                # Create ID from description
                current_test_id = (
                    description.lower().replace(" ", "_").replace("-", "_")
                )
                current_test_id = re.sub(r"[^a-z0-9_]", "", current_test_id)

        if in_manual_test:
            # Look for parse("...")
            parse_match = re.search(
                r'parse\s*\(\s*(?:String\.raw)?(`|"|\')(.*?)\1', stripped
            )

            if parse_match:
                pattern = parse_match.group(2)
                quote_type = parse_match.group(1)
                is_raw = "String.raw" in stripped[: stripped.find(pattern)]  # heuristic

                final_pattern = pattern
                if not is_raw and quote_type in ['"', "'"]:
                    try:
                        final_pattern = final_pattern.encode("utf-8").decode(
                            "unicode_escape"
                        )
                    except:
                        pass

                # Check for expected error
                # In manual tests, error checking is usually expect(...).toThrow()
                # We can try to detect if we are in a negative test block or if the test name implies error.

                file_content = ""
                if (
                    (in_negative_describe and "as_a_literal" not in current_test_id)
                    or "fail" in current_test_id
                    or "error" in current_test_id
                ):
                    # We don't have the error message easily available.
                    # We can try to extract it from expect(err.message).toContain("...")
                    # But that might be on a later line.
                    # For now, just add %expect_error without message?
                    # Or skip negative manual tests?

                    # Let's skip negative manual tests for now as they are hard to migrate automatically
                    pass
                else:
                    file_content += final_pattern

                    filename = f"{current_test_id}.pattern"
                    filepath = os.path.join(output_dir, filename)

                    # Avoid overwriting existing files (from test.each)
                    if not os.path.exists(filepath):
                        with open(filepath, "w", encoding="utf-8") as out:
                            out.write(file_content)
                        count += 1

                in_manual_test = False

                in_manual_test = False

            if stripped.endswith("});"):
                in_manual_test = False

        # Start of a test case
        if stripped.startswith("[") and not buffer:
            buffer = stripped
            start_indent = current_indent

            # Check if it ends on the same line
            if stripped.endswith("],") or stripped.endswith("]"):
                # Process immediately
                # Copy-paste processing logic (refactoring would be better but I am lazy)
                content = buffer.rstrip(",")

                # Extract pattern (first string)
                pattern_match = re.match(
                    r'\[\s*(?:String\.raw)?(`|"|\')(.*?)\1', content, re.DOTALL
                )

                # Extract ID (last string)
                id_match = re.search(
                    r'(?:`|"|\')([a-zA-Z0-9_]+)(?:`|"|\')\s*,?\s*\]', content
                )

                if pattern_match and id_match:
                    pattern = pattern_match.group(2)
                    test_id = id_match.group(1)

                    quote_type = pattern_match.group(1)
                    is_raw = "String.raw" in content[:20]  # heuristic

                    final_pattern = pattern
                    if not is_raw and quote_type in ['"', "'"]:
                        try:
                            final_pattern = final_pattern.encode("utf-8").decode(
                                "unicode_escape"
                            )
                        except:
                            pass

                    # Check for expected error
                    file_content = ""
                    if in_negative_describe:
                        second_str_match = re.match(
                            r'\[\s*(?:String\.raw)?(?:`|"|\').*?(?:`|"|\')\s*,\s*(?:String\.raw)?(`|"|\')(.*?)\1',
                            content,
                            re.DOTALL,
                        )

                        if second_str_match:
                            error_msg = second_str_match.group(2)
                            # Unescape error message
                            try:
                                error_msg = error_msg.encode("utf-8").decode(
                                    "unicode_escape"
                                )
                            except:
                                pass
                            file_content += f"%expect_error {error_msg}\n"

                    file_content += final_pattern

                    filename = f"{test_id}.pattern"
                    filepath = os.path.join(output_dir, filename)

                    with open(filepath, "w", encoding="utf-8") as out:
                        out.write(file_content)

                    count += 1
                else:
                    print(f"Warning: Could not parse: ...{content[-50:]}")

                buffer = ""

        elif buffer:
            buffer += " " + stripped

            # End of a test case
            # We check if the line is just "]," or "]" and indentation matches start
            if (stripped == "]," or stripped == "]") and current_indent == start_indent:
                # Process the buffer
                content = buffer.rstrip(",")

                # Extract pattern (first string)
                pattern_match = re.match(
                    r'\[\s*(?:String\.raw)?(`|"|\')(.*?)\1', content, re.DOTALL
                )

                # Extract ID (last string)
                id_match = re.search(
                    r'(?:`|"|\')([a-zA-Z0-9_]+)(?:`|"|\')\s*,?\s*\]', content
                )

                if pattern_match and id_match:
                    pattern = pattern_match.group(2)
                    test_id = id_match.group(1)

                    quote_type = pattern_match.group(1)
                    is_raw = "String.raw" in content[:20]  # heuristic

                    final_pattern = pattern
                    if not is_raw and quote_type in ['"', "'"]:
                        try:
                            final_pattern = final_pattern.encode("utf-8").decode(
                                "unicode_escape"
                            )
                        except:
                            pass

                    # Check for expected error
                    file_content = ""
                    if in_negative_describe:
                        second_str_match = re.match(
                            r'\[\s*(?:String\.raw)?(?:`|"|\').*?(?:`|"|\')\s*,\s*(?:String\.raw)?(`|"|\')(.*?)\1',
                            content,
                            re.DOTALL,
                        )

                        if second_str_match:
                            error_msg = second_str_match.group(2)
                            # Unescape error message
                            try:
                                error_msg = error_msg.encode("utf-8").decode(
                                    "unicode_escape"
                                )
                            except:
                                pass
                            file_content += f"%expect_error {error_msg}\n"

                    file_content += final_pattern

                    filename = f"{test_id}.pattern"
                    filepath = os.path.join(output_dir, filename)

                    with open(filepath, "w", encoding="utf-8") as out:
                        out.write(file_content)

                    count += 1
                else:
                    print(f"Warning: Could not parse: ...{content[-50:]}")

                buffer = ""

    print(f"Extracted {count} tests from {ts_file_path}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python migrate_tests.py <ts_file> <output_dir>")
        sys.exit(1)

    ts_file = sys.argv[1]
    output_dir = sys.argv[2]

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    migrate_file(ts_file, output_dir)
