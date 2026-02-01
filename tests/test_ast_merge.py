#!/usr/bin/env python3
"""
Tests for AST-based Python file merging.

Tests cover:
- File parsing (docstrings, imports, TYPE_CHECKING blocks)
- Class dependency detection
- Topological sorting
- Class merging (add methods, warn on duplicates, preserve decorators)
- Import deduplication
- Full merge integration
- Regression cases (known corruption patterns)
"""
import ast
import sys
import tempfile
from pathlib import Path
from textwrap import dedent

import pytest

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.lead_contractor.ast_merge import (
    ParsedPythonFile,
    MergeResult,
    parse_python_file,
    merge_parsed_files,
    merge_class_definitions,
    deduplicate_imports,
    topological_sort_classes,
    detect_class_dependencies,
    merge_python_files,
    merge_from_strings,
)


class TestParseFile:
    """Tests for parse_python_file function."""

    def test_parse_module_docstring(self, tmp_path):
        """Test extraction of module docstring."""
        source = tmp_path / "test.py"
        source.write_text('"""This is the module docstring."""\n\nclass Foo:\n    pass\n')

        result = parse_python_file(source)
        assert result.module_docstring == "This is the module docstring."

    def test_parse_multiline_docstring(self, tmp_path):
        """Test extraction of multi-line docstring."""
        source = tmp_path / "test.py"
        source.write_text('"""\nMulti-line\ndocstring\n"""\n\nclass Foo:\n    pass\n')

        result = parse_python_file(source)
        assert "Multi-line" in result.module_docstring

    def test_parse_future_imports(self, tmp_path):
        """Test extraction of __future__ imports."""
        source = tmp_path / "test.py"
        source.write_text(
            'from __future__ import annotations\n'
            'from __future__ import division\n'
            'import os\n'
        )

        result = parse_python_file(source)
        assert len(result.future_imports) == 2
        assert result.future_imports[0].module == '__future__'

    def test_parse_regular_imports(self, tmp_path):
        """Test extraction of regular imports."""
        source = tmp_path / "test.py"
        source.write_text(
            'import os\n'
            'import sys\n'
            'from typing import Optional\n'
            'from pathlib import Path\n'
        )

        result = parse_python_file(source)
        assert len(result.regular_imports) == 4

    def test_parse_type_checking_block(self, tmp_path):
        """Test extraction of TYPE_CHECKING blocks."""
        source = tmp_path / "test.py"
        source.write_text(
            'from typing import TYPE_CHECKING\n'
            'if TYPE_CHECKING:\n'
            '    from mymodule import Foo\n'
        )

        result = parse_python_file(source)
        assert len(result.type_checking_imports) == 1

    def test_parse_classes(self, tmp_path):
        """Test extraction of class definitions."""
        source = tmp_path / "test.py"
        source.write_text(
            'class Foo:\n'
            '    pass\n'
            '\n'
            'class Bar:\n'
            '    def method(self):\n'
            '        pass\n'
        )

        result = parse_python_file(source)
        assert 'Foo' in result.classes
        assert 'Bar' in result.classes

    def test_parse_functions(self, tmp_path):
        """Test extraction of function definitions."""
        source = tmp_path / "test.py"
        source.write_text(
            'def foo():\n'
            '    pass\n'
            '\n'
            'def bar(x: int) -> str:\n'
            '    return str(x)\n'
        )

        result = parse_python_file(source)
        assert 'foo' in result.functions
        assert 'bar' in result.functions

    def test_parse_all_export(self, tmp_path):
        """Test extraction of __all__ export list."""
        source = tmp_path / "test.py"
        source.write_text(
            '__all__ = ["Foo", "Bar", "baz"]\n'
            '\n'
            'class Foo:\n'
            '    pass\n'
        )

        result = parse_python_file(source)
        assert result.all_export == ["Foo", "Bar", "baz"]

    def test_parse_decorated_class(self, tmp_path):
        """Test that decorators are preserved with classes."""
        source = tmp_path / "test.py"
        source.write_text(
            'from dataclasses import dataclass\n'
            '\n'
            '@dataclass\n'
            'class Foo:\n'
            '    x: int\n'
            '    y: str\n'
        )

        result = parse_python_file(source)
        assert 'Foo' in result.classes
        foo_class = result.classes['Foo']
        assert len(foo_class.decorator_list) == 1
        assert foo_class.decorator_list[0].id == 'dataclass'

    def test_parse_syntax_error(self, tmp_path):
        """Test that syntax errors are raised."""
        source = tmp_path / "test.py"
        source.write_text('class Foo\n    pass\n')  # Missing colon

        with pytest.raises(SyntaxError):
            parse_python_file(source)

    def test_parse_markdown_cleanup(self, tmp_path):
        """Test that markdown code blocks are cleaned."""
        source = tmp_path / "test.py"
        source.write_text(
            '```python\n'
            'class Foo:\n'
            '    pass\n'
            '```\n'
        )

        result = parse_python_file(source)
        assert 'Foo' in result.classes


