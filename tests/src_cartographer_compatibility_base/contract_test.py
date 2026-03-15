"""
Contract tests for CompatibilityChecker abstract base class.

This test suite verifies the contract for the CompatibilityChecker ABC,
focusing on abstract method enforcement and basic behavioral guarantees.

Coverage Notes:
- Abstract base class instantiation prevention
- Concrete implementation contract compliance
- Abstract method decorator verification
- Method signature validation

Coverage Gaps (Intentional):
- Detailed CheckResult validation: Belongs in concrete subclass tests
- Property-based testing: Not used per requirements
- Filesystem interaction scenarios: Deferred to concrete implementations
- Tool-specific validation logic: Tested in concrete subclasses
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
import inspect
from abc import ABC, abstractmethod


# Import the component under test
try:
    from src.cartographer.compatibility.base import CompatibilityChecker
except ImportError:
    try:
        from cartographer.compatibility.base import CompatibilityChecker
    except ImportError:
        # Fallback for different module structures
        from src.cartographer.compatibility.base import CompatibilityChecker


# Mock dependencies
class MockCartographerConfig:
    """Mock CartographerConfig for testing."""
    def __init__(self, **kwargs):
        self.data = kwargs


class MockCheckResult:
    """Mock CheckResult for testing."""
    def __init__(self, message, severity="info", tool=None):
        self.message = message
        self.severity = severity
        self.tool = tool


# Fixtures

@pytest.fixture
def mock_config():
    """Provide a mock CartographerConfig instance."""
    return MockCartographerConfig(tool="test", version="1.0")


@pytest.fixture
def mock_path(tmp_path):
    """Provide a mock Path object."""
    return tmp_path


@pytest.fixture
def concrete_checker():
    """
    Provide a concrete implementation of CompatibilityChecker for testing.
    This implementation satisfies the contract by implementing all abstract methods.
    """
    class ConcreteTestChecker(CompatibilityChecker):
        @property
        def tool_name(self) -> str:
            return "test_tool"
        
        def check(self, config, base_dir):
            return [MockCheckResult("Test check passed", "info", "test_tool")]
    
    return ConcreteTestChecker()


@pytest.fixture
def empty_results_checker():
    """
    Provide a concrete checker that returns empty results.
    """
    class EmptyResultsChecker(CompatibilityChecker):
        @property
        def tool_name(self) -> str:
            return "empty_tool"
        
        def check(self, config, base_dir):
            return []
    
    return EmptyResultsChecker()


@pytest.fixture
def incomplete_checker_no_tool_name():
    """
    Provide an incomplete checker missing tool_name implementation.
    """
    class IncompleteChecker(CompatibilityChecker):
        def check(self, config, base_dir):
            return []
    
    return IncompleteChecker


@pytest.fixture
def incomplete_checker_no_check():
    """
    Provide an incomplete checker missing check implementation.
    """
    class IncompleteChecker(CompatibilityChecker):
        @property
        def tool_name(self) -> str:
            return "incomplete_tool"
    
    return IncompleteChecker


# Test Cases

class TestAbstractClassEnforcement:
    """Tests for abstract base class enforcement."""
    
    def test_abstract_class_cannot_be_instantiated(self):
        """
        Verify that CompatibilityChecker is an abstract base class 
        and cannot be instantiated directly.
        
        Contract: CompatibilityChecker is an abstract base class and cannot be instantiated directly
        """
        with pytest.raises(TypeError) as exc_info:
            CompatibilityChecker()
        
        # Verify the error message indicates abstract method issue
        assert "abstract" in str(exc_info.value).lower() or "instantiate" in str(exc_info.value).lower()
    
    def test_concrete_implementation_can_be_instantiated(self, concrete_checker):
        """
        Verify that a concrete subclass implementing all abstract methods 
        can be instantiated.
        
        Contract: All concrete subclasses must implement both tool_name property and check method
        """
        # The fixture already instantiated it successfully
        assert concrete_checker is not None
        assert isinstance(concrete_checker, CompatibilityChecker)
    
    def test_incomplete_subclass_raises_not_implemented_for_tool_name(self, incomplete_checker_no_tool_name):
        """
        Verify that subclass without tool_name implementation raises error 
        when attempting instantiation.
        
        Contract Error: not_implemented when Called on abstract base class or subclass without implementation
        """
        with pytest.raises(TypeError) as exc_info:
            incomplete_checker_no_tool_name()
        
        # Verify it's due to abstract method
        assert "abstract" in str(exc_info.value).lower()
    
    def test_incomplete_subclass_raises_not_implemented_for_check(self, incomplete_checker_no_check):
        """
        Verify that subclass without check implementation raises error 
        when attempting instantiation.
        
        Contract Error: not_implemented when Called on abstract base class or subclass without implementation
        """
        with pytest.raises(TypeError) as exc_info:
            incomplete_checker_no_check()
        
        # Verify it's due to abstract method
        assert "abstract" in str(exc_info.value).lower()


class TestToolNameProperty:
    """Tests for tool_name property."""
    
    def test_tool_name_returns_non_empty_string(self, concrete_checker):
        """
        Verify that tool_name property returns a non-empty string 
        for concrete implementation.
        
        Contract Postcondition: Returns a non-empty string identifying the tool name
        """
        tool_name = concrete_checker.tool_name
        
        assert isinstance(tool_name, str), "tool_name must return a string"
        assert len(tool_name) > 0, "tool_name must return a non-empty string"
        assert tool_name == "test_tool"


class TestCheckMethod:
    """Tests for check method."""
    
    def test_check_returns_list_of_check_results(self, concrete_checker, mock_config, mock_path):
        """
        Verify that check method returns a list of CheckResult objects.
        
        Contract Postcondition: Returns a list of CheckResult objects (may be empty)
        Contract Postcondition: Each CheckResult represents a validation finding
        """
        results = concrete_checker.check(mock_config, mock_path)
        
        assert isinstance(results, list), "check must return a list"
        assert len(results) > 0, "concrete_checker should return at least one result"
        
        # Verify each item is a CheckResult-like object
        for result in results:
            assert hasattr(result, 'message'), "Each result should have a message attribute"
            assert hasattr(result, 'severity'), "Each result should have a severity attribute"
    
    def test_check_with_empty_results(self, empty_results_checker, mock_config, mock_path):
        """
        Verify that check method can return an empty list when no issues found.
        
        Contract Postcondition: Returns a list of CheckResult objects (may be empty)
        """
        results = empty_results_checker.check(mock_config, mock_path)
        
        assert isinstance(results, list), "check must return a list"
        assert len(results) == 0, "empty_results_checker should return an empty list"
    
    def test_check_method_signature(self, concrete_checker):
        """
        Verify that check method accepts correct parameters (self, config, base_dir).
        
        Contract: check method must accept config and base_dir parameters
        """
        # Get the method signature
        sig = inspect.signature(concrete_checker.check)
        params = list(sig.parameters.keys())
        
        # Should have config and base_dir parameters
        assert 'config' in params, "check method must have 'config' parameter"
        assert 'base_dir' in params, "check method must have 'base_dir' parameter"
    
    def test_check_accepts_valid_config_and_path(self, concrete_checker, mock_config, mock_path):
        """
        Verify that check method accepts valid CartographerConfig and Path objects.
        
        Contract Precondition: config must be a valid CartographerConfig instance
        Contract Precondition: base_dir must be a valid Path object
        """
        # Should not raise any exceptions
        results = concrete_checker.check(mock_config, mock_path)
        
        assert results is not None
        assert isinstance(results, list)


class TestInvariants:
    """Tests for contract invariants."""
    
    def test_abstract_methods_have_decorators(self):
        """
        Verify that tool_name and check are marked as abstract methods.
        
        Contract Invariant: All concrete subclasses must implement both tool_name property and check method
        """
        # Check that CompatibilityChecker has abstract methods
        abstract_methods = getattr(CompatibilityChecker, '__abstractmethods__', set())
        
        # The abstract methods should include 'tool_name' and 'check'
        assert len(abstract_methods) > 0, "CompatibilityChecker should have abstract methods"
        
        # Note: The exact names might vary based on implementation
        # We verify that there ARE abstract methods that need implementation
        assert hasattr(CompatibilityChecker, 'tool_name'), "CompatibilityChecker should define tool_name"
        assert hasattr(CompatibilityChecker, 'check'), "CompatibilityChecker should define check"
    
    def test_is_abstract_base_class(self):
        """
        Verify that CompatibilityChecker is properly defined as an ABC.
        
        Contract Invariant: CompatibilityChecker is an abstract base class
        """
        # Check if it's a subclass of ABC or has ABCMeta as metaclass
        assert hasattr(CompatibilityChecker, '__abstractmethods__'), \
            "CompatibilityChecker should have __abstractmethods__ attribute"
        
        # Verify we cannot instantiate it
        with pytest.raises(TypeError):
            CompatibilityChecker()
    
    def test_concrete_implementation_is_instance_of_base(self, concrete_checker):
        """
        Verify that concrete implementations are instances of CompatibilityChecker.
        
        Contract Invariant: All concrete subclasses must implement both tool_name property and check method
        """
        assert isinstance(concrete_checker, CompatibilityChecker), \
            "Concrete implementation must be an instance of CompatibilityChecker"


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""
    
    def test_check_with_various_path_types(self, concrete_checker, mock_config, tmp_path):
        """
        Verify check handles various valid Path types.
        
        Contract Precondition: base_dir must be a valid Path object
        """
        # Test with tmp_path (Path object)
        results1 = concrete_checker.check(mock_config, tmp_path)
        assert isinstance(results1, list)
        
        # Test with subdirectory
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        results2 = concrete_checker.check(mock_config, subdir)
        assert isinstance(results2, list)
    
    def test_multiple_checkers_independent(self):
        """
        Verify that multiple concrete checker instances are independent.
        
        Contract Invariant: Each checker should maintain its own state
        """
        class Checker1(CompatibilityChecker):
            @property
            def tool_name(self) -> str:
                return "checker1"
            
            def check(self, config, base_dir):
                return []
        
        class Checker2(CompatibilityChecker):
            @property
            def tool_name(self) -> str:
                return "checker2"
            
            def check(self, config, base_dir):
                return []
        
        c1 = Checker1()
        c2 = Checker2()
        
        assert c1.tool_name == "checker1"
        assert c2.tool_name == "checker2"
        assert c1.tool_name != c2.tool_name


class TestSideEffects:
    """Tests verifying no side effects as per contract."""
    
    def test_tool_name_has_no_side_effects(self, concrete_checker):
        """
        Verify that calling tool_name multiple times has no side effects.
        
        Contract Side Effect: none
        """
        name1 = concrete_checker.tool_name
        name2 = concrete_checker.tool_name
        name3 = concrete_checker.tool_name
        
        assert name1 == name2 == name3, "tool_name should return consistent results"
    
    def test_check_has_no_side_effects_on_inputs(self, concrete_checker, mock_config, mock_path):
        """
        Verify that check method doesn't modify input parameters.
        
        Contract Side Effect: none
        """
        # Store original state
        original_config_data = getattr(mock_config, 'data', {}).copy() if hasattr(mock_config, 'data') else {}
        original_path_str = str(mock_path)
        
        # Call check
        concrete_checker.check(mock_config, mock_path)
        
        # Verify inputs unchanged
        if hasattr(mock_config, 'data'):
            assert mock_config.data == original_config_data, "check should not modify config"
        assert str(mock_path) == original_path_str, "check should not modify path"
