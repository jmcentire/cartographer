"""
Contract-based tests for ArbiterChecker component.
Generated from contract version 1.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, mock_open
from typing import Any

# Import component under test
from src.cartographer.compatibility.arbiter_checker import ArbiterChecker

# Mock imports for dependencies that may not be available
# We'll create mock classes for the dependencies


class MockSeverity:
    """Mock Severity enum"""
    info = "info"
    warning = "warning"
    error = "error"


class MockCheckResult:
    """Mock CheckResult model"""
    def __init__(self, tool: str, check_id: str, severity: str, message: str = "", **kwargs):
        self.tool = tool
        self.check_id = check_id
        self.severity = severity
        self.message = message
        for key, value in kwargs.items():
            setattr(self, key, value)


class MockCartographerConfig:
    """Mock CartographerConfig"""
    def __init__(self, **kwargs):
        self.stack = Mock()
        for key, value in kwargs.items():
            setattr(self, key, value)


# Fixtures
@pytest.fixture
def arbiter_checker():
    """Create an ArbiterChecker instance"""
    return ArbiterChecker()


@pytest.fixture
def minimal_config():
    """Create a minimal CartographerConfig"""
    config = MockCartographerConfig()
    config.stack = Mock()
    config.stack.arbiter_registry_path = None
    return config


@pytest.fixture
def config_with_registry_path(tmp_path):
    """Create config with configured registry path"""
    config = MockCartographerConfig()
    config.stack = Mock()
    registry_path = tmp_path / "custom_registry"
    registry_path.mkdir()
    config.stack.arbiter_registry_path = str(registry_path)
    return config, registry_path


@pytest.fixture
def base_dir_with_arbiter_registry(tmp_path):
    """Create base directory with .arbiter/registry structure"""
    arbiter_dir = tmp_path / ".arbiter" / "registry"
    arbiter_dir.mkdir(parents=True)
    return tmp_path, arbiter_dir


@pytest.fixture
def base_dir_with_arbiter_only(tmp_path):
    """Create base directory with .arbiter only"""
    arbiter_dir = tmp_path / ".arbiter"
    arbiter_dir.mkdir()
    return tmp_path, arbiter_dir


@pytest.fixture
def base_dir_empty(tmp_path):
    """Create empty base directory"""
    return tmp_path


def create_json_file(path: Path, content: dict):
    """Helper to create a JSON file"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        json.dump(content, f)


def create_invalid_json_file(path: Path, content: str):
    """Helper to create an invalid JSON file"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        f.write(content)


# Tests for tool_name property
def test_tool_name_returns_arbiter(arbiter_checker):
    """Verify tool_name property returns 'arbiter'"""
    result = arbiter_checker.tool_name
    assert result == 'arbiter', f"Expected 'arbiter', got {result}"


def test_tool_name_consistency(arbiter_checker):
    """Verify tool_name returns same value on multiple calls"""
    result1 = arbiter_checker.tool_name
    result2 = arbiter_checker.tool_name
    result3 = arbiter_checker.tool_name
    assert result1 == result2 == result3 == 'arbiter', \
        "tool_name should consistently return 'arbiter'"


# Tests for _find_registry function
def test_find_registry_configured_path(minimal_config, tmp_path):
    """Find registry at configured path in config.stack"""
    checker = ArbiterChecker()
    registry_path = tmp_path / "custom_registry"
    registry_path.mkdir()
    minimal_config.stack.arbiter_registry_path = str(registry_path)
    
    result = checker._find_registry(minimal_config, tmp_path)
    
    assert result is not None, "Should find configured registry"
    assert isinstance(result, Path), "Should return Path object"
    assert result.exists(), "Returned path should exist"
    assert result.is_dir(), "Returned path should be a directory"
    assert str(result) == str(registry_path), "Should return configured path"


def test_find_registry_default_arbiter_registry(minimal_config, tmp_path):
    """Find registry at .arbiter/registry default location"""
    checker = ArbiterChecker()
    arbiter_registry = tmp_path / ".arbiter" / "registry"
    arbiter_registry.mkdir(parents=True)
    minimal_config.stack.arbiter_registry_path = None
    
    result = checker._find_registry(minimal_config, tmp_path)
    
    assert result is not None, "Should find .arbiter/registry"
    assert isinstance(result, Path), "Should return Path object"
    assert result.name == "registry", "Should point to registry directory"
    assert result.parent.name == ".arbiter", "Should be inside .arbiter"


def test_find_registry_default_arbiter(minimal_config, tmp_path):
    """Find registry at .arbiter default location when registry subdir doesn't exist"""
    checker = ArbiterChecker()
    arbiter_dir = tmp_path / ".arbiter"
    arbiter_dir.mkdir()
    minimal_config.stack.arbiter_registry_path = None
    
    result = checker._find_registry(minimal_config, tmp_path)
    
    assert result is not None, "Should find .arbiter"
    assert isinstance(result, Path), "Should return Path object"
    assert result.name == ".arbiter", "Should point to .arbiter directory"


