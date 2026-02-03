#!/usr/bin/env python3
"""
AST-based Python file merging utilities.

This module provides robust merging of Python files using the ast module,
avoiding the structural corruption issues caused by text-based merging.

Key features:
- Proper handling of decorators attached to classes/functions
- Correct ordering of imports (__future__ first, then standard, then typing)
- Topological sorting of classes based on dependencies
- Detection of TYPE_CHECKING blocks
- Preservation of docstrings and comments where possible
"""
from __future__ import annotations

import ast
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

# For Python 3.9+ we can use ast.unparse, otherwise fallback
if sys.version_info >= (3, 9):
    from ast import unparse as ast_unparse
else:
    # Fallback for older Python
    import astor
    ast_unparse = astor.to_source


@dataclass
class ParsedPythonFile:
    """Represents a parsed Python file with categorized components."""

    # File metadata
    source_path: Optional[Path] = None

    # Docstring (module-level)
    module_docstring: Optional[str] = None

    # Imports categorized by type
    future_imports: List[ast.ImportFrom] = field(default_factory=list)
    regular_imports: List[Union[ast.Import, ast.ImportFrom]] = field(default_factory=list)
    type_checking_imports: List[ast.stmt] = field(default_factory=list)

    # Definitions
    classes: Dict[str, ast.ClassDef] = field(default_factory=dict)
    functions: Dict[str, ast.FunctionDef] = field(default_factory=dict)
    constants: List[ast.Assign] = field(default_factory=list)

    # Special exports
    all_export: Optional[List[str]] = None

    # Raw AST for anything we couldn't categorize
    other_statements: List[ast.stmt] = field(default_factory=list)


@dataclass
class MergeResult:
    """Result of merging Python files."""

    content: str
    warnings: List[str] = field(default_factory=list)
    classes_merged: List[str] = field(default_factory=list)
    functions_merged: List[str] = field(default_factory=list)
    imports_deduplicated: int = 0


def parse_python_file(source_path: Path) -> ParsedPythonFile:
    """
    Parse a Python file into categorized components.

    Args:
        source_path: Path to the Python file

    Returns:
        ParsedPythonFile with categorized components

    Raises:
        SyntaxError: If the file contains invalid Python syntax
    """
    with open(source_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Clean markdown code blocks if present
    content = _clean_markdown_blocks(content)

    # Parse the AST
    tree = ast.parse(content, filename=str(source_path))

    result = ParsedPythonFile(source_path=source_path)

    # Extract module docstring
    # Note: ast.Str is removed in Python 3.14, use only ast.Constant
    if (tree.body and
        isinstance(tree.body[0], ast.Expr) and
        isinstance(tree.body[0].value, ast.Constant) and
        isinstance(tree.body[0].value.value, str)):
        result.module_docstring = tree.body[0].value.value

    # Track if we're in a TYPE_CHECKING block
    in_type_checking = False

    for node in ast.walk(tree):
        # We only want top-level statements
        if node not in tree.body:
            continue

        # Skip the docstring if we already extracted it
        if (isinstance(node, ast.Expr) and
            isinstance(node.value, ast.Constant) and
            isinstance(node.value.value, str) and
            node == tree.body[0]):
            continue

        # Future imports
        if isinstance(node, ast.ImportFrom) and node.module == '__future__':
            result.future_imports.append(node)

        # Regular imports
        elif isinstance(node, ast.Import):
            result.regular_imports.append(node)
        elif isinstance(node, ast.ImportFrom):
            result.regular_imports.append(node)

        # Class definitions
        elif isinstance(node, ast.ClassDef):
            result.classes[node.name] = node

        # Function definitions
        elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            result.functions[node.name] = node

        # Assignments (constants, __all__, etc.)
        elif isinstance(node, ast.Assign):
            # Check if it's __all__
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == '__all__':
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        result.all_export = [
                            elt.value
                            for elt in node.value.elts
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                        ]
                    continue
            # Other constants
            result.constants.append(node)

        # If blocks: TYPE_CHECKING or __main__ guard
        elif isinstance(node, ast.If):
            if _is_main_guard(node):
                pass  # Exclude __main__ blocks from merge
            elif _is_type_checking(node):
                result.type_checking_imports.append(node)
            else:
                result.other_statements.append(node)

        # Module-level bare calls (example/demo code like print(), AgentCard())
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            pass  # Exclude module-level calls from merge

        # Everything else
        else:
            result.other_statements.append(node)

    return result


def _clean_markdown_blocks(content: str) -> str:
    """Remove markdown code blocks from content."""
    content = content.strip()
    lines = content.split('\n')

    # Remove opening ```python or ``` at the start
    if lines and lines[0].strip().startswith('```'):
        lines = lines[1:]

    # Remove closing ``` at the end
    if lines and lines[-1].strip() == '```':
        lines = lines[:-1]

    return '\n'.join(lines)


def _is_main_guard(node: ast.If) -> bool:
    """Check if an ast.If node is an ``if __name__ == "__main__":`` guard."""
    test = node.test
    return (isinstance(test, ast.Compare) and
            isinstance(test.left, ast.Name) and test.left.id == '__name__' and
            len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq) and
            len(test.comparators) == 1 and
            isinstance(test.comparators[0], ast.Constant) and
            test.comparators[0].value == '__main__')