class TestClassDependencies:
    """Tests for detect_class_dependencies function."""

    def test_detect_inheritance(self):
        """Test detection of inheritance dependencies."""
        code = dedent('''
            class Base:
                pass

            class Child(Base):
                pass
        ''')
        tree = ast.parse(code)
        classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}

        deps = detect_class_dependencies(classes['Child'], set(classes.keys()))
        assert deps == {'Base'}

    def test_detect_type_annotation(self):
        """Test detection of type annotation dependencies."""
        code = dedent('''
            class Foo:
                pass

            class Bar:
                foo: Foo
        ''')
        tree = ast.parse(code)
        classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}

        deps = detect_class_dependencies(classes['Bar'], set(classes.keys()))
        assert deps == {'Foo'}

    def test_detect_method_annotation(self):
        """Test detection of method argument/return type dependencies."""
        code = dedent('''
            class Foo:
                pass

            class Bar:
                def process(self, foo: Foo) -> Foo:
                    return foo
        ''')
        tree = ast.parse(code)
        classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}

        deps = detect_class_dependencies(classes['Bar'], set(classes.keys()))
        assert deps == {'Foo'}

    def test_no_self_reference(self):
        """Test that self-reference is not included."""
        code = dedent('''
            class Foo:
                def clone(self) -> Foo:
                    pass
        ''')
        tree = ast.parse(code)
        classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}

        deps = detect_class_dependencies(classes['Foo'], set(classes.keys()))
        assert deps == set()

    def test_detect_generic_type(self):
        """Test detection of dependencies in generic types."""
        code = dedent('''
            from typing import List

            class Item:
                pass

            class Container:
                items: List[Item]
        ''')
        tree = ast.parse(code)
        classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}

        deps = detect_class_dependencies(classes['Container'], set(classes.keys()))
        assert deps == {'Item'}


class TestTopologicalSort:
    """Tests for topological_sort_classes function."""

    def test_simple_ordering(self):
        """Test simple dependency ordering."""
        code = dedent('''
            class Base:
                pass

            class Child(Base):
                pass
        ''')
        tree = ast.parse(code)
        classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}

        sorted_names = topological_sort_classes(classes)
        assert sorted_names.index('Base') < sorted_names.index('Child')

    def test_chain_ordering(self):
        """Test chain of dependencies."""
        code = dedent('''
            class A:
                pass

            class B(A):
                pass

            class C(B):
                pass
        ''')
        tree = ast.parse(code)
        classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}

        sorted_names = topological_sort_classes(classes)
        assert sorted_names.index('A') < sorted_names.index('B')
        assert sorted_names.index('B') < sorted_names.index('C')

    def test_multiple_bases(self):
        """Test class with multiple base classes."""
        code = dedent('''
            class A:
                pass

            class B:
                pass

            class C(A, B):
                pass
        ''')
        tree = ast.parse(code)
        classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}

        sorted_names = topological_sort_classes(classes)
        assert sorted_names.index('A') < sorted_names.index('C')
        assert sorted_names.index('B') < sorted_names.index('C')

    def test_circular_dependency(self):
        """Test handling of circular dependencies."""
        code = dedent('''
            class A:
                b: "B"  # Forward reference

            class B:
                a: "A"  # Forward reference
        ''')
        tree = ast.parse(code)
        classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}

        # Should not raise, should include both classes
        sorted_names = topological_sort_classes(classes)
        assert set(sorted_names) == {'A', 'B'}

    def test_no_dependencies(self):
        """Test classes with no dependencies."""
        code = dedent('''
            class A:
                pass

            class B:
                pass

            class C:
                pass
        ''')
        tree = ast.parse(code)
        classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}

        sorted_names = topological_sort_classes(classes)
        # All should be present, order is alphabetical for no deps
        assert set(sorted_names) == {'A', 'B', 'C'}


