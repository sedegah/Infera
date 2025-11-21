import os
import zipfile
import tempfile
from typing import Tuple, Dict, List
import re
import shutil

def parse_codebase(zip_path: str) -> Tuple[Dict, str]:
    """
    Parses a zipped codebase and returns:
    1. Full folder structure
    2. Detailed Mermaid class diagram including:
       - classes
       - methods
       - attributes
       - module-level functions
       - packages
    """
    if not os.path.exists(zip_path):
        raise FileNotFoundError(f"Zip file not found: {zip_path}")

    tmp_dir = tempfile.mkdtemp(prefix="infera_")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(tmp_dir)

        structure = scan_dir(tmp_dir)
        mermaid_erd = generate_mermaid_erd(tmp_dir)

        return structure, mermaid_erd
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

def scan_dir(path: str) -> Dict:
    tree = {}
    for entry in os.scandir(path):
        if entry.is_dir():
            tree[entry.name] = scan_dir(entry.path)
        else:
            tree[entry.name] = None
    return tree

def generate_mermaid_erd(path: str) -> str:
    """
    Generates Mermaid class diagram with classes, inheritance, methods, attributes,
    module-level functions, and package structure.
    """
    class_pattern = re.compile(r'class\s+(\w+)(?:\((\w+)\))?:')
    method_pattern = re.compile(r'^\s+def\s+(\w+)\s*\(')
    attr_pattern = re.compile(r'^\s+self\.(\w+)\s*=')
    func_pattern = re.compile(r'^def\s+(\w+)\s*\(')

    classes: Dict[str, Dict] = {}
    relationships: List[Tuple[str, str]] = []
    module_functions: Dict[str, List[str]] = {}

    for root, dirs, files in os.walk(path):
        rel_root = os.path.relpath(root, path).replace("\\", "/")
        module_functions[rel_root] = []
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                current_class = None
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        line_strip = line.strip()
                        class_match = class_pattern.match(line_strip)
                        if class_match:
                            cls_name = class_match.group(1)
                            parent = class_match.group(2)
                            current_class = cls_name
                            classes[cls_name] = {"methods": [], "attributes": [], "file": os.path.relpath(file_path, path)}
                            if parent:
                                relationships.append((parent, cls_name))
                        elif current_class:
                            method_match = method_pattern.match(line)
                            if method_match:
                                classes[current_class]["methods"].append(method_match.group(1))
                            attr_match = attr_pattern.match(line)
                            if attr_match:
                                classes[current_class]["attributes"].append(attr_match.group(1))
                        else:
                            func_match = func_pattern.match(line_strip)
                            if func_match:
                                module_functions[rel_root].append(func_match.group(1))

    # Build Mermaid diagram
    lines = ["classDiagram"]
    for cls, info in classes.items():
        members = []
        if info["attributes"]:
            members.extend(info["attributes"])
        if info["methods"]:
            members.extend(info["methods"])
        if members:
            lines.append(f'    class {cls} {{ {"\\n".join(members)} }}')
        else:
            lines.append(f'    class {cls}')
    for parent, child in relationships:
        lines.append(f'    {parent} <|-- {child}')

    # Optional: show module-level functions as separate classes
    for mod, funcs in module_functions.items():
        if funcs:
            mod_class_name = mod.replace("/", "_") + "_module"
            lines.append(f'    class {mod_class_name} {{ {"\\n".join(funcs)} }}')

    return "\n".join(lines)
