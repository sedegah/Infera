import ast
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, List, Set, Tuple


class UnsafeZipArchiveError(ValueError):
    """Raised when a zip archive contains unsafe member paths."""


def parse_codebase(zip_path: str) -> Tuple[Dict, str]:
    """
    Parses a zipped codebase and returns:
    1. Full folder structure
    2. Mermaid class diagram (classes, inheritance, methods, attributes, module functions)
    """
    if not os.path.exists(zip_path):
        raise FileNotFoundError(f"Zip file not found: {zip_path}")

    tmp_dir = tempfile.mkdtemp(prefix="infera_")
    try:
        extract_zip_safely(zip_path, tmp_dir)
        structure = scan_dir(tmp_dir)
        mermaid_erd = generate_mermaid_erd(tmp_dir)
        return structure, mermaid_erd
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def extract_zip_safely(zip_path: str, destination: str) -> None:
    """Extract zip contents while blocking Zip Slip style path traversal."""
    destination_path = Path(destination).resolve()
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        for member in zip_ref.infolist():
            member_path = (destination_path / member.filename).resolve()
            if destination_path not in member_path.parents and member_path != destination_path:
                raise UnsafeZipArchiveError(f"Unsafe path in zip file: {member.filename}")
        zip_ref.extractall(destination_path)


def scan_dir(path: str) -> Dict:
    tree: Dict = {}
    entries = sorted(os.scandir(path), key=lambda entry: (not entry.is_dir(), entry.name.lower()))
    for entry in entries:
        if entry.is_dir():
            tree[entry.name] = scan_dir(entry.path)
        else:
            tree[entry.name] = None
    return tree


def generate_mermaid_erd(path: str) -> str:
    """Generate Mermaid classDiagram text for Python files in a directory."""
    classes: Dict[str, Dict[str, Set[str]]] = {}
    relationships: List[Tuple[str, str]] = []
    module_functions: Dict[str, Set[str]] = {}

    for root, _, files in os.walk(path):
        rel_root = os.path.relpath(root, path).replace("\\", "/")
        module_functions.setdefault(rel_root, set())
        for file_name in sorted(files):
            if not file_name.endswith(".py"):
                continue

            file_path = os.path.join(root, file_name)
            parsed = parse_python_file(file_path)
            for class_name, data in parsed["classes"].items():
                if class_name not in classes:
                    classes[class_name] = {"methods": set(), "attributes": set()}
                classes[class_name]["methods"].update(data["methods"])
                classes[class_name]["attributes"].update(data["attributes"])

            relationships.extend(parsed["relationships"])
            module_functions[rel_root].update(parsed["module_functions"])

    lines = ["classDiagram"]
    for class_name in sorted(classes):
        members = sorted(classes[class_name]["attributes"]) + sorted(classes[class_name]["methods"])
        if members:
            member_block = "\\n".join(members)
            lines.append(f"    class {class_name} {{ {member_block} }}")
        else:
            lines.append(f"    class {class_name}")

    for parent, child in sorted(set(relationships)):
        lines.append(f"    {parent} <|-- {child}")

    for module_name in sorted(module_functions):
        funcs = sorted(module_functions[module_name])
        if funcs:
            module_class_name = "root" if module_name == "." else module_name.replace("/", "_")
            module_class_name = f"{module_class_name}_module"
            function_block = "\\n".join(funcs)
            lines.append(f"    class {module_class_name} {{ {function_block} }}")

    return "\n".join(lines)


def parse_python_file(file_path: str) -> Dict[str, object]:
    """Parse a Python file using AST and return class/module metadata."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as source_file:
            tree = ast.parse(source_file.read())
    except SyntaxError:
        return {"classes": {}, "relationships": [], "module_functions": set()}

    classes: Dict[str, Dict[str, Set[str]]] = {}
    relationships: List[Tuple[str, str]] = []
    module_functions: Set[str] = set()

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            class_name = node.name
            classes[class_name] = {"methods": set(), "attributes": set()}

            for base in node.bases:
                if isinstance(base, ast.Name):
                    relationships.append((base.id, class_name))
                elif isinstance(base, ast.Attribute):
                    relationships.append((base.attr, class_name))

            for class_item in node.body:
                if isinstance(class_item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    classes[class_name]["methods"].add(class_item.name)
                    for statement in ast.walk(class_item):
                        if isinstance(statement, ast.Assign):
                            for target in statement.targets:
                                attribute = extract_self_attribute(target)
                                if attribute:
                                    classes[class_name]["attributes"].add(attribute)
                        elif isinstance(statement, ast.AnnAssign):
                            attribute = extract_self_attribute(statement.target)
                            if attribute:
                                classes[class_name]["attributes"].add(attribute)

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            module_functions.add(node.name)

    return {
        "classes": classes,
        "relationships": relationships,
        "module_functions": module_functions,
    }


def extract_self_attribute(node: ast.AST) -> str | None:
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "self":
        return node.attr
    return None