class TestClassMerging:
    """Tests for merge_class_definitions function."""

    def test_add_new_method(self):
        """Test adding a new method from second class."""
        code1 = dedent('''
            class Foo:
                def method1(self):
                    pass
        ''')
        code2 = dedent('''
            class Foo:
                def method2(self):
                    pass
        ''')
        tree1 = ast.parse(code1)
        tree2 = ast.parse(code2)
        cls1 = tree1.body[0]
        cls2 = tree2.body[0]

        merged, warnings = merge_class_definitions(cls1, cls2)

        method_names = [
            node.name for node in merged.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        assert 'method1' in method_names
        assert 'method2' in method_names
        assert len(warnings) == 0

    def test_duplicate_method_warning(self):
        """Test warning for duplicate methods."""
        code1 = dedent('''
            class Foo:
                def method(self):
                    return 1
        ''')
        code2 = dedent('''
            class Foo:
                def method(self):
                    return 2
        ''')
        tree1 = ast.parse(code1)
        tree2 = ast.parse(code2)
        cls1 = tree1.body[0]
        cls2 = tree2.body[0]

        merged, warnings = merge_class_definitions(cls1, cls2)

        # Should have exactly one method (the existing one)
        method_names = [
            node.name for node in merged.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        assert method_names.count('method') == 1
        assert len(warnings) == 1
        assert 'Duplicate method' in warnings[0]

    def test_preserve_decorators(self):
        """Test that decorators are preserved."""
        code1 = dedent('''
            from dataclasses import dataclass

            @dataclass
            class Foo:
                x: int
        ''')
        code2 = dedent('''
            class Foo:
                y: str
        ''')
        tree1 = ast.parse(code1)
        tree2 = ast.parse(code2)
        cls1 = [n for n in tree1.body if isinstance(n, ast.ClassDef)][0]
        cls2 = tree2.body[0]

        merged, warnings = merge_class_definitions(cls1, cls2)

        # Decorator should be preserved
        assert len(merged.decorator_list) == 1

    def test_add_new_attribute(self):
        """Test adding a new attribute from second class."""
        code1 = dedent('''
            class Foo:
                x: int
        ''')
        code2 = dedent('''
            class Foo:
                y: str
        ''')
        tree1 = ast.parse(code1)
        tree2 = ast.parse(code2)
        cls1 = tree1.body[0]
        cls2 = tree2.body[0]

        merged, warnings = merge_class_definitions(cls1, cls2)

        # Should have both attributes
        ann_assigns = [
            node for node in merged.body
            if isinstance(node, ast.AnnAssign)
        ]
        names = [node.target.id for node in ann_assigns]
        assert 'x' in names
        assert 'y' in names


class TestImportDeduplication:
    """Tests for deduplicate_imports function."""

    def test_deduplicate_simple_imports(self):
        """Test deduplication of simple imports."""
        code = dedent('''
            import os
            import sys
            import os
        ''')
        tree = ast.parse(code)
        imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]

        deduped = deduplicate_imports(imports)
        import_names = []
        for node in deduped:
            if isinstance(node, ast.Import):
                import_names.extend(alias.name for alias in node.names)

        assert import_names.count('os') == 1
        assert import_names.count('sys') == 1

    def test_merge_from_imports(self):
        """Test merging from X import a, b style imports."""
        code = dedent('''
            from typing import Optional
            from typing import List
            from typing import Dict
        ''')
        tree = ast.parse(code)
        imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]

        deduped = deduplicate_imports(imports)

        # Should be merged into single from typing import ...
        assert len(deduped) == 1
        assert deduped[0].module == 'typing'
        names = [alias.name for alias in deduped[0].names]
        assert 'Optional' in names
        assert 'List' in names
        assert 'Dict' in names

    def test_preserve_order(self):
        """Test that import order is preserved."""
        code = dedent('''
            import sys
            import os
            from pathlib import Path
        ''')
        tree = ast.parse(code)
        imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]

        deduped = deduplicate_imports(imports)

        # Simple imports should come first (in order), then from imports
        assert len(deduped) == 3

    def test_handle_aliases(self):
        """Test handling of import aliases."""
        code = dedent('''
            import numpy as np
            import numpy as np
        ''')
        tree = ast.parse(code)
        imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]

        deduped = deduplicate_imports(imports)

        assert len(deduped) == 1
        assert deduped[0].names[0].asname == 'np'


