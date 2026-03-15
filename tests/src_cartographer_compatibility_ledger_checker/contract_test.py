"""
Contract tests for LedgerChecker compatibility checker.
Tests verify behavior at boundaries, not internals.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, mock_open
import tempfile
import os
import yaml

# Import the component under test
from src.cartographer.compatibility.ledger_checker import LedgerChecker, _find_registry


# Mock classes for dependencies
class MockSeverity:
    INFO = "INFO"
    WARN = "WARN"
    FAIL = "FAIL"


class MockCheckResult:
    def __init__(self, tool, check_id, severity, message="", **kwargs):
        self.tool = tool
        self.check_id = check_id
        self.severity = severity
        self.message = message
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def __eq__(self, other):
        if not isinstance(other, MockCheckResult):
            return False
        return (self.tool == other.tool and 
                self.check_id == other.check_id and 
                self.severity == other.severity)


class MockCartographerConfig:
    def __init__(self, ledger_registry_path=None):
        self.stack = Mock()
        if ledger_registry_path:
            self.stack.ledger_registry = ledger_registry_path
        else:
            self.stack.ledger_registry = None


# Fixtures
@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_config():
    """Create a mock CartographerConfig."""
    return MockCartographerConfig()


@pytest.fixture
def ledger_checker():
    """Create a LedgerChecker instance."""
    return LedgerChecker()


@pytest.fixture
def valid_schema_yaml():
    """Return a valid ledger schema YAML content."""
    return """
name: user_ledger
fields:
  - name: user_id
    type: string
    classification: pii
  - name: email
    type: string
    classification: pii
    gdpr_erasable: true
    erasure_method: anonymize
  - name: created_at
    type: timestamp
    classification: metadata
    audit: true
    retention_policy: 7_years
"""


@pytest.fixture
def invalid_classification_schema():
    """Schema with majority of fields missing classification."""
    return """
name: bad_schema
fields:
  - name: field1
    type: string
  - name: field2
    type: string
  - name: field3
    type: string
    classification: pii
"""


@pytest.fixture
def conflicting_annotation_schema():
    """Schema with gdpr_erasable and immutable conflict."""
    return """
name: conflict_schema
fields:
  - name: conflicting_field
    type: string
    classification: pii
    gdpr_erasable: true
    immutable: true
"""


@pytest.fixture
def gdpr_no_method_schema():
    """Schema with gdpr_erasable but no erasure_method."""
    return """
name: gdpr_schema
fields:
  - name: user_email
    type: string
    classification: pii
    gdpr_erasable: true
"""


@pytest.fixture
def audit_no_retention_schema():
    """Schema with audit but no retention_policy."""
    return """
name: audit_schema
fields:
  - name: audit_log
    type: string
    classification: metadata
    audit: true
