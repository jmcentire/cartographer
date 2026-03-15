"""Source code scanner orchestrator."""

from __future__ import annotations

from pathlib import Path

from cartographer.config.loader import CartographerConfig
from cartographer.discovery.plugins.base import ScannerPlugin
from cartographer.discovery.plugins.python_scanner import PythonScanner
from cartographer.discovery.plugins.typescript_scanner import TypeScriptScanner
from cartographer.discovery.plugins.javascript_scanner import JavaScriptScanner
from cartographer.discovery.plugins.ruby_scanner import RubyScanner
from cartographer.discovery.plugins.go_scanner import GoScanner
from cartographer.discovery.plugins.java_scanner import JavaScanner
from cartographer.discovery.pact_keys import PactKeyScanner
from cartographer.discovery.env_vars import EnvVarScanner
from cartographer.discovery.sensitive_fields import SensitiveFieldScanner
from cartographer.models import DiscoveryResult


LANGUAGE_PLUGINS: dict[str, type[ScannerPlugin]] = {
    "python": PythonScanner,
    "typescript": TypeScriptScanner,
    "javascript": JavaScriptScanner,
    "ruby": RubyScanner,
    "go": GoScanner,
    "java": JavaScanner,
}

LANGUAGE_EXTENSIONS: dict[str, list[str]] = {
    "python": [".py"],
    "typescript": [".ts", ".tsx"],
    "javascript": [".js", ".jsx", ".mjs", ".cjs"],
    "ruby": [".rb"],
    "go": [".go"],
    "java": [".java"],
}


def _collect_files(
    dirs: list[str],
    extensions: list[str],
    exclude: list[str],
    base: Path,
) -> list[Path]:
    """Collect all files matching extensions under the given directories."""
    files: list[Path] = []
    for d in dirs:
        root = base / d
        if not root.exists():
            continue
        for ext in extensions:
            for f in root.rglob(f"*{ext}"):
                if any(part in exclude for part in f.parts):
                    continue
                files.append(f)
    return sorted(files)


def scan_source(config: CartographerConfig, base_dir: Path) -> DiscoveryResult:
    """Run all applicable source scanners against the configured directories."""
    result = DiscoveryResult()
    source = config.targets.source

    for lang in source.languages:
        plugin_cls = LANGUAGE_PLUGINS.get(lang)
        extensions = LANGUAGE_EXTENSIONS.get(lang)
        if plugin_cls is None or extensions is None:
            continue

        files = _collect_files(source.dirs, extensions, source.exclude, base_dir)
        if not files:
            continue

        plugin = plugin_cls()
        for f in files:
            try:
                content = f.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            file_result = plugin.scan(f, content)
            result.models.extend(file_result.models)
            result.routes.extend(file_result.routes)
            result.components.extend(file_result.components)

    # Cross-language scanners
    all_files: list[Path] = []
    for lang in source.languages:
        extensions = LANGUAGE_EXTENSIONS.get(lang, [])
        all_files.extend(
            _collect_files(source.dirs, extensions, source.exclude, base_dir)
        )

    pact_scanner = PactKeyScanner(config.compatibility.pact_key_format)
    env_scanner = EnvVarScanner()
    sensitive_scanner = SensitiveFieldScanner()

    for f in all_files:
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        result.pact_keys.extend(pact_scanner.scan(f, content))
        result.env_vars.extend(env_scanner.scan(f, content))
        result.sensitive_fields.extend(sensitive_scanner.scan(f, content))

    return result
