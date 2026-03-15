"""Python source code scanner — AST-based detection of ORM models, routes, and components."""

from __future__ import annotations

import ast
from pathlib import Path

from cartographer.discovery.plugins.base import ScannerPlugin
from cartographer.models import (
    Confidence,
    ComponentType,
    DiscoveredComponent,
    DiscoveredField,
    DiscoveredModel,
    DiscoveredRoute,
    DiscoveryResult,
)

# ORM base classes and their corresponding ORM name
SQLALCHEMY_BASES = {"Base", "DeclarativeBase", "db.Model", "Model"}
DJANGO_BASES = {"models.Model", "Model"}
PEEWEE_BASES = {"Model", "BaseModel"}
TORTOISE_BASES = {"Model"}
PYDANTIC_BASES = {"BaseModel", "BaseSettings"}

# Route decorator patterns
FLASK_DECORATORS = {"route", "get", "post", "put", "delete", "patch"}
FASTAPI_DECORATORS = {"get", "post", "put", "delete", "patch", "options", "head", "trace"}

# SQLAlchemy column type mapping
SA_COLUMN_TYPES = {
    "String": "string",
    "Text": "text",
    "Integer": "integer",
    "BigInteger": "bigint",
    "Float": "float",
    "Boolean": "boolean",
    "DateTime": "datetime",
    "Date": "date",
    "Time": "time",
    "JSON": "json",
    "LargeBinary": "binary",
    "Enum": "enum",
    "UUID": "uuid",
    "Numeric": "decimal",
}


class PythonScanner(ScannerPlugin):
    def scan(self, file_path: Path, content: str) -> DiscoveryResult:
        result = DiscoveryResult()
        try:
            tree = ast.parse(content, filename=str(file_path))
        except SyntaxError:
            return result

        imports = _collect_imports(tree)
        orm_hint = _detect_orm(imports)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                self._check_class(node, file_path, orm_hint, imports, result)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._check_route(node, file_path, imports, result)

        return result

    def _check_class(
        self,
        node: ast.ClassDef,
        file_path: Path,
        orm_hint: str | None,
        imports: dict[str, str],
        result: DiscoveryResult,
    ) -> None:
        bases = _get_base_names(node)

        # Check for ORM model
        orm, confidence = _match_orm_base(bases, orm_hint, imports)
        if orm:
            fields = _extract_fields(node, orm)
            model = DiscoveredModel(
                name=node.name,
                source_file=str(file_path),
                line=node.lineno,
                orm=orm,
                fields=fields,
                confidence=confidence,
            )
            result.models.append(model)

        # Every class is a potential component
        public_methods = [
            n.name
            for n in ast.iter_child_nodes(node)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            and not n.name.startswith("_")
        ]
        if public_methods:
            has_init_deps = _has_dependency_injection(node)
            component = DiscoveredComponent(
                name=node.name,
                source_file=str(file_path),
                line=node.lineno,
                type=ComponentType.SERVICE if has_init_deps else ComponentType.LIBRARY,
                public_methods=public_methods,
                dependencies=_extract_init_deps(node),
                confidence=Confidence.MEDIUM,
                note="Class with public methods detected",
            )
            result.components.append(component)

    def _check_route(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        file_path: Path,
        imports: dict[str, str],
        result: DiscoveryResult,
    ) -> None:
        for decorator in node.decorator_list:
            route_info = _parse_route_decorator(decorator, imports)
            if route_info:
                path, method, framework = route_info
                result.routes.append(
                    DiscoveredRoute(
                        path=path,
                        method=method,
                        handler=node.name,
                        source_file=str(file_path),
                        line=node.lineno,
                        framework=framework,
                        confidence=Confidence.HIGH,
                    )
                )


def _collect_imports(tree: ast.Module) -> dict[str, str]:
    """Map imported names to their module source."""
    imports: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname or alias.name
                imports[name] = alias.name
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                name = alias.asname or alias.name
                imports[name] = f"{module}.{alias.name}"
    return imports


def _detect_orm(imports: dict[str, str]) -> str | None:
    """Detect which ORM is imported."""
    for source in imports.values():
        if "sqlalchemy" in source.lower():
            return "sqlalchemy"
        if "django" in source.lower() and "models" in source.lower():
            return "django"
        if "peewee" in source.lower():
            return "peewee"
        if "tortoise" in source.lower():
            return "tortoise"
        if "pydantic" in source.lower():
            return "pydantic"
    return None


def _get_base_names(node: ast.ClassDef) -> list[str]:
    """Extract base class names as strings."""
    names = []
    for base in node.bases:
        if isinstance(base, ast.Name):
            names.append(base.id)
        elif isinstance(base, ast.Attribute):
            names.append(f"{_attr_to_str(base)}")
    return names


def _attr_to_str(node: ast.Attribute) -> str:
    if isinstance(node.value, ast.Name):
        return f"{node.value.id}.{node.attr}"
    if isinstance(node.value, ast.Attribute):
        return f"{_attr_to_str(node.value)}.{node.attr}"
    return node.attr