"""


# Layer 1: tool_name() tests
class TestToolName:
    """Tests for tool_name() property method."""
    
    def test_tool_name_happy_path(self, ledger_checker):
        """Verify tool_name() returns 'ledger' string."""
        result = ledger_checker.tool_name()
        
        assert result == 'ledger', "tool_name should return 'ledger'"
        assert isinstance(result, str), "tool_name should return a string"
        assert len(result) > 0, "tool_name should return non-empty string"
    
    def test_tool_name_stability(self, ledger_checker):
        """Verify tool_name() returns same value on multiple calls."""
        first_call = ledger_checker.tool_name()
        second_call = ledger_checker.tool_name()
        
        assert first_call == second_call, "tool_name should be stable across calls"
        assert first_call == 'ledger', "tool_name should always return 'ledger'"


# Layer 2: check() tests
class TestCheck:
    """Tests for check() method."""
    
    def test_check_valid_registry_with_schemas(self, temp_dir, valid_schema_yaml):
        """Happy path: check() with valid registry containing schema files."""
        # Setup registry structure
        registry_dir = temp_dir / ".ledger" / "registry"
        registry_dir.mkdir(parents=True)
        
        schema_file = registry_dir / "user.yaml"
        schema_file.write_text(valid_schema_yaml)
        
        config = MockCartographerConfig()
        checker = LedgerChecker()
        
        results = checker.check(config, temp_dir)
        
        assert len(results) >= 1, "Should return at least one CheckResult"
        assert all(r.tool == 'ledger' for r in results), "All results should have tool='ledger'"
    
    def test_check_no_registry_found(self, temp_dir):
        """Edge case: check() when no registry directory exists."""
        config = MockCartographerConfig()
        checker = LedgerChecker()
        
        results = checker.check(config, temp_dir)
        
        assert len(results) == 1, "Should return single CheckResult when no registry"
        assert results[0].check_id == 'ledger_registry_exists', "Should have correct check_id"
        assert results[0].tool == 'ledger', "Result should have tool='ledger'"
        assert results[0].severity == MockSeverity.INFO, "Should be INFO severity"
    
    def test_check_empty_registry(self, temp_dir):
        """Edge case: check() with registry directory containing no YAML files."""
        registry_dir = temp_dir / ".ledger" / "registry"
        registry_dir.mkdir(parents=True)
        
        config = MockCartographerConfig()
        checker = LedgerChecker()
        
        results = checker.check(config, temp_dir)
        
        assert len(results) >= 1, "Should return at least one CheckResult"
        assert all(r.tool == 'ledger' for r in results), "All results should have tool='ledger'"
    
    def test_check_yaml_parse_error_malformed(self, temp_dir):
        """Error case: YAML file with malformed syntax."""
        registry_dir = temp_dir / ".ledger" / "registry"
        registry_dir.mkdir(parents=True)
        
        malformed_yaml = "invalid: yaml: content:\n\t- broken"
        schema_file = registry_dir / "bad.yaml"
        schema_file.write_text(malformed_yaml)
        
        config = MockCartographerConfig()
        checker = LedgerChecker()
        
        # Should either raise exception or return error result
        try:
            results = checker.check(config, temp_dir)
            # If no exception, should have error result
            assert any('yaml' in r.message.lower() or 'parse' in r.message.lower() 
                      for r in results if hasattr(r, 'message')), "Should indicate YAML parse error"
        except Exception as e:
            assert 'yaml' in str(e).lower() or 'parse' in str(e).lower(), "Exception should mention YAML parse error"
    
    def test_check_yaml_parse_error_invalid_structure(self, temp_dir):
        """Error case: YAML file with invalid structure."""
        registry_dir = temp_dir / ".ledger" / "registry"
        registry_dir.mkdir(parents=True)
        
        # Valid YAML but unexpected structure
        invalid_structure = "just_a_string"
        schema_file = registry_dir / "invalid_structure.yaml"
        schema_file.write_text(invalid_structure)
        
        config = MockCartographerConfig()
        checker = LedgerChecker()
        
        # Should handle gracefully
        try:
            results = checker.check(config, temp_dir)
            assert len(results) >= 1, "Should return results even with invalid structure"
        except Exception:
            # Exception is acceptable for invalid structure
            pass
    
    @patch('builtins.open', side_effect=PermissionError("Permission denied"))
    def test_check_file_read_error_permission(self, mock_file, temp_dir):
        """Error case: File cannot be read due to permissions."""
        registry_dir = temp_dir / ".ledger" / "registry"
        registry_dir.mkdir(parents=True)
        
        # Create a file (but mock will prevent reading)
        schema_file = registry_dir / "restricted.yaml"
        schema_file.touch()
        
        config = MockCartographerConfig()
        checker = LedgerChecker()
        
        try:
            results = checker.check(config, temp_dir)
            # If returns results, should indicate file read error
            assert any('permission' in r.message.lower() or 'read' in r.message.lower()
                      for r in results if hasattr(r, 'message')), "Should indicate file read error"
        except (PermissionError, IOError):
            # Exception is acceptable
            pass
    
    def test_check_file_read_error_missing(self, temp_dir):
        """Error case: File referenced but does not exist."""
        registry_dir = temp_dir / ".ledger" / "registry"
        registry_dir.mkdir(parents=True)
        
        config = MockCartographerConfig()
        checker = LedgerChecker()
        
        # Simulate scenario where file is discovered but deleted before read
        with patch.object(Path, 'glob', return_value=[Path("nonexistent.yaml")]):
            try:
                results = checker.check(config, temp_dir)
                # Should handle gracefully
                assert len(results) >= 1, "Should return results"
            except (FileNotFoundError, IOError):
                # Exception is acceptable
                pass
    
    def test_check_classification_one_per_schema(self, temp_dir, valid_schema_yaml):
        """Invariant: Classification check creates one result per schema file."""
        registry_dir = temp_dir / ".ledger" / "registry"
        registry_dir.mkdir(parents=True)
        
        # Create multiple schema files
        for i in range(3):
            schema_file = registry_dir / f"schema{i}.yaml"
            schema_file.write_text(valid_schema_yaml)
        
        config = MockCartographerConfig()
        checker = LedgerChecker()
        
        results = checker.check(config, temp_dir)
        
        # Count classification-related results
        classification_results = [r for r in results if 'classification' in r.check_id.lower()]
        schema_file_count = len(list(registry_dir.glob("*.yaml")))
        
        assert len(classification_results) == schema_file_count, \
            "Should have one classification result per schema file"
    
    def test_check_annotation_conflict_gdpr_immutable(self, temp_dir, conflicting_annotation_schema):
        """Edge case: Field annotated as both gdpr_erasable and immutable."""
        registry_dir = temp_dir / ".ledger" / "registry"
        registry_dir.mkdir(parents=True)
        
        schema_file = registry_dir / "conflict.yaml"
        schema_file.write_text(conflicting_annotation_schema)
        
        config = MockCartographerConfig()
        checker = LedgerChecker()
        
        results = checker.check(config, temp_dir)
        
        assert any(r.severity == MockSeverity.FAIL for r in results), \
            "Should have FAIL result for annotation conflict"
        fail_results = [r for r in results if r.severity == MockSeverity.FAIL]
        assert any('conflict' in r.message.lower() or 'annotation' in r.message.lower()
                  for r in fail_results if hasattr(r, 'message')), \
            "FAIL result should mention conflict"
    
    def test_check_gdpr_erasable_no_method(self, temp_dir, gdpr_no_method_schema):
        """Edge case: GDPR erasable field without erasure_method."""
        registry_dir = temp_dir / ".ledger" / "registry"
        registry_dir.mkdir(parents=True)
        
        schema_file = registry_dir / "gdpr.yaml"
        schema_file.write_text(gdpr_no_method_schema)
        
        config = MockCartographerConfig()
        checker = LedgerChecker()
        
        results = checker.check(config, temp_dir)
        
        assert any(r.severity == MockSeverity.WARN for r in results), \
            "Should have WARN result for missing erasure_method"
    
    def test_check_audit_field_no_retention(self, temp_dir, audit_no_retention_schema):
        """Edge case: Audit field without retention_policy."""
        registry_dir = temp_dir / ".ledger" / "registry"
        registry_dir.mkdir(parents=True)
        
        schema_file = registry_dir / "audit.yaml"
        schema_file.write_text(audit_no_retention_schema)
        
        config = MockCartographerConfig()
        checker = LedgerChecker()
        
        results = checker.check(config, temp_dir)
        
        assert any(r.severity == MockSeverity.WARN for r in results), \
            "Should have WARN result for missing retention_policy"
    
    def test_check_classification_fail_majority_missing(self, temp_dir, invalid_classification_schema):
        """Edge case: Classification FAIL when more than half fields missing classification."""
        registry_dir = temp_dir / ".ledger" / "registry"
        registry_dir.mkdir(parents=True)
        
        schema_file = registry_dir / "bad_classification.yaml"
        schema_file.write_text(invalid_classification_schema)
        
        config = MockCartographerConfig()
        checker = LedgerChecker()
        
        results = checker.check(config, temp_dir)
        
        # Should have FAIL for majority missing classification
        classification_results = [r for r in results if 'classification' in r.check_id.lower()]
        assert any(r.severity == MockSeverity.FAIL for r in classification_results), \
            "Should have FAIL when majority of fields missing classification"
    
    def test_check_classification_warn_minority_missing(self, temp_dir):
        """Edge case: Classification WARN when less than half fields missing classification."""
        registry_dir = temp_dir / ".ledger" / "registry"
        registry_dir.mkdir(parents=True)
        
        # Schema with minority missing classification
        schema_yaml = """