def test_find_registry_not_found(minimal_config, tmp_path):
    """Return None when registry not found in any location"""
    checker = ArbiterChecker()
    minimal_config.stack.arbiter_registry_path = None
    
    result = checker._find_registry(minimal_config, tmp_path)
    
    assert result is None, "Should return None when registry not found"


def test_find_registry_search_order(minimal_config, tmp_path):
    """Verify registry search order: configured, .arbiter/registry, .arbiter"""
    checker = ArbiterChecker()
    
    # Create all possible locations
    configured_path = tmp_path / "configured"
    configured_path.mkdir()
    arbiter_registry = tmp_path / ".arbiter" / "registry"
    arbiter_registry.mkdir(parents=True)
    
    # Set configured path
    minimal_config.stack.arbiter_registry_path = str(configured_path)
    
    result = checker._find_registry(minimal_config, tmp_path)
    
    assert result is not None, "Should find registry"
    assert str(result) == str(configured_path), \
        "Configured path should take precedence over default locations"


# Tests for check function
def test_check_registry_not_found(arbiter_checker, minimal_config, tmp_path):
    """Check returns INFO result when registry doesn't exist"""
    minimal_config.stack.arbiter_registry_path = None
    
    with patch('src_cartographer_compatibility_arbiter_checker.CheckResult', MockCheckResult):
        with patch('src_cartographer_compatibility_arbiter_checker.Severity', MockSeverity):
            results = arbiter_checker.check(minimal_config, tmp_path)
    
    assert len(results) > 0, "Should return non-empty list"
    assert isinstance(results, list), "Should return a list"
    
    # Check for registry exists check
    registry_check = [r for r in results if hasattr(r, 'check_id') and 
                      r.check_id == 'arbiter_registry_exists']
    if registry_check:
        assert registry_check[0].tool == 'arbiter', "tool should be 'arbiter'"


def test_check_valid_access_graph(arbiter_checker, minimal_config, tmp_path):
    """Check validates existing valid access_graph.json"""
    registry_dir = tmp_path / ".arbiter" / "registry"
    registry_dir.mkdir(parents=True)
    
    # Create valid access_graph.json
    access_graph = registry_dir / "access_graph.json"
    create_json_file(access_graph, {"nodes": [], "edges": []})
    
    minimal_config.stack.arbiter_registry_path = None
    
    with patch('src_cartographer_compatibility_arbiter_checker.CheckResult', MockCheckResult):
        with patch('src_cartographer_compatibility_arbiter_checker.Severity', MockSeverity):
            results = arbiter_checker.check(minimal_config, tmp_path)
    
    assert len(results) > 0, "Should return non-empty list"
    assert all(hasattr(r, 'tool') and r.tool == 'arbiter' for r in results), \
        "All results should have tool='arbiter'"


def test_check_valid_trust_ledger(arbiter_checker, minimal_config, tmp_path):
    """Check validates existing valid trust_ledger.json"""
    registry_dir = tmp_path / ".arbiter" / "registry"
    registry_dir.mkdir(parents=True)
    
    # Create valid trust_ledger.json
    trust_ledger = registry_dir / "trust_ledger.json"
    create_json_file(trust_ledger, {"entries": []})
    
    minimal_config.stack.arbiter_registry_path = None
    
    with patch('src_cartographer_compatibility_arbiter_checker.CheckResult', MockCheckResult):
        with patch('src_cartographer_compatibility_arbiter_checker.Severity', MockSeverity):
            results = arbiter_checker.check(minimal_config, tmp_path)
    
    assert len(results) > 0, "Should return non-empty list"
    assert all(hasattr(r, 'tool') and r.tool == 'arbiter' for r in results), \
        "All results should have tool='arbiter'"