def _is_type_checking(node: ast.If) -> bool:
    """Check if an ast.If node is a ``TYPE_CHECKING`` block."""
    test = node.test
    return ((isinstance(test, ast.Name) and test.id == 'TYPE_CHECKING') or
            (isinstance(test, ast.Attribute) and test.attr == 'TYPE_CHECKING'))


def detect_class_dependencies(cls: ast.ClassDef, all_classes: Set[str]) -> Set[str]:
    """
    Detect classes that this class depends on.

    Checks:
    - Base classes (inheritance)
    - Type annotations
    - Default values
    """
    deps = set()

    # Check base classes
    for base in cls.bases:
        if isinstance(base, ast.Name) and base.id in all_classes:
            deps.add(base.id)
        elif isinstance(base, ast.Subscript):
            # Generic types like List[Foo]
            _extract_names_from_node(base, all_classes, deps)

    # Check type annotations in class body
    for node in ast.walk(cls):
        if isinstance(node, ast.AnnAssign) and node.annotation:
            _extract_names_from_node(node.annotation, all_classes, deps)
        elif isinstance(node, ast.FunctionDef):
            # Check argument annotations
            for arg in node.args.args + node.args.kwonlyargs:
                if arg.annotation:
                    _extract_names_from_node(arg.annotation, all_classes, deps)
            # Check return annotation
            if node.returns:
                _extract_names_from_node(node.returns, all_classes, deps)

    # Don't include self-reference
    deps.discard(cls.name)

    return deps


def _extract_names_from_node(node: ast.AST, all_classes: Set[str], deps: Set[str]) -> None:
    """Extract class names from an AST node."""
    if isinstance(node, ast.Name) and node.id in all_classes:
        deps.add(node.id)
    elif isinstance(node, ast.Subscript):
        _extract_names_from_node(node.value, all_classes, deps)
        _extract_names_from_node(node.slice, all_classes, deps)
    elif isinstance(node, (ast.Tuple, ast.List)):
        for elt in node.elts:
            _extract_names_from_node(elt, all_classes, deps)
    elif isinstance(node, ast.BinOp):
        # Union types with | operator (Python 3.10+)
        _extract_names_from_node(node.left, all_classes, deps)
        _extract_names_from_node(node.right, all_classes, deps)
    elif isinstance(node, ast.Constant) and isinstance(node.value, str):
        # Forward reference as string
        if node.value in all_classes:
            deps.add(node.value)