class TestFullMerge:
    """Tests for merge_parsed_files function."""

    def test_merge_two_files(self, tmp_path):
        """Test merging two simple files."""
        file1 = tmp_path / "file1.py"
        file1.write_text(dedent('''
            """Module 1 docstring."""
            import os

            class Foo:
                def method1(self):
                    pass
        '''))

        file2 = tmp_path / "file2.py"
        file2.write_text(dedent('''
            import sys

            class Bar:
                def method2(self):
                    pass
        '''))

        parsed1 = parse_python_file(file1)
        parsed2 = parse_python_file(file2)

        result = merge_parsed_files([parsed1, parsed2])

        # Check content
        assert 'class Foo' in result.content
        assert 'class Bar' in result.content
        assert 'import os' in result.content or 'os' in result.content
        assert 'import sys' in result.content or 'sys' in result.content

    def test_merge_preserves_future_imports(self, tmp_path):
        """Test that __future__ imports are preserved at the top."""
        file1 = tmp_path / "file1.py"
        file1.write_text(dedent('''
            from __future__ import annotations
            import os

            class Foo:
                pass
        '''))

        file2 = tmp_path / "file2.py"
        file2.write_text(dedent('''
            import sys

            class Bar:
                pass
        '''))

        parsed1 = parse_python_file(file1)
        parsed2 = parse_python_file(file2)

        result = merge_parsed_files([parsed1, parsed2])

        # __future__ import should be near the top
        lines = result.content.split('\n')
        future_line = None
        os_line = None
        for i, line in enumerate(lines):
            if 'from __future__' in line:
                future_line = i
            if 'import os' in line or "'os'" in line:
                os_line = i

        if future_line is not None and os_line is not None:
            assert future_line < os_line

    def test_merge_generates_all(self, tmp_path):
        """Test that __all__ is generated."""
        file1 = tmp_path / "file1.py"
        file1.write_text(dedent('''
            class Foo:
                pass

            def helper():
                pass
        '''))

        parsed1 = parse_python_file(file1)
        result = merge_parsed_files([parsed1])

        assert '__all__' in result.content

    def test_merge_from_strings(self):
        """Test the convenience function for merging from strings."""
        source1 = dedent('''
            class Foo:
                def method1(self):
                    pass
        ''')
        source2 = dedent('''
            class Bar:
                def method2(self):
                    pass
        ''')

        result = merge_from_strings([source1, source2])

        assert 'class Foo' in result.content
        assert 'class Bar' in result.content