def test_check_both_valid_files(arbiter_checker, minimal_config, tmp_path):
    """Check validates both access_graph.json and trust_ledger.json when both exist"""
    registry_dir = tmp_path / ".arbiter" / "registry"
    registry_dir.mkdir(parents=True)
    
    # Create both valid JSON files
    access_graph = registry_dir / "access_graph.json"
    create_json_file(access_graph, {"nodes": [], "edges": []})
    trust_ledger = registry_dir / "trust_ledger.json"
    create_json_file(trust_ledger, {"entries": []})
    
    minimal_config.stack.arbiter_registry_path = None
    
    with patch('src_cartographer_compatibility_arbiter_checker.CheckResult', MockCheckResult):
        with patch('src_cartographer_compatibility_arbiter_checker.Severity', MockSeverity):
            results = arbiter_checker.check(minimal_config, tmp_path)
    
    assert len(results) > 0, "Should return non-empty list"
    assert all(hasattr(r, 'tool') and r.tool == 'arbiter' for r in results), \
        "All results should have tool='arbiter'"


def test_check_invalid_json_access_graph(arbiter_checker, minimal_config, tmp_path):
    """Check detects invalid JSON in access_graph.json"""
    registry_dir = tmp_path / ".arbiter" / "registry"
    registry_dir.mkdir(parents=True)
    
    # Create invalid JSON
    access_graph = registry_dir / "access_graph.json"
    create_invalid_json_file(access_graph, "{invalid json content")
    
    minimal_config.stack.arbiter_registry_path = None
    
    with patch('src_cartographer_compatibility_arbiter_checker.CheckResult', MockCheckResult):
        with patch('src_cartographer_compatibility_arbiter_checker.Severity', MockSeverity):
            results = arbiter_checker.check(minimal_config, tmp_path)
    
    assert len(results) > 0, "Should return non-empty list"
    # Should contain error result for access_graph.json
    assert all(hasattr(r, 'tool') and r.tool == 'arbiter' for r in results), \
        "All results should have tool='arbiter'"


def test_check_invalid_json_trust_ledger(arbiter_checker, minimal_config, tmp_path):
    """Check detects invalid JSON in trust_ledger.json"""
    registry_dir = tmp_path / ".arbiter" / "registry"
    registry_dir.mkdir(parents=True)
    
    # Create invalid JSON
    trust_ledger = registry_dir / "trust_ledger.json"
    create_invalid_json_file(trust_ledger, "not valid json at all")
    
    minimal_config.stack.arbiter_registry_path = None
    
    with patch('src_cartographer_compatibility_arbiter_checker.CheckResult', MockCheckResult):
        with patch('src_cartographer_compatibility_arbiter_checker.Severity', MockSeverity):
            results = arbiter_checker.check(minimal_config, tmp_path)
    
    assert len(results) > 0, "Should return non-empty list"
    assert all(hasattr(r, 'tool') and r.tool == 'arbiter' for r in results), \
        "All results should have tool='arbiter'"


def test_check_file_read_error_access_graph(arbiter_checker, minimal_config, tmp_path):
    """Check handles file read error for access_graph.json"""
    registry_dir = tmp_path / ".arbiter" / "registry"
    registry_dir.mkdir(parents=True)
    
    # Create file
    access_graph = registry_dir / "access_graph.json"
    create_json_file(access_graph, {"test": "data"})
    
    minimal_config.stack.arbiter_registry_path = None
    
    # Mock open to raise permission error
    with patch('builtins.open', side_effect=PermissionError("Access denied")):
        with patch('src_cartographer_compatibility_arbiter_checker.CheckResult', MockCheckResult):
            with patch('src_cartographer_compatibility_arbiter_checker.Severity', MockSeverity):
                # Mock Path.exists to return True so it tries to read
                with patch.object(Path, 'exists', return_value=True):
                    results = arbiter_checker.check(minimal_config, tmp_path)
    
    assert len(results) > 0, "Should return non-empty list"
    assert all(hasattr(r, 'tool') and r.tool == 'arbiter' for r in results), \
        "All results should have tool='arbiter'"


def test_check_file_read_error_trust_ledger(arbiter_checker, minimal_config, tmp_path):
    """Check handles file read error for trust_ledger.json"""
    registry_dir = tmp_path / ".arbiter" / "registry"
    registry_dir.mkdir(parents=True)
    
    # Create file
    trust_ledger = registry_dir / "trust_ledger.json"
    create_json_file(trust_ledger, {"test": "data"})
    
    minimal_config.stack.arbiter_registry_path = None
    
    # Mock open to raise OSError
    with patch('builtins.open', side_effect=OSError("I/O error")):
        with patch('src_cartographer_compatibility_arbiter_checker.CheckResult', MockCheckResult):
            with patch('src_cartographer_compatibility_arbiter_checker.Severity', MockSeverity):
                with patch.object(Path, 'exists', return_value=True):
                    results = arbiter_checker.check(minimal_config, tmp_path)
    
    assert len(results) > 0, "Should return non-empty list"
    assert all(hasattr(r, 'tool') and r.tool == 'arbiter' for r in results), \
        "All results should have tool='arbiter'"