def topological_sort_classes(classes: Dict[str, ast.ClassDef]) -> List[str]:
    """
    Sort classes so dependencies come before dependents.

    Uses Kahn's algorithm for topological sorting.
    Handles circular dependencies by appending them at the end.
    """
    all_names = set(classes.keys())
    deps = {name: detect_class_dependencies(cls, all_names)
            for name, cls in classes.items()}

    # Calculate in-degree for each class
    in_degree = {name: 0 for name in classes}
    for name, class_deps in deps.items():
        for dep in class_deps:
            if dep in in_degree:
                in_degree[dep] = in_degree.get(dep, 0)

    # Count how many times each class is depended on
    for name, class_deps in deps.items():
        for dep in class_deps:
            if dep in in_degree:
                pass  # We want to process deps first, not dependents

    # Kahn's algorithm
    result = []
    # Start with classes that have no dependencies
    no_deps = [n for n, d in deps.items() if not d]

    # Sort for deterministic output
    no_deps.sort()

    visited = set()
    while no_deps:
        name = no_deps.pop(0)
        if name in visited:
            continue
        visited.add(name)
        result.append(name)

        # Check which classes can now be processed
        for other_name, other_deps in deps.items():
            if other_name in visited:
                continue
            # Remove this class from dependencies
            other_deps.discard(name)
            if not other_deps and other_name not in visited:
                no_deps.append(other_name)
                no_deps.sort()  # Keep sorted for determinism

    # Add any remaining classes (circular dependencies)
    for name in sorted(classes.keys()):
        if name not in result:
            result.append(name)

    return result


def deduplicate_imports(imports: List[Union[ast.Import, ast.ImportFrom]]) -> List[Union[ast.Import, ast.ImportFrom]]:
    """
    Deduplicate imports while preserving order.

    For 'from X import a, b' style imports, merges imports from the same module.
    """
    seen_imports = set()  # For 'import X' style
    from_imports: Dict[str, Set[str]] = {}  # module -> set of names
    from_import_nodes: Dict[str, ast.ImportFrom] = {}  # Keep first node for each module
    result = []

    for node in imports:
        if isinstance(node, ast.Import):
            # 'import X' or 'import X, Y'
            for alias in node.names:
                key = (alias.name, alias.asname)
                if key not in seen_imports:
                    seen_imports.add(key)
                    # Create individual import for clarity
                    new_node = ast.Import(names=[alias])
                    ast.copy_location(new_node, node)
                    result.append(new_node)

        elif isinstance(node, ast.ImportFrom):
            # 'from X import a, b'
            module = node.module or ''
            level = node.level  # Relative import level
            key = (module, level)

            if key not in from_imports:
                from_imports[key] = set()
                from_import_nodes[key] = node

            for alias in node.names:
                name_key = (alias.name, alias.asname)
                from_imports[key].add(name_key)

    # Reconstruct from imports
    for (module, level), names in sorted(from_imports.items()):
        original_node = from_import_nodes[(module, level)]
        aliases = [
            ast.alias(name=name, asname=asname)
            for name, asname in sorted(names)
        ]
        new_node = ast.ImportFrom(
            module=module if module else None,
            names=aliases,
            level=level
        )
        ast.copy_location(new_node, original_node)
        result.append(new_node)

    return result


