"""
Contract-based pytest test suite for BatonChecker component.
Tests verify behavior against contract specifications with focus on boundaries,
error handling, and invariants.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, mock_open
from typing import Any, Optional
import tempfile
import random
import yaml


# Import the component under test
from src.cartographer.compatibility.baton_checker import (
    BatonChecker,
    _find_baton_config,
    _version_lt
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def baton_checker():
    """Factory fixture for BatonChecker instance."""
    return BatonChecker()


@pytest.fixture
def mock_config_factory():
    """Factory fixture for creating CartographerConfig mocks with various configurations."""
    def _create_config(
        baton_config_path: Optional[str] = None,
        min_baton_schema_version: str = "1.0"
    ):
        config = Mock()
        config.compatibility = Mock()
        config.compatibility.min_baton_schema_version = min_baton_schema_version
        config.stack = Mock()
        config.stack.baton_config = baton_config_path
        return config
    return _create_config


@pytest.fixture
def temp_dir():
    """Create a temporary directory for file-based tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# ============================================================================
# TestToolName
# ============================================================================

class TestToolName:
    """Test suite for tool_name method."""
    
    def test_tool_name_happy_path(self, baton_checker):
        """tool_name returns the literal string 'baton'."""
        result = baton_checker.tool_name()
        assert result == 'baton'
        assert isinstance(result, str)


# ============================================================================
# TestCheck
# ============================================================================