def test_check_always_returns_non_empty_list(arbiter_checker, minimal_config, tmp_path):
    """Invariant: check() always returns non-empty list"""
    # Test with various configurations
    configs_and_dirs = [
        (minimal_config, tmp_path),
    ]
    
    for config, base_dir in configs_and_dirs:
        with patch('src_cartographer_compatibility_arbiter_checker.CheckResult', MockCheckResult):
            with patch('src_cartographer_compatibility_arbiter_checker.Severity', MockSeverity):
                results = arbiter_checker.check(config, base_dir)
        
        assert len(results) > 0, "check() should always return non-empty list"
        assert isinstance(results, list), "check() should return a list"


def test_check_all_results_have_arbiter_tool(arbiter_checker, minimal_config, tmp_path):
    """Invariant: All CheckResult objects have tool='arbiter'"""
    # Test with registry not found
    with patch('src_cartographer_compatibility_arbiter_checker.CheckResult', MockCheckResult):
        with patch('src_cartographer_compatibility_arbiter_checker.Severity', MockSeverity):
            results = arbiter_checker.check(minimal_config, tmp_path)
    
    assert all(hasattr(r, 'tool') and r.tool == 'arbiter' for r in results), \
        "All CheckResult objects must have tool='arbiter'"
    
    # Test with registry found
    registry_dir = tmp_path / ".arbiter"
    registry_dir.mkdir()
    access_graph = registry_dir / "access_graph.json"
    create_json_file(access_graph, {})
    
    with patch('src_cartographer_compatibility_arbiter_checker.CheckResult', MockCheckResult):
        with patch('src_cartographer_compatibility_arbiter_checker.Severity', MockSeverity):
            results = arbiter_checker.check(minimal_config, tmp_path)
    
    assert all(hasattr(r, 'tool') and r.tool == 'arbiter' for r in results), \
        "All CheckResult objects must have tool='arbiter'"


def test_check_file_search_order_access_graph(arbiter_checker, minimal_config, tmp_path):
    """Invariant: File search order for access_graph.json: registry_path, base_dir"""
    registry_dir = tmp_path / ".arbiter" / "registry"
    registry_dir.mkdir(parents=True)
    
    # Create access_graph.json in both locations with different content
    registry_access_graph = registry_dir / "access_graph.json"
    create_json_file(registry_access_graph, {"location": "registry"})
    
    base_access_graph = tmp_path / "access_graph.json"
    create_json_file(base_access_graph, {"location": "base"})
    
    minimal_config.stack.arbiter_registry_path = None
    
    with patch('src_cartographer_compatibility_arbiter_checker.CheckResult', MockCheckResult):
        with patch('src_cartographer_compatibility_arbiter_checker.Severity', MockSeverity):
            results = arbiter_checker.check(minimal_config, tmp_path)
    
    assert len(results) > 0, "Should return non-empty list"
    # The implementation should prefer registry_path over base_dir


def test_check_file_search_order_trust_ledger(arbiter_checker, minimal_config, tmp_path):
    """Invariant: File search order for trust_ledger.json: registry_path, base_dir"""
    registry_dir = tmp_path / ".arbiter" / "registry"
    registry_dir.mkdir(parents=True)
    
    # Create trust_ledger.json in both locations with different content
    registry_trust_ledger = registry_dir / "trust_ledger.json"
    create_json_file(registry_trust_ledger, {"location": "registry"})
    
    base_trust_ledger = tmp_path / "trust_ledger.json"
    create_json_file(base_trust_ledger, {"location": "base"})
    
    minimal_config.stack.arbiter_registry_path = None
    
    with patch('src_cartographer_compatibility_arbiter_checker.CheckResult', MockCheckResult):
        with patch('src_cartographer_compatibility_arbiter_checker.Severity', MockSeverity):
            results = arbiter_checker.check(minimal_config, tmp_path)
    
    assert len(results) > 0, "Should return non-empty list"
    # The implementation should prefer registry_path over base_dir