def _match_orm_base(
    bases: list[str], orm_hint: str | None, imports: dict[str, str]
) -> tuple[str | None, Confidence]:
    """Check if any base matches known ORM patterns."""
    for base in bases:
        if base in SQLALCHEMY_BASES or (orm_hint == "sqlalchemy" and base in {"Base", "Model"}):
            return "sqlalchemy", Confidence.HIGH
        if base == "models.Model" or (orm_hint == "django" and base == "Model"):
            return "django", Confidence.HIGH
        if orm_hint == "peewee" and base in PEEWEE_BASES:
            return "peewee", Confidence.HIGH
        if orm_hint == "tortoise" and base in TORTOISE_BASES:
            return "tortoise", Confidence.HIGH
        if base in PYDANTIC_BASES or (orm_hint == "pydantic" and base == "BaseModel"):
            return "pydantic", Confidence.MEDIUM
    return None, Confidence.LOW


def _extract_fields(node: ast.ClassDef, orm: str) -> list[DiscoveredField]:
    """Extract field definitions from an ORM model class."""
    fields: list[DiscoveredField] = []
    for item in ast.iter_child_nodes(node):
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            field_name = item.target.id
            field_type = _annotation_to_type(item.annotation)
            fields.append(
                DiscoveredField(
                    name=field_name,
                    type=field_type,
                    confidence=Confidence.HIGH,
                )
            )
        elif isinstance(item, ast.Assign):
            for target in item.targets:
                if isinstance(target, ast.Name) and not target.id.startswith("_"):
                    col_type = _extract_column_type(item.value, orm)
                    if col_type:
                        fields.append(
                            DiscoveredField(
                                name=target.id,
                                type=col_type,
                                confidence=Confidence.HIGH,
                            )
                        )
    return fields


def _annotation_to_type(ann: ast.expr) -> str:
    if isinstance(ann, ast.Name):
        return ann.id.lower()
    if isinstance(ann, ast.Attribute):
        return ann.attr.lower()
    if isinstance(ann, ast.Subscript):
        if isinstance(ann.value, ast.Name):
            return ann.value.id.lower()
    return "unknown"


def _extract_column_type(value: ast.expr, orm: str) -> str | None:
    """Extract column type from SQLAlchemy Column() or mapped_column() calls."""
    if not isinstance(value, ast.Call):
        return None
    func_name = ""
    if isinstance(value.func, ast.Name):
        func_name = value.func.id
    elif isinstance(value.func, ast.Attribute):
        func_name = value.func.attr

    if func_name in ("Column", "mapped_column", "Field"):
        for arg in value.args:
            if isinstance(arg, ast.Name) and arg.id in SA_COLUMN_TYPES:
                return SA_COLUMN_TYPES[arg.id]
            if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name):
                if arg.func.id in SA_COLUMN_TYPES:
                    return SA_COLUMN_TYPES[arg.func.id]
        return "unknown"
    return None


def _has_dependency_injection(node: ast.ClassDef) -> bool:
    """Check if __init__ accepts injected dependencies."""
    for item in ast.iter_child_nodes(node):
        if isinstance(item, ast.FunctionDef) and item.name == "__init__":
            # More than just self
            return len(item.args.args) > 1
    return False


def _extract_init_deps(node: ast.ClassDef) -> list[str]:
    """Extract parameter names from __init__ (excluding self)."""
    for item in ast.iter_child_nodes(node):
        if isinstance(item, ast.FunctionDef) and item.name == "__init__":
            return [
                arg.arg
                for arg in item.args.args
                if arg.arg != "self"
            ]
    return []


def _parse_route_decorator(
    decorator: ast.expr, imports: dict[str, str]
) -> tuple[str, str, str] | None:
    """Parse a route decorator to extract (path, method, framework)."""
    if isinstance(decorator, ast.Call):
        func = decorator.func
        if isinstance(func, ast.Attribute):
            method = func.attr.lower()
            if method in FLASK_DECORATORS or method in FASTAPI_DECORATORS:
                path = _first_string_arg(decorator)
                framework = _infer_framework(func, imports)
                http_method = method.upper() if method != "route" else "ANY"
                return path or "/", http_method, framework
        elif isinstance(func, ast.Name):
            if func.id in ("app_route", "router"):
                path = _first_string_arg(decorator)
                return path or "/", "ANY", "unknown"
    return None


def _first_string_arg(call: ast.Call) -> str | None:
    for arg in call.args:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            return arg.value
    return None


def _infer_framework(func: ast.Attribute, imports: dict[str, str]) -> str:
    if isinstance(func.value, ast.Name):
        source = imports.get(func.value.id, "")
        if "fastapi" in source.lower():
            return "fastapi"
        if "flask" in source.lower():
            return "flask"
        # Heuristic: "app" is commonly Flask, "router" is commonly FastAPI
        if func.value.id == "router":
            return "fastapi"
        if func.value.id == "app":
            return "flask"
    return "unknown"