class TestRegressionCases:
    """Tests for known corruption patterns from the broken merge."""

    def test_decorator_not_separated(self, tmp_path):
        """
        Regression test: decorators must stay attached to their class.

        The old merge would sometimes separate @dataclass from the class definition.
        """
        file1 = tmp_path / "file1.py"
        file1.write_text(dedent('''
            from dataclasses import dataclass

            @dataclass
            class MessageRole:
                value: str

            @dataclass
            class Message:
                role: MessageRole
                content: str
        '''))

        parsed = parse_python_file(file1)
        result = merge_parsed_files([parsed])

        # Verify decorators are attached
        tree = ast.parse(result.content)
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                if node.name in ('MessageRole', 'Message'):
                    assert len(node.decorator_list) == 1, \
                        f"Class {node.name} lost its decorator"

    def test_future_import_first(self, tmp_path):
        """
        Regression test: __future__ imports must come first.

        The old merge would sometimes put regular imports before __future__.
        """
        file1 = tmp_path / "file1.py"
        file1.write_text(dedent('''
            from __future__ import annotations
            import os
            from typing import Optional

            class Foo:
                pass
        '''))

        parsed = parse_python_file(file1)
        result = merge_parsed_files([parsed])

        # Verify __future__ is first import
        tree = ast.parse(result.content)
        first_import = None
        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                first_import = node
                break

        assert first_import is not None
        if isinstance(first_import, ast.ImportFrom):
            assert first_import.module == '__future__', \
                "__future__ import not first"

    def test_class_dependency_order(self, tmp_path):
        """
        Regression test: classes must be ordered by dependency.

        The old merge would put Message before MessageRole, causing NameError.
        """
        file1 = tmp_path / "file1.py"
        file1.write_text(dedent('''
            from dataclasses import dataclass

            @dataclass
            class MessageRole:
                value: str

            @dataclass
            class Message:
                role: MessageRole
        '''))

        parsed = parse_python_file(file1)
        result = merge_parsed_files([parsed])

        # Verify order
        tree = ast.parse(result.content)
        class_order = [
            node.name for node in tree.body
            if isinstance(node, ast.ClassDef)
        ]

        if 'MessageRole' in class_order and 'Message' in class_order:
            assert class_order.index('MessageRole') < class_order.index('Message'), \
                "MessageRole must come before Message"

    def test_no_example_code_at_module_level(self, tmp_path):
        """
        Regression test: example code should not be included at module level.

        Generated files often have example code that shouldn't be merged in.
        """
        file1 = tmp_path / "file1.py"
        file1.write_text(dedent('''
            class Foo:
                pass

            if __name__ == "__main__":
                foo = Foo()
                print(foo)
        '''))

        parsed = parse_python_file(file1)
        result = merge_parsed_files([parsed])

        # The __main__ block should be in other_statements
        # but won't execute when imported

    def test_multiline_string_not_broken(self, tmp_path):
        """
        Regression test: multiline strings must not be broken.

        The old merge would sometimes split docstrings incorrectly.
        """
        file1 = tmp_path / "file1.py"
        file1.write_text(dedent('''
            class Foo:
                """
                This is a multiline
                docstring that should
                stay intact.
                """
                def method(self):
                    pass
        '''))

        parsed = parse_python_file(file1)
        result = merge_parsed_files([parsed])

        # Should be valid Python
        try:
            ast.parse(result.content)
        except SyntaxError as e:
            pytest.fail(f"Merged content has syntax error: {e}")

    def test_parts_file_merge(self, tmp_path):
        """
        Regression test: simulate the parts.py corruption scenario.

        This is the exact pattern that caused the original bug.
        """
        file1 = tmp_path / "parts1.py"
        file1.write_text(dedent('''
            """Data models for agent communication."""
            from __future__ import annotations
            from dataclasses import dataclass
            from enum import Enum
            from typing import List, Optional

            class MessageRole(str, Enum):
                USER = "user"
                ASSISTANT = "assistant"

            @dataclass
            class Message:
                role: MessageRole
                content: str
        '''))

        file2 = tmp_path / "parts2.py"
        file2.write_text(dedent('''
            """Additional models."""
            from dataclasses import dataclass
            from typing import Optional

            @dataclass
            class Artifact:
                name: str
                data: bytes
        '''))

        parsed1 = parse_python_file(file1)
        parsed2 = parse_python_file(file2)
        result = merge_parsed_files([parsed1, parsed2])

        # Must be valid Python
        try:
            tree = ast.parse(result.content)
        except SyntaxError as e:
            pytest.fail(f"Merged parts file has syntax error: {e}")

        # All classes must be present with decorators
        classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}
        assert 'MessageRole' in classes
        assert 'Message' in classes
        assert 'Artifact' in classes

        # @dataclass decorators must be preserved
        for name in ['Message', 'Artifact']:
            cls = classes[name]
            decorator_names = [
                d.id if isinstance(d, ast.Name) else str(d)
                for d in cls.decorator_list
            ]
            assert 'dataclass' in decorator_names, \
                f"Class {name} lost @dataclass decorator"


class TestIntegration:
    """Integration tests using merge_python_files."""

    def test_merge_with_existing_target(self, tmp_path):
        """Test merging source files with an existing target."""
        target = tmp_path / "target.py"
        target.write_text(dedent('''
            class Existing:
                def old_method(self):
                    pass
        '''))

        source = tmp_path / "source.py"
        source.write_text(dedent('''
            class New:
                def new_method(self):
                    pass
        '''))

        result = merge_python_files(target, [source], include_target=True)

        assert 'class Existing' in result.content
        assert 'class New' in result.content

    def test_merge_without_target(self, tmp_path):
        """Test merging when target doesn't exist."""
        target = tmp_path / "target.py"  # Does not exist

        source = tmp_path / "source.py"
        source.write_text(dedent('''
            class New:
                pass
        '''))

        result = merge_python_files(target, [source], include_target=True)

        assert 'class New' in result.content

    def test_skip_invalid_source(self, tmp_path):
        """Test that invalid source files are skipped with warning."""
        source1 = tmp_path / "valid.py"
        source1.write_text('class Valid:\n    pass\n')

        source2 = tmp_path / "invalid.py"
        source2.write_text('class Invalid\n    pass\n')  # Missing colon

        result = merge_python_files(
            tmp_path / "target.py",
            [source1, source2],
            include_target=False
        )

        assert 'class Valid' in result.content
        assert any('syntax error' in w.lower() for w in result.warnings)