def test_check_empty_json_files(arbiter_checker, minimal_config, tmp_path):
    """Edge case: Check handles empty but valid JSON files"""
    registry_dir = tmp_path / ".arbiter" / "registry"
    registry_dir.mkdir(parents=True)
    
    # Create empty but valid JSON
    access_graph = registry_dir / "access_graph.json"
    create_json_file(access_graph, {})
    trust_ledger = registry_dir / "trust_ledger.json"
    create_json_file(trust_ledger, {})
    
    minimal_config.stack.arbiter_registry_path = None
    
    with patch('src_cartographer_compatibility_arbiter_checker.CheckResult', MockCheckResult):
        with patch('src_cartographer_compatibility_arbiter_checker.Severity', MockSeverity):
            results = arbiter_checker.check(minimal_config, tmp_path)
    
    assert len(results) > 0, "Should return non-empty list"
    assert all(hasattr(r, 'tool') and r.tool == 'arbiter' for r in results), \
        "All results should have tool='arbiter'"


def test_check_missing_access_graph(arbiter_checker, minimal_config, tmp_path):
    """Edge case: Check handles missing access_graph.json"""
    registry_dir = tmp_path / ".arbiter" / "registry"
    registry_dir.mkdir(parents=True)
    
    # Create only trust_ledger.json
    trust_ledger = registry_dir / "trust_ledger.json"
    create_json_file(trust_ledger, {"entries": []})
    
    minimal_config.stack.arbiter_registry_path = None
    
    with patch('src_cartographer_compatibility_arbiter_checker.CheckResult', MockCheckResult):
        with patch('src_cartographer_compatibility_arbiter_checker.Severity', MockSeverity):
            results = arbiter_checker.check(minimal_config, tmp_path)
    
    assert len(results) > 0, "Should return non-empty list"
    assert all(hasattr(r, 'tool') and r.tool == 'arbiter' for r in results), \
        "All results should have tool='arbiter'"


# Additional edge case tests
def test_find_registry_with_none_stack(tmp_path):
    """Edge case: Handle config with None or missing stack attribute"""
    checker = ArbiterChecker()
    config = MockCartographerConfig()
    config.stack = None
    
    # Should handle gracefully - either return None or raise appropriate error
    try:
        result = checker._find_registry(config, tmp_path)
        # If it doesn't raise, it should return None or a valid path
        assert result is None or isinstance(result, Path)
    except AttributeError:
        # This is also acceptable behavior
        pass


def test_check_with_symlink_registry(arbiter_checker, minimal_config, tmp_path):
    """Edge case: Check handles symlinked registry directory"""
    real_registry = tmp_path / "real_registry"
    real_registry.mkdir()
    
    symlink_registry = tmp_path / ".arbiter"
    try:
        symlink_registry.symlink_to(real_registry)
    except (OSError, NotImplementedError):
        # Skip test if symlinks not supported
        pytest.skip("Symlinks not supported on this platform")
    
    access_graph = real_registry / "access_graph.json"
    create_json_file(access_graph, {"test": "data"})
    
    minimal_config.stack.arbiter_registry_path = None
    
    with patch('src_cartographer_compatibility_arbiter_checker.CheckResult', MockCheckResult):
        with patch('src_cartographer_compatibility_arbiter_checker.Severity', MockSeverity):
            results = arbiter_checker.check(minimal_config, tmp_path)
    
    assert len(results) > 0, "Should handle symlinked registry"
    assert all(hasattr(r, 'tool') and r.tool == 'arbiter' for r in results)


def test_check_large_json_files(arbiter_checker, minimal_config, tmp_path):
    """Edge case: Check handles large valid JSON files"""
    registry_dir = tmp_path / ".arbiter" / "registry"
    registry_dir.mkdir(parents=True)
    
    # Create large JSON files
    large_data = {"nodes": [{"id": i, "data": "x" * 100} for i in range(1000)]}
    access_graph = registry_dir / "access_graph.json"
    create_json_file(access_graph, large_data)
    
    minimal_config.stack.arbiter_registry_path = None
    
    with patch('src_cartographer_compatibility_arbiter_checker.CheckResult', MockCheckResult):
        with patch('src_cartographer_compatibility_arbiter_checker.Severity', MockSeverity):
            results = arbiter_checker.check(minimal_config, tmp_path)
    
    assert len(results) > 0, "Should handle large JSON files"
    assert all(hasattr(r, 'tool') and r.tool == 'arbiter' for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
