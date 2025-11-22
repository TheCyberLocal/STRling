import json
import glob
import os


def scan_files():
    # Use relative path since we will run this from the root
    files = glob.glob("tests/spec/*.json")
    types = {}

    for file_path in files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if "input_ast" in data:
                ast = data["input_ast"]

                # Helper function to recursively scan AST nodes
                def scan_node(node):
                    if isinstance(node, dict) and "type" in node:
                        type_name = node["type"]
                        keys = set(node.keys())

                        if type_name == "Group":
                            if "body" in node and "expression" in node:
                                print(
                                    f"WARNING: Group has both body and expression in {file_path}"
                                )
                            if "body" in node:
                                print(f"INFO: Group has body in {file_path}")
                            if "expression" in node:
                                print(f"INFO: Group has expression in {file_path}")

                        if type_name not in types:
                            types[type_name] = set()

                        types[type_name].update(keys)

                        # Recursively check children
                        for key, value in node.items():
                            if isinstance(value, dict):
                                scan_node(value)
                            elif isinstance(value, list):
                                for item in value:
                                    scan_node(item)

                scan_node(ast)

        except Exception as e:
            print(f"Error processing {file_path}: {e}")

    print("Unique types and their keys:")
    for type_name, keys in sorted(types.items()):
        print(f"\nType: {type_name}")
        print(f"Keys: {', '.join(sorted(keys))}")


if __name__ == "__main__":
    scan_files()