def merge_class_definitions(
    existing: ast.ClassDef,
    new: ast.ClassDef
) -> Tuple[ast.ClassDef, List[str]]:
    """
    Merge two class definitions.

    Strategy:
    - Keep existing class structure (decorators, bases)
    - Add new methods that don't exist in existing
    - For duplicate methods: keep existing, emit warning
    - Merge class-level attributes

    Returns:
        Tuple of (merged class, list of warnings)
    """
    warnings = []

    # Start with a copy of the existing class
    merged = existing

    # Get existing method and attribute names
    existing_methods = {
        node.name for node in existing.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    existing_attrs = {
        node.targets[0].id for node in existing.body
        if isinstance(node, ast.Assign) and
           len(node.targets) == 1 and
           isinstance(node.targets[0], ast.Name)
    }
    existing_ann_attrs = {
        node.target.id for node in existing.body
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    }

    # Add new methods/attributes that don't exist
    new_body_items = []
    for node in new.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name in existing_methods:
                warnings.append(
                    f"Duplicate method '{existing.name}.{node.name}' - keeping existing"
                )
            else:
                new_body_items.append(node)

        elif isinstance(node, ast.Assign):
            if (len(node.targets) == 1 and
                isinstance(node.targets[0], ast.Name)):
                attr_name = node.targets[0].id
                if attr_name in existing_attrs:
                    warnings.append(
                        f"Duplicate attribute '{existing.name}.{attr_name}' - keeping existing"
                    )
                else:
                    new_body_items.append(node)
            else:
                new_body_items.append(node)

        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                attr_name = node.target.id
                if attr_name in existing_ann_attrs:
                    warnings.append(
                        f"Duplicate annotated attribute '{existing.name}.{attr_name}' - keeping existing"
                    )
                else:
                    new_body_items.append(node)
            else:
                new_body_items.append(node)

        else:
            # Other statements (pass, expressions, etc.)
            new_body_items.append(node)

    # Append new items to existing body
    if new_body_items:
        merged.body = list(existing.body) + new_body_items

    return merged, warnings


def merge_parsed_files(files: List[ParsedPythonFile]) -> MergeResult:
    """
    Merge multiple parsed Python files into a single output.

    Strategy:
    1. Collect all docstrings (use first non-empty)
    2. Collect all future imports (deduplicate)
    3. Collect all regular imports (deduplicate)
    4. Collect all TYPE_CHECKING blocks
    5. Merge classes (topologically sorted)
    6. Merge functions
    7. Merge constants
    8. Generate __all__ list
    """
    result = MergeResult(content='')
    warnings = []

    # Collect components from all files
    module_docstring: Optional[str] = None
    all_future_imports: List[ast.ImportFrom] = []
    all_regular_imports: List[Union[ast.Import, ast.ImportFrom]] = []
    all_type_checking: List[ast.stmt] = []
    all_classes: Dict[str, ast.ClassDef] = {}
    all_functions: Dict[str, ast.FunctionDef] = {}
    all_constants: List[ast.Assign] = []
    all_exports: Set[str] = set()
    all_other: List[ast.stmt] = []

    for parsed in files:
        # Use first non-empty docstring
        if not module_docstring and parsed.module_docstring:
            module_docstring = parsed.module_docstring

        # Collect imports
        all_future_imports.extend(parsed.future_imports)
        all_regular_imports.extend(parsed.regular_imports)
        all_type_checking.extend(parsed.type_checking_imports)

        # Merge classes
        for name, cls in parsed.classes.items():
            if name in all_classes:
                merged_cls, merge_warnings = merge_class_definitions(
                    all_classes[name], cls
                )
                all_classes[name] = merged_cls
                warnings.extend(merge_warnings)
                result.classes_merged.append(name)
            else:
                all_classes[name] = cls

        # Merge functions
        for name, func in parsed.functions.items():
            if name in all_functions:
                warnings.append(f"Duplicate function '{name}' - keeping first occurrence")
            else:
                all_functions[name] = func
                result.functions_merged.append(name)

        # Collect constants
        all_constants.extend(parsed.constants)

        # Collect exports
        if parsed.all_export:
            all_exports.update(parsed.all_export)

        # Collect other statements
        all_other.extend(parsed.other_statements)

    # Deduplicate imports
    original_import_count = len(all_future_imports) + len(all_regular_imports)
    deduped_future = deduplicate_imports(all_future_imports)
    deduped_regular = deduplicate_imports(all_regular_imports)
    result.imports_deduplicated = original_import_count - len(deduped_future) - len(deduped_regular)

    # Sort classes topologically
    sorted_class_names = topological_sort_classes(all_classes)

    # Build the merged module
    body: List[ast.stmt] = []

    # Add docstring
    if module_docstring:
        body.append(ast.Expr(value=ast.Constant(value=module_docstring)))

    # Add future imports first
    body.extend(deduped_future)

    # Add regular imports
    body.extend(deduped_regular)

    # Add TYPE_CHECKING blocks
    body.extend(all_type_checking)

    # Add constants (before classes in case they're used as defaults)
    body.extend(all_constants)

    # Add classes in topological order
    for class_name in sorted_class_names:
        body.append(all_classes[class_name])

    # Add functions
    for func_name in sorted(all_functions.keys()):
        body.append(all_functions[func_name])

    # Exclude uncategorized statements (example code, bare expressions)
    if all_other:
        warnings.append(f"Excluded {len(all_other)} uncategorized statement(s) from merge output")

    # Add __all__ at the end if we have exports
    if all_exports or all_classes or all_functions:
        # If the first file (target) has explicit __all__, preserve it as baseline
        if files and files[0].all_export is not None:
            final_exports = set(files[0].all_export)
            for parsed in files[1:]:
                if parsed.all_export:
                    final_exports.update(parsed.all_export)
        else:
            # Auto-generate from public classes and functions
            final_exports = {n for n in all_classes if not n.startswith('_')}
            final_exports.update(n for n in all_functions if not n.startswith('_'))

        all_node = ast.Assign(
            targets=[ast.Name(id='__all__', ctx=ast.Store())],
            value=ast.List(
                elts=[ast.Constant(value=name) for name in sorted(final_exports)],
                ctx=ast.Load()
            )
        )
        body.append(all_node)

    # Create module
    module = ast.Module(body=body, type_ignores=[])
    ast.fix_missing_locations(module)

    # Convert back to source
    try:
        result.content = ast_unparse(module)
    except Exception as e:
        warnings.append(f"Failed to unparse merged AST: {e}")
        result.content = ''

    result.warnings = warnings
    return result


def merge_python_files(
    target_path: Path,
    source_paths: List[Path],
    include_target: bool = True
) -> MergeResult:
    """
    High-level function to merge Python files.

    Args:
        target_path: Path to the target file (will be included if it exists)
        source_paths: List of source file paths to merge
        include_target: If True, include existing target in merge

    Returns:
        MergeResult with merged content
    """
    parsed_files = []
    warnings = []

    # Include existing target first (so its content takes precedence)
    if include_target and target_path.exists():
        try:
            parsed = parse_python_file(target_path)
            parsed_files.append(parsed)
        except SyntaxError as e:
            warnings.append(f"Skipping target {target_path.name} due to syntax error: {e}")

    # Parse source files
    for src_path in source_paths:
        if not src_path.exists():
            warnings.append(f"Source file not found: {src_path}")
            continue
        try:
            parsed = parse_python_file(src_path)
            parsed_files.append(parsed)
        except SyntaxError as e:
            warnings.append(f"Skipping {src_path.name} due to syntax error: {e}")
            continue

    if not parsed_files:
        result = MergeResult(content='')
        result.warnings = warnings + ["No valid files to merge"]
        return result

    result = merge_parsed_files(parsed_files)
    result.warnings = warnings + result.warnings
    return result


# Convenience function for testing
def merge_from_strings(sources: List[str]) -> MergeResult:
    """
    Merge Python code from strings (for testing).

    Args:
        sources: List of Python source code strings

    Returns:
        MergeResult with merged content
    """
    parsed_files = []
    warnings = []

    for i, source in enumerate(sources):
        try:
            tree = ast.parse(source)
            parsed = ParsedPythonFile()

            # Simple parsing for testing
            for node in tree.body:
                if isinstance(node, ast.ImportFrom) and node.module == '__future__':
                    parsed.future_imports.append(node)
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    parsed.regular_imports.append(node)
                elif isinstance(node, ast.ClassDef):
                    parsed.classes[node.name] = node
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    parsed.functions[node.name] = node
                elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
                    if not parsed.module_docstring and isinstance(node.value.value, str):
                        parsed.module_docstring = node.value.value

            parsed_files.append(parsed)
        except SyntaxError as e:
            warnings.append(f"Source {i} has syntax error: {e}")

    if not parsed_files:
        return MergeResult(content='', warnings=warnings)

    result = merge_parsed_files(parsed_files)
    result.warnings = warnings + result.warnings
    return result
