import os
import json


def analyze_spec_files(directory):
    ir_types = {}

    for filename in os.listdir(directory):
        if filename.endswith(".json"):
            filepath = os.path.join(directory, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)

                    # Helper function to traverse the IR tree
                    def traverse(node):
                        if isinstance(node, dict):
                            if "ir" in node:
                                ir_type = node["ir"]
                                keys = sorted(list(node.keys()))
                                if ir_type not in ir_types:
                                    ir_types[ir_type] = set()
                                ir_types[ir_type].add(tuple(keys))

                            for key, value in node.items():
                                traverse(value)
                        elif isinstance(node, list):
                            for item in node:
                                traverse(item)

                    if "expected_ir" in data:
                        traverse(data["expected_ir"])

            except json.JSONDecodeError:
                print(f"Error decoding JSON in {filename}")
            except Exception as e:
                print(f"Error processing {filename}: {e}")

    print("Unique 'ir' values and their field names:")
    for ir_type, keys_set in sorted(ir_types.items()):
        print(f"\nType: {ir_type}")
        for keys in keys_set:
            print(f"  Fields: {', '.join(keys)}")


if __name__ == "__main__":
    analyze_spec_files("tests/spec")