name: mostly_classified
fields:
  - name: field1
    type: string
    classification: pii
  - name: field2
    type: string
    classification: pii
  - name: field3
    type: string
"""
        schema_file = registry_dir / "mostly_good.yaml"
        schema_file.write_text(schema_yaml)
        
        config = MockCartographerConfig()
        checker = LedgerChecker()
        
        results = checker.check(config, temp_dir)
        
        classification_results = [r for r in results if 'classification' in r.check_id.lower()]
        # Should be WARN, not FAIL, when minority missing
        if classification_results:
            assert any(r.severity == MockSeverity.WARN for r in classification_results), \
                "Should have WARN when minority of fields missing classification"
    
    def test_check_multiple_yaml_files(self, temp_dir, valid_schema_yaml):
        """Happy path: check() processes multiple YAML schema files."""
        registry_dir = temp_dir / ".ledger" / "registry"
        registry_dir.mkdir(parents=True)
        
        # Create 5 schema files
        num_files = 5
        for i in range(num_files):
            schema_file = registry_dir / f"schema{i}.yaml"
            schema_file.write_text(valid_schema_yaml)
        
        config = MockCartographerConfig()
        checker = LedgerChecker()
        
        results = checker.check(config, temp_dir)
        
        assert len(results) >= num_files, "Should return results for all YAML files"
    
    def test_check_results_always_non_empty(self, temp_dir, mock_config):
        """Invariant: check() always returns at least one CheckResult."""
        checker = LedgerChecker()
        
        results = checker.check(mock_config, temp_dir)
        
        assert len(results) >= 1, "check() must always return at least one CheckResult"
    
    def test_check_idempotency(self, temp_dir, valid_schema_yaml):
        """Invariant: check() returns same results when called multiple times."""
        registry_dir = temp_dir / ".ledger" / "registry"
        registry_dir.mkdir(parents=True)
        
        schema_file = registry_dir / "schema.yaml"
        schema_file.write_text(valid_schema_yaml)
        
        config = MockCartographerConfig()
        checker = LedgerChecker()
        
        first_call = checker.check(config, temp_dir)
        second_call = checker.check(config, temp_dir)
        
        assert len(first_call) == len(second_call), "Should return same number of results"
        # Compare check_ids and severities
        first_ids = sorted([(r.check_id, r.severity) for r in first_call])
        second_ids = sorted([(r.check_id, r.severity) for r in second_call])
        assert first_ids == second_ids, "Results should be identical across calls"


# Layer 3: _find_registry() tests
class TestFindRegistry:
    """Tests for _find_registry() function."""
    
    def test_find_registry_config_path(self, temp_dir):
        """Happy path: _find_registry() finds registry from config.stack.ledger_registry."""
        # Create custom registry location
        custom_registry = temp_dir / "custom" / "ledger_registry"
        custom_registry.mkdir(parents=True)
        
        config = MockCartographerConfig(ledger_registry_path=str(custom_registry))
        
        result = _find_registry(config, temp_dir)
        
        assert result is not None, "Should find registry from config"
        assert result.exists(), "Returned path should exist"
        assert isinstance(result, Path), "Should return Path object"
        assert str(custom_registry) in str(result), "Should match config path"
    
    def test_find_registry_ledger_registry_fallback(self, temp_dir):
        """Edge case: _find_registry() falls back to .ledger/registry."""
        # Create .ledger/registry
        fallback_registry = temp_dir / ".ledger" / "registry"
        fallback_registry.mkdir(parents=True)
        
        config = MockCartographerConfig()
        
        result = _find_registry(config, temp_dir)
        
        assert result is not None, "Should find .ledger/registry"
        assert result.name == 'registry', "Should be the registry directory"
    
    def test_find_registry_ledger_fallback(self, temp_dir):
        """Edge case: _find_registry() falls back to .ledger."""
        # Create only .ledger, not .ledger/registry
        ledger_dir = temp_dir / ".ledger"
        ledger_dir.mkdir()
        
        config = MockCartographerConfig()
        
        result = _find_registry(config, temp_dir)
        
        assert result is not None, "Should find .ledger"
        assert result.name == '.ledger', "Should be the .ledger directory"
    
    def test_find_registry_none_found(self, temp_dir):
        """Edge case: _find_registry() returns None when no registry found."""
        config = MockCartographerConfig()
        
        result = _find_registry(config, temp_dir)
        
        assert result is None, "Should return None when no registry exists"
    
    def test_find_registry_search_order(self, temp_dir):
        """Invariant: _find_registry() checks in correct order."""
        # Create all possible locations
        custom_registry = temp_dir / "custom_registry"
        custom_registry.mkdir()
        
        ledger_registry = temp_dir / ".ledger" / "registry"
        ledger_registry.mkdir(parents=True)
        
        ledger_dir = temp_dir / ".ledger"
        # Already created above
        
        config = MockCartographerConfig(ledger_registry_path=str(custom_registry))
        
        result = _find_registry(config, temp_dir)
        
        # Should return config path first, not fallback paths
        assert result is not None, "Should find a registry"
        assert str(custom_registry) in str(result), "Should prioritize config.stack.ledger_registry"
        assert result != ledger_registry, "Should not return fallback when config path exists"
    
    def test_find_registry_nonexistent_config_path(self, temp_dir):
        """Edge case: config.stack.ledger_registry set but path doesn't exist."""
        # Config points to non-existent path
        config = MockCartographerConfig(ledger_registry_path=str(temp_dir / "nonexistent"))
        
        # Create fallback
        fallback = temp_dir / ".ledger" / "registry"
        fallback.mkdir(parents=True)
        
        result = _find_registry(config, temp_dir)
        
        # Should fall back to .ledger/registry
        assert result is not None, "Should fall back when config path doesn't exist"
        assert result == fallback, "Should use fallback path"