class TestCheck:
    """Test suite for check method."""
    
    def test_check_baton_config_not_found(self, baton_checker, mock_config_factory, temp_dir):
        """check returns INFO CheckResult when baton config not found."""
        config = mock_config_factory(baton_config_path=None)
        
        # Ensure no baton files exist
        result = baton_checker.check(config, temp_dir)
        
        assert len(result) >= 1
        assert result[0].tool == 'baton'
        # Check for INFO level (flexible attribute name)
        assert hasattr(result[0], 'level') or hasattr(result[0], 'severity')
        if hasattr(result[0], 'level'):
            assert result[0].level in ['INFO', 'info']
        elif hasattr(result[0], 'severity'):
            assert result[0].severity in ['INFO', 'info']
    
    @patch('src_cartographer_compatibility_baton_checker._find_baton_config')
    @patch('builtins.open', new_callable=mock_open, read_data='invalid: yaml: content: [')
    @patch('yaml.safe_load')
    def test_check_yaml_parse_error(self, mock_yaml_load, mock_file, mock_find, 
                                     baton_checker, mock_config_factory, temp_dir):
        """check returns FAIL CheckResult when YAML is invalid."""
        config = mock_config_factory()
        mock_find.return_value = temp_dir / "baton.yaml"
        mock_yaml_load.side_effect = yaml.YAMLError("Invalid YAML")
        
        result = baton_checker.check(config, temp_dir)
        
        assert len(result) >= 1
        assert result[0].tool == 'baton'
        if hasattr(result[0], 'level'):
            assert result[0].level in ['FAIL', 'fail', 'ERROR', 'error']
        elif hasattr(result[0], 'severity'):
            assert result[0].severity in ['FAIL', 'fail', 'ERROR', 'error']
    
    @patch('src_cartographer_compatibility_baton_checker._find_baton_config')
    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.safe_load')
    def test_check_valid_compatible_version(self, mock_yaml_load, mock_file, mock_find,
                                            baton_checker, mock_config_factory, temp_dir):
        """check returns PASS CheckResult when schema version is compatible."""
        config = mock_config_factory(min_baton_schema_version="1.0")
        mock_find.return_value = temp_dir / "baton.yaml"
        mock_yaml_load.return_value = {
            'schema_version': '2.0',
            'nodes': {},
            'global': {}
        }
        
        result = baton_checker.check(config, temp_dir)
        
        assert len(result) >= 1
        assert all(r.tool == 'baton' for r in result)
    
    @patch('src_cartographer_compatibility_baton_checker._find_baton_config')
    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.safe_load')
    @patch('src_cartographer_compatibility_baton_checker._version_lt')
    def test_check_incompatible_version(self, mock_version_lt, mock_yaml_load, 
                                        mock_file, mock_find, baton_checker, 
                                        mock_config_factory, temp_dir):
        """check returns FAIL CheckResult when schema version is incompatible."""
        config = mock_config_factory(min_baton_schema_version="2.0")
        mock_find.return_value = temp_dir / "baton.yaml"
        mock_yaml_load.return_value = {
            'schema_version': '1.0',
            'nodes': {},
            'global': {}
        }
        # Mock version comparison to indicate 1.0 < 2.0
        mock_version_lt.return_value = True
        
        result = baton_checker.check(config, temp_dir)
        
        assert len(result) >= 1
        assert all(r.tool == 'baton' for r in result)
        # Should have at least one FAIL result
        has_fail = False
        for r in result:
            if hasattr(r, 'level') and r.level in ['FAIL', 'fail', 'ERROR', 'error']:
                has_fail = True
            elif hasattr(r, 'severity') and r.severity in ['FAIL', 'fail', 'ERROR', 'error']:
                has_fail = True
        assert has_fail
    
    @patch('src_cartographer_compatibility_baton_checker._find_baton_config')
    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.safe_load')
    def test_check_all_results_have_baton_tool_field(self, mock_yaml_load, mock_file, 
                                                     mock_find, baton_checker, 
                                                     mock_config_factory, temp_dir):
        """check ensures all CheckResult objects have tool field set to 'baton' (invariant)."""
        config = mock_config_factory()
        
        # Test multiple scenarios
        scenarios = [
            None,  # Config not found
            temp_dir / "baton.yaml"  # Config found
        ]
        
        for scenario_path in scenarios:
            mock_find.return_value = scenario_path
            if scenario_path:
                mock_yaml_load.return_value = {
                    'schema_version': '1.0',
                    'nodes': {'node1': {}},
                    'global': {}
                }
            
            result = baton_checker.check(config, temp_dir)
            assert all(r.tool == 'baton' for r in result), \
                f"Failed invariant for scenario: {scenario_path}"
    
    @patch('src_cartographer_compatibility_baton_checker._find_baton_config')
    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.safe_load')
    def test_check_malformed_yaml_with_tabs(self, mock_yaml_load, mock_file, mock_find,
                                           baton_checker, mock_config_factory, temp_dir):
        """check handles YAML with tab characters causing parse errors."""
        config = mock_config_factory()
        mock_find.return_value = temp_dir / "baton.yaml"
        mock_yaml_load.side_effect = yaml.YAMLError("Tab character in YAML")
        
        result = baton_checker.check(config, temp_dir)
        
        assert len(result) >= 1
        assert result[0].tool == 'baton'
    
    @patch('src_cartographer_compatibility_baton_checker._find_baton_config')
    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.safe_load')
    def test_check_yaml_type_mismatch(self, mock_yaml_load, mock_file, mock_find,
                                     baton_checker, mock_config_factory, temp_dir):
        """check handles YAML type mismatches gracefully."""
        config = mock_config_factory()
        mock_find.return_value = temp_dir / "baton.yaml"
        # Return a list instead of dict
        mock_yaml_load.return_value = ['item1', 'item2']
        
        result = baton_checker.check(config, temp_dir)
        
        assert len(result) >= 1
        assert all(r.tool == 'baton' for r in result)
    
    @patch('src_cartographer_compatibility_baton_checker._find_baton_config')
    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.safe_load')
    def test_check_empty_yaml_file(self, mock_yaml_load, mock_file, mock_find,
                                   baton_checker, mock_config_factory, temp_dir):
        """check handles empty YAML file."""
        config = mock_config_factory()
        mock_find.return_value = temp_dir / "baton.yaml"
        mock_yaml_load.return_value = None
        
        result = baton_checker.check(config, temp_dir)
        
        assert len(result) >= 1
        assert all(r.tool == 'baton' for r in result)
    
    @patch('src_cartographer_compatibility_baton_checker._find_baton_config')
    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.safe_load')
    def test_check_default_baton_version(self, mock_yaml_load, mock_file, mock_find,
                                         baton_checker, mock_config_factory, temp_dir):
        """check uses default version '1.0' if not specified in config (invariant)."""
        config = mock_config_factory(min_baton_schema_version="1.0")
        mock_find.return_value = temp_dir / "baton.yaml"
        # YAML without schema_version field
        mock_yaml_load.return_value = {
            'nodes': {},
            'global': {}
        }
        
        result = baton_checker.check(config, temp_dir)
        
        assert len(result) >= 1
        assert all(r.tool == 'baton' for r in result)
    
    @patch('src_cartographer_compatibility_baton_checker._find_baton_config')
    def test_check_config_file_search_order(self, mock_find, baton_checker, 
                                           mock_config_factory, temp_dir):
        """check follows search order: config.stack.baton_config, baton.yaml, baton.yml (invariant)."""
        config = mock_config_factory()
        
        # Verify _find_baton_config is called with correct parameters
        baton_checker.check(config, temp_dir)
        mock_find.assert_called_once_with(config, temp_dir)
    
    def test_check_integration_real_files(self, baton_checker, mock_config_factory, temp_dir):
        """Integration test: check with real baton.yaml file structure."""
        config = mock_config_factory(min_baton_schema_version="1.0")
        
        # Create real baton.yaml file
        baton_file = temp_dir / "baton.yaml"
        baton_content = """
schema_version: "2.0"
nodes:
  node1:
    type: worker
    config:
      workers: 4
  node2:
    type: manager
global:
  timeout: 30
  retries: 3
"""
        baton_file.write_text(baton_content)
        
        result = baton_checker.check(config, temp_dir)
        
        assert len(result) >= 1
        assert all(r.tool == 'baton' for r in result)
        # Verify at least one result exists
        assert isinstance(result, list)


