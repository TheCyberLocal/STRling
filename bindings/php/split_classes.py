import re
import os


def split_file(source_file, output_dir, namespace):
    with open(source_file, "r") as f:
        content = f.read()

    lines = content.split("\n")

    current_class_name = None
    buffer = []
    in_class = False
    brace_count = 0
    started_block = False

    imports = ["use JsonSerializable;"]

    for line in lines:
        stripped = line.strip()

        # Detect start of class/interface
        if not in_class:
            if (
                stripped.startswith("class ")
                or stripped.startswith("interface ")
                or stripped.startswith("readonly class ")
                or stripped.startswith("abstract class ")
            ):
                match = re.search(r"(?:class|interface)\s+(\w+)", stripped)
                if match:
                    current_class_name = match.group(1)
                    in_class = True
                    brace_count = 0
                    started_block = False

            # Always append to buffer (docblocks etc)
            buffer.append(line)

            if in_class:
                # Check for opening brace on the same line
                brace_count += line.count("{")
                brace_count -= line.count("}")
                if "{" in line:
                    started_block = True
        else:
            buffer.append(line)
            brace_count += line.count("{")
            brace_count -= line.count("}")
            if "{" in line:
                started_block = True

            if started_block and brace_count == 0:
                # Class finished
                write_class(output_dir, namespace, current_class_name, buffer, imports)
                buffer = []
                in_class = False
                current_class_name = None
                started_block = False


def write_class(output_dir, namespace, class_name, lines, imports):
    if not class_name:
        return

    filename = os.path.join(output_dir, f"{class_name}.php")

    # Clean up leading empty lines/comments that don't belong
    # Actually, we might have captured previous class's trailing newlines or comments
    # But for now let's just write it.

    # Filter out lines that are just namespace or use from original file if we captured them
    # My logic captures everything before the class starts, which might include the file header.
    # We need to be smarter.

    # Refined logic:
    # Only keep docblocks immediately preceding the class.

    final_lines = []
    docblock_buffer = []
    capturing_docblock = False

    # Scan backwards from the class definition line
    class_def_index = -1
    for i, line in enumerate(lines):
        if f"class {class_name}" in line or f"interface {class_name}" in line:
            class_def_index = i
            break

    if class_def_index == -1:
        # Fallback
        final_lines = lines
    else:
        # Get the class body
        body = lines[class_def_index:]

        # Get docblock
        preamble = lines[:class_def_index]
        docblock = []
        if preamble:
            # Take lines from the end of preamble as long as they are comments or empty
            for line in reversed(preamble):
                s = line.strip()
                if (
                    s.startswith("//")
                    or s.startswith("*")
                    or s.startswith("/**")
                    or s.startswith("*/")
                    or not s
                ):
                    docblock.insert(0, line)
                else:
                    break  # Stop at non-comment code (like previous class end)

        final_lines = docblock + body

    content = "<?php\n\n"
    content += f"namespace {namespace};\n\n"
    for imp in imports:
        content += f"{imp}\n"
    content += "\n"
    content += "\n".join(final_lines)
    content += "\n"

    with open(filename, "w") as f:
        f.write(content)
    print(f"Created {filename}")


if __name__ == "__main__":
    base_path = "src/Core"

    # Split Nodes.php
    split_file(
        os.path.join(base_path, "Nodes.php"),
        os.path.join(base_path, "Nodes"),
        "STRling\\Core\\Nodes",
    )

    # Split IR.php
    split_file(
        os.path.join(base_path, "IR.php"),
        os.path.join(base_path, "IR"),
        "STRling\\Core\\IR",
    )