# Additional edge case tests
class TestEdgeCases:
    """Additional edge case tests."""
    
    def test_check_with_nested_registry(self, temp_dir):
        """Edge case: Registry in nested subdirectory."""
        # Create deeply nested structure
        nested_registry = temp_dir / "a" / "b" / "c" / "registry"
        nested_registry.mkdir(parents=True)
        
        schema_yaml = """
name: nested_schema
fields:
  - name: id
    type: string
    classification: pii
"""
        schema_file = nested_registry / "schema.yaml"
        schema_file.write_text(schema_yaml)
        
        config = MockCartographerConfig(ledger_registry_path=str(nested_registry))
        checker = LedgerChecker()
        
        results = checker.check(config, temp_dir)
        
        assert len(results) >= 1, "Should handle nested registry"
        assert all(r.tool == 'ledger' for r in results), "All results should have tool='ledger'"
    
    def test_check_yaml_with_unicode(self, temp_dir):
        """Edge case: YAML file with unicode characters."""
        registry_dir = temp_dir / ".ledger" / "registry"
        registry_dir.mkdir(parents=True)
        
        unicode_yaml = """
name: unicode_schema_测试
fields:
  - name: user_名前
    type: string
    classification: pii
"""
        schema_file = registry_dir / "unicode.yaml"
        schema_file.write_text(unicode_yaml, encoding='utf-8')
        
        config = MockCartographerConfig()
        checker = LedgerChecker()
        
        results = checker.check(config, temp_dir)
        
        assert len(results) >= 1, "Should handle unicode in YAML"
    
    def test_check_empty_yaml_file(self, temp_dir):
        """Edge case: Empty YAML file."""
        registry_dir = temp_dir / ".ledger" / "registry"
        registry_dir.mkdir(parents=True)
        
        schema_file = registry_dir / "empty.yaml"
        schema_file.write_text("")
        
        config = MockCartographerConfig()
        checker = LedgerChecker()
        
        # Should handle gracefully
        results = checker.check(config, temp_dir)
        assert len(results) >= 1, "Should handle empty YAML file"
    
    def test_check_yaml_comments_only(self, temp_dir):
        """Edge case: YAML file with only comments."""
        registry_dir = temp_dir / ".ledger" / "registry"
        registry_dir.mkdir(parents=True)
        
        comments_yaml = """
# This is a comment
# Another comment
"""
        schema_file = registry_dir / "comments.yaml"
        schema_file.write_text(comments_yaml)
        
        config = MockCartographerConfig()
        checker = LedgerChecker()
        
        results = checker.check(config, temp_dir)
        assert len(results) >= 1, "Should handle YAML with only comments"