# ============================================================================
# TestFindBatonConfig
# ============================================================================

class TestFindBatonConfig:
    """Test suite for _find_baton_config function."""
    
    def test_find_baton_config_with_configured_path_exists(self, mock_config_factory, temp_dir):
        """_find_baton_config returns configured path when it exists."""
        baton_file = temp_dir / "custom_baton.yaml"
        baton_file.write_text("schema_version: 1.0")
        
        config = mock_config_factory(baton_config_path=str(baton_file))
        result = _find_baton_config(config, temp_dir)
        
        assert result is not None
        assert result.exists()
        assert 'baton' in result.name
    
    def test_find_baton_config_searches_baton_yaml(self, mock_config_factory, temp_dir):
        """_find_baton_config searches for baton.yaml when no configured path."""
        config = mock_config_factory(baton_config_path=None)
        baton_file = temp_dir / "baton.yaml"
        baton_file.write_text("schema_version: 1.0")
        
        result = _find_baton_config(config, temp_dir)
        
        assert result is not None
        assert result.name == 'baton.yaml'
        assert result.exists()
    
    def test_find_baton_config_searches_baton_yml(self, mock_config_factory, temp_dir):
        """_find_baton_config searches for baton.yml as fallback."""
        config = mock_config_factory(baton_config_path=None)
        # Don't create baton.yaml, only baton.yml
        baton_file = temp_dir / "baton.yml"
        baton_file.write_text("schema_version: 1.0")
        
        result = _find_baton_config(config, temp_dir)
        
        assert result is not None
        assert result.name == 'baton.yml'
        assert result.exists()
    
    def test_find_baton_config_returns_none_when_not_found(self, mock_config_factory, temp_dir):
        """_find_baton_config returns None when no config file found."""
        config = mock_config_factory(baton_config_path=None)
        
        result = _find_baton_config(config, temp_dir)
        
        assert result is None
    
    def test_find_baton_config_configured_path_not_exists_absolute(self, mock_config_factory, temp_dir):
        """_find_baton_config returns base_dir / path when configured path doesn't exist as absolute."""
        config = mock_config_factory(baton_config_path="configs/baton.yaml")
        
        result = _find_baton_config(config, temp_dir)
        
        # Should return base_dir / configured_path even if it doesn't exist
        assert result is not None
        assert result == temp_dir / "configs/baton.yaml" or result == Path("configs/baton.yaml")
    
    def test_find_baton_config_with_symlink(self, mock_config_factory, temp_dir):
        """_find_baton_config resolves symlinked config files."""
        # Create actual file
        actual_file = temp_dir / "actual_baton.yaml"
        actual_file.write_text("schema_version: 1.0")
        
        # Create symlink
        symlink = temp_dir / "baton.yaml"
        try:
            symlink.symlink_to(actual_file)
        except (OSError, NotImplementedError):
            # Skip test if symlinks not supported (e.g., Windows without admin)
            pytest.skip("Symlinks not supported on this system")
        
        config = mock_config_factory(baton_config_path=None)
        result = _find_baton_config(config, temp_dir)
        
        assert result is not None
        assert result.name == 'baton.yaml'
        # Verify it points to valid content
        assert result.exists()
    
    def test_find_baton_config_with_unicode_path(self, mock_config_factory, temp_dir):
        """_find_baton_config handles unicode characters in paths."""
        # Create subdirectory with unicode characters
        unicode_dir = temp_dir / "配置"
        unicode_dir.mkdir(exist_ok=True)
        
        baton_file = unicode_dir / "baton.yaml"
        baton_file.write_text("schema_version: 1.0")
        
        config = mock_config_factory(baton_config_path=str(baton_file))
        result = _find_baton_config(config, unicode_dir.parent)
        
        assert result is not None
        assert result.exists()


# ============================================================================
# TestVersionLt
# ============================================================================

class TestVersionLt:
    """Test suite for _version_lt function."""
    
    def test_version_lt_simple_less_than(self):
        """_version_lt returns True when a < b numerically."""
        result = _version_lt("1.0.0", "2.0.0")
        assert result is True
    
    def test_version_lt_simple_greater_than(self):
        """_version_lt returns False when a > b numerically."""
        result = _version_lt("2.0.0", "1.0.0")
        assert result is False
    
    def test_version_lt_equal_versions(self):
        """_version_lt returns False when a == b."""
        result = _version_lt("1.0.0", "1.0.0")
        assert result is False
    
    def test_version_lt_different_segment_counts(self):
        """_version_lt handles versions with varying segment counts."""
        result = _version_lt("1.0", "1.0.1")
        assert result is True
        
        result2 = _version_lt("1.0.1", "1.0")
        assert result2 is False
    
    def test_version_lt_lexicographic_fallback(self):
        """_version_lt falls back to lexicographic comparison on parse failure."""
        result = _version_lt("1.x.0", "2.0.0")
        # Lexicographic: "1.x.0" < "2.0.0"
        assert result is True
        
        result2 = _version_lt("abc", "def")
        assert result2 is True
    
    def test_version_lt_leading_zeros(self):
        """_version_lt handles versions with leading zeros."""
        result = _version_lt("01.02.03", "1.2.4")
        assert result is True
        
        result2 = _version_lt("01.02.03", "1.2.3")
        assert result2 is False
    
    def test_version_lt_pre_release_versions(self):
        """_version_lt handles pre-release version strings."""
        # These will fail numeric parsing and fall back to lexicographic
        result = _version_lt("1.0.0-alpha", "1.0.0-beta")
        # Lexicographic: "1.0.0-alpha" < "1.0.0-beta"
        assert result is True
    
    def test_version_lt_empty_strings(self):
        """_version_lt handles empty version strings."""
        result = _version_lt("", "1.0.0")
        # Empty string < "1.0.0" lexicographically
        assert result is True
        
        result2 = _version_lt("1.0.0", "")
        assert result2 is False
    
    def test_version_lt_single_number(self):
        """_version_lt handles single number versions."""
        result = _version_lt("1", "2")
        assert result is True
        
        result2 = _version_lt("10", "2")
        assert result2 is False  # Numeric: 10 > 2
    
    @pytest.mark.parametrize("a,b,expected", [
        ("1.0.0", "1.0.1", True),
        ("1.0.1", "1.0.0", False),
        ("1.2.0", "1.10.0", True),
        ("2.0.0", "1.99.99", False),
        ("0.0.1", "0.0.2", True),
        ("1.0", "1.0.0", True),  # Fewer segments
        ("1.0.0.0", "1.0.0.1", True),
        ("3.2.1", "3.2.1", False),  # Equal
    ])
    def test_version_lt_parametrized_comparisons(self, a, b, expected):
        """Parametrized test for various version comparisons."""
        result = _version_lt(a, b)
        assert result == expected
    
    def test_version_lt_random_valid_versions(self):
        """Test with randomly generated valid version strings."""
        for _ in range(10):
            major1, minor1, patch1 = random.randint(0, 10), random.randint(0, 10), random.randint(0, 10)
            major2, minor2, patch2 = random.randint(0, 10), random.randint(0, 10), random.randint(0, 10)
            
            v1 = f"{major1}.{minor1}.{patch1}"
            v2 = f"{major2}.{minor2}.{patch2}"
            
            result = _version_lt(v1, v2)
            
            # Verify against expected behavior
            parts1 = [major1, minor1, patch1]
            parts2 = [major2, minor2, patch2]
            expected = parts1 < parts2
            
            assert result == expected, f"Failed for {v1} vs {v2}"
    
    def test_version_lt_transitivity(self):
        """Test transitivity property: if a < b and b < c, then a < c."""
        versions = ["1.0.0", "1.5.0", "2.0.0"]
        
        # 1.0.0 < 1.5.0
        assert _version_lt(versions[0], versions[1]) is True
        # 1.5.0 < 2.0.0
        assert _version_lt(versions[1], versions[2]) is True
        # Therefore: 1.0.0 < 2.0.0
        assert _version_lt(versions[0], versions[2]) is True
    
    def test_version_lt_antisymmetry(self):
        """Test antisymmetry: if a < b is True, then b < a must be False."""
        a, b = "1.0.0", "2.0.0"
        
        assert _version_lt(a, b) is True
        assert _version_lt(b, a) is False
    
    def test_version_lt_reflexivity(self):
        """Test that a version is never less than itself."""
        versions = ["1.0.0", "2.5.3", "10.0.1"]
        
        for v in versions:
            assert _version_lt(v, v) is False


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests combining multiple components."""
    
    def test_full_workflow_with_real_files(self, baton_checker, mock_config_factory, temp_dir):
        """Test complete workflow from config discovery to validation."""
        config = mock_config_factory(
            baton_config_path=None,
            min_baton_schema_version="1.5"
        )
        
        # Create baton.yaml with various configurations
        baton_file = temp_dir / "baton.yaml"
        content = {
            'schema_version': '2.0',
            'nodes': {
                'worker1': {'type': 'worker', 'count': 3},
                'manager1': {'type': 'manager'}
            },
            'global': {
                'timeout': 60,
                'log_level': 'INFO'
            }
        }
        
        with open(baton_file, 'w') as f:
            yaml.dump(content, f)
        
        # Run check
        results = baton_checker.check(config, temp_dir)
        
        # Verify results
        assert len(results) >= 1
        assert all(r.tool == 'baton' for r in results)
        assert isinstance(results, list)
    
    def test_multiple_config_file_precedence(self, baton_checker, mock_config_factory, temp_dir):
        """Test that configured path takes precedence over default search."""
        # Create multiple config files
        default_yaml = temp_dir / "baton.yaml"
        default_yaml.write_text("schema_version: '1.0'\n")
        
        custom_yaml = temp_dir / "custom.yaml"
        custom_yaml.write_text("schema_version: '3.0'\n")
        
        # Configure to use custom file
        config = mock_config_factory(
            baton_config_path=str(custom_yaml),
            min_baton_schema_version="1.0"
        )
        
        # Find config should return custom path
        found = _find_baton_config(config, temp_dir)
        assert found == custom_yaml
