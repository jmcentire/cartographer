"""
Contract Test Suite for Cartographer Models
Generated for contract version 1

This test suite validates the behavior of cartographer models including:
- Enums: Confidence, Severity, ComponentType, BackendType
- Structs: DiscoveredField, DiscoveredModel, DiscoveredRoute, DiscoveredComponent,
  DiscoveredPactKey, DiscoveredEnvVar, DiscoveredSensitiveField, DiscoveryResult,
  CheckResult, CompatibilityReport, DraftField, DraftArtifact
- Functions: score_pct, has_failures
- Invariants: Enum ordering, total calculation, BaseModel inheritance

Coverage target: >95%
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import Any
import random
from datetime import datetime

# Import the component under test
from src.cartographer.models import *


# ============================================================================
# FIXTURES AND FACTORY FUNCTIONS
# ============================================================================

@pytest.fixture
def sample_discovered_field():
    """Factory for DiscoveredField instances"""
    return DiscoveredField(
        name="user_id",
        type="int",
        confidence=Confidence.HIGH,
        note="Primary key",
        classification_hint="identifier"
    )


@pytest.fixture
def sample_discovered_model():
    """Factory for DiscoveredModel instances"""
    return DiscoveredModel(
        name="User",
        source_file="models.py",
        line=10,
        orm="SQLAlchemy",
        fields=[],
        confidence=Confidence.HIGH
    )


@pytest.fixture
def sample_discovered_route():
    """Factory for DiscoveredRoute instances"""
    return DiscoveredRoute(
        path="/api/users",
        method="GET",
        handler="get_users",
        source_file="routes.py",
        line=25,
        framework="FastAPI",
        confidence=Confidence.HIGH
    )


@pytest.fixture
def sample_discovered_component():
    """Factory for DiscoveredComponent instances"""
    return DiscoveredComponent(
        name="UserService",
        source_file="service.py",
        line=15,
        type=ComponentType.SERVICE,
        public_methods=["create_user", "get_user"],
        dependencies=["database", "cache"],
        confidence=Confidence.HIGH,
        note=None
    )


@pytest.fixture
def sample_discovered_pact_key():
    """Factory for DiscoveredPactKey instances"""
    return DiscoveredPactKey(
        key="user.created",
        source_file="events.py",
        line=42,
        confidence=Confidence.MEDIUM
    )


@pytest.fixture
def sample_discovered_env_var():
    """Factory for DiscoveredEnvVar instances"""
    return DiscoveredEnvVar(
        name="DATABASE_URL",
        source_file="config.py",
        line=8,
        backend_hint="POSTGRES",
        confidence=Confidence.HIGH
    )


@pytest.fixture
def sample_discovered_sensitive_field():
    """Factory for DiscoveredSensitiveField instances"""
    return DiscoveredSensitiveField(
        field_name="ssn",
        source_file="models.py",
        line=20,
        pattern_matched="ssn|social_security",
        classification_hint="PII",
        confidence=Confidence.HIGH
    )


@pytest.fixture
def sample_check_result():
    """Factory for CheckResult instances"""
    return CheckResult(
        check_id="CHK001",
        target="UserService",
        severity=Severity.WARN,
        status="warning",
        message="Deprecated method used",
        tool="linter"
    )


@pytest.fixture
def sample_compatibility_report():
    """Factory for CompatibilityReport instances"""
    return CompatibilityReport(
        generated="2024-01-01T00:00:00Z",
        checks=[],
        score_pass=7,
        score_warn=2,
        score_fail=1,
        total=10,
        recommendations=[]
    )


@pytest.fixture
def sample_discovery_result():
    """Factory for DiscoveryResult instances"""
    return DiscoveryResult(
        models=[],
        routes=[],
        components=[],
        pact_keys=[],
        env_vars=[],
        sensitive_fields=[]
    )


@pytest.fixture
def sample_draft_field():
    """Factory for DraftField instances"""
    return DraftField(
        value="test_value",
        confidence=Confidence.MEDIUM,
        note="Auto-generated"
    )


@pytest.fixture
def sample_draft_artifact():
    """Factory for DraftArtifact instances"""
    return DraftArtifact(
        _draft=True,
        _generated_by="scanner",
        tool="cartographer",
        artifact_type="model",
        path="models/user.py",
        content={}
    )


# ============================================================================
# ENUM TESTS
# ============================================================================

class TestConfidenceEnum:
    """Test suite for Confidence enum"""
    
    def test_confidence_enum_members(self):
        """Test Confidence enum has all required members"""
        assert hasattr(Confidence, 'HIGH')
        assert hasattr(Confidence, 'MEDIUM')
        assert hasattr(Confidence, 'LOW')
        
        # Verify all members are present
        members = [e.name for e in Confidence]
        assert 'HIGH' in members
        assert 'MEDIUM' in members
        assert 'LOW' in members
    
    def test_confidence_enum_string_values(self):
        """Test all Confidence enum values are strings"""
        for member in Confidence:
            assert isinstance(member.value, str)
    
    def test_confidence_enum_access(self):
        """Test Confidence enum members can be accessed"""
        high = Confidence.HIGH
        medium = Confidence.MEDIUM
        low = Confidence.LOW
        
        assert high is not None
        assert medium is not None
        assert low is not None


class TestSeverityEnum:
    """Test suite for Severity enum"""
    
    def test_severity_enum_members(self):
        """Test Severity enum has all required members"""
        assert hasattr(Severity, 'FAIL')
        assert hasattr(Severity, 'WARN')
        assert hasattr(Severity, 'INFO')
        
        members = [e.name for e in Severity]
        assert 'FAIL' in members
        assert 'WARN' in members
        assert 'INFO' in members
    
    def test_severity_enum_string_values(self):
        """Test all Severity enum values are strings"""
        for member in Severity:
            assert isinstance(member.value, str)


class TestComponentTypeEnum:
    """Test suite for ComponentType enum"""
    
    def test_component_type_enum_members(self):
        """Test ComponentType enum has all required members"""
        expected_members = ['SERVICE', 'LIBRARY', 'WORKER', 'EGRESS', 'INGRESS']
        members = [e.name for e in ComponentType]
        
        for expected in expected_members:
            assert expected in members
    
    def test_component_type_enum_string_values(self):
        """Test all ComponentType enum values are strings"""
        for member in ComponentType:
            assert isinstance(member.value, str)


class TestBackendTypeEnum:
    """Test suite for BackendType enum"""
    
    def test_backend_type_enum_members(self):
        """Test BackendType enum has all required members"""
        expected_members = [
            'POSTGRES', 'MYSQL', 'SQLITE', 'MONGODB', 'REDIS',
            'S3', 'DYNAMODB', 'KAFKA', 'RABBITMQ', 'SQS'
        ]
        members = [e.name for e in BackendType]
        
        for expected in expected_members:
            assert expected in members
    
    def test_backend_type_enum_string_values(self):
        """Test all BackendType enum values are strings"""
        for member in BackendType:
            assert isinstance(member.value, str)


# ============================================================================
# STRUCT/MODEL TESTS
# ============================================================================

class TestDiscoveredField:
    """Test suite for DiscoveredField struct"""
    
    def test_discovered_field_creation(self):
        """Test DiscoveredField can be created with all fields"""
        field = DiscoveredField(
            name="user_id",
            type="int",
            confidence=Confidence.HIGH,
            note="Primary key",
            classification_hint="identifier"
        )
        
        assert field.name == "user_id"
        assert field.type == "int"
        assert field.confidence == Confidence.HIGH
        assert field.note == "Primary key"
        assert field.classification_hint == "identifier"
    
    def test_discovered_field_optional_fields(self):
        """Test DiscoveredField with optional fields as None"""
        field = DiscoveredField(
            name="field1",
            type=None,
            confidence=Confidence.MEDIUM,
            note=None,
            classification_hint=None
        )
        
        assert field.name == "field1"
        assert field.type is None
        assert field.note is None
        assert field.classification_hint is None
        assert field.confidence == Confidence.MEDIUM
    
    def test_discovered_field_inherits_basemodel(self):
        """Test DiscoveredField inherits from BaseModel"""
        from pydantic import BaseModel
        field = DiscoveredField(
            name="test",
            type=None,
            confidence=Confidence.LOW,
            note=None,
            classification_hint=None
        )
        assert isinstance(field, BaseModel)


class TestDiscoveredModel:
    """Test suite for DiscoveredModel struct"""
    
    def test_discovered_model_creation(self):
        """Test DiscoveredModel creation with fields"""
        field1 = DiscoveredField(
            name="id",
            type="int",
            confidence=Confidence.HIGH,
            note=None,
            classification_hint=None
        )
        
        model = DiscoveredModel(
            name="User",
            source_file="models.py",
            line=10,
            orm="SQLAlchemy",
            fields=[field1],
            confidence=Confidence.HIGH
        )
        
        assert model.name == "User"
        assert model.source_file == "models.py"
        assert model.line == 10
        assert model.orm == "SQLAlchemy"
        assert len(model.fields) == 1
        assert model.confidence == Confidence.HIGH
    
    def test_discovered_model_empty_fields(self):
        """Test DiscoveredModel with empty fields list"""
        model = DiscoveredModel(
            name="EmptyModel",
            source_file="test.py",
            line=1,
            orm=None,
            fields=[],
            confidence=Confidence.LOW
        )
        
        assert len(model.fields) == 0
        assert model.orm is None
    
    def test_discovered_model_positive_line_number(self):
        """Test DiscoveredModel with positive line number"""
        model = DiscoveredModel(
            name="Model",
            source_file="test.py",
            line=1,
            orm=None,
            fields=[],
            confidence=Confidence.HIGH
        )
        assert model.line > 0


class TestDiscoveredRoute:
    """Test suite for DiscoveredRoute struct"""
    
    def test_discovered_route_creation(self):
        """Test DiscoveredRoute creation"""
        route = DiscoveredRoute(
            path="/api/users",
            method="GET",
            handler="get_users",
            source_file="routes.py",
            line=25,
            framework="FastAPI",
            confidence=Confidence.HIGH
        )
        
        assert route.path == "/api/users"
        assert route.method == "GET"
        assert route.handler == "get_users"
        assert route.source_file == "routes.py"
        assert route.line == 25
        assert route.framework == "FastAPI"
        assert route.confidence == Confidence.HIGH
    
    def test_discovered_route_various_methods(self):
        """Test DiscoveredRoute with various HTTP methods"""
        methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]
        
        for method in methods:
            route = DiscoveredRoute(
                path=f"/api/{method.lower()}",
                method=method,
                handler=f"handle_{method.lower()}",
                source_file="routes.py",
                line=1,
                framework="Flask",
                confidence=Confidence.MEDIUM
            )
            assert route.method == method


class TestDiscoveredComponent:
    """Test suite for DiscoveredComponent struct"""
    
    def test_discovered_component_creation(self):
        """Test DiscoveredComponent creation with dependencies"""
        component = DiscoveredComponent(
            name="UserService",
            source_file="service.py",
            line=15,
            type=ComponentType.SERVICE,
            public_methods=["create", "read", "update", "delete"],
            dependencies=["database", "cache"],
            confidence=Confidence.HIGH,
            note=None
        )
        
        assert component.name == "UserService"
        assert component.type == ComponentType.SERVICE
        assert len(component.public_methods) == 4
        assert len(component.dependencies) == 2
        assert component.confidence == Confidence.HIGH
    
    def test_discovered_component_all_types(self):
        """Test DiscoveredComponent with all ComponentType values"""
        types = [
            ComponentType.SERVICE,
            ComponentType.LIBRARY,
            ComponentType.WORKER,
            ComponentType.EGRESS,
            ComponentType.INGRESS
        ]
        
        for comp_type in types:
            component = DiscoveredComponent(
                name=f"Test{comp_type.name}",
                source_file="test.py",
                line=1,
                type=comp_type,
                public_methods=[],
                dependencies=[],
                confidence=Confidence.MEDIUM,
                note=None
            )
            assert component.type == comp_type


class TestDiscoveredPactKey:
    """Test suite for DiscoveredPactKey struct"""
    
    def test_discovered_pact_key_creation(self):
        """Test DiscoveredPactKey creation"""
        pact = DiscoveredPactKey(
            key="user.created",
            source_file="events.py",
            line=42,
            confidence=Confidence.MEDIUM
        )
        
        assert pact.key == "user.created"
        assert pact.source_file == "events.py"
        assert pact.line == 42
        assert pact.confidence == Confidence.MEDIUM
    
    def test_discovered_pact_key_various_keys(self):
        """Test DiscoveredPactKey with various key patterns"""
        keys = [
            "user.created",
            "order.updated",
            "payment.processed",
            "notification.sent"
        ]
        
        for key in keys:
            pact = DiscoveredPactKey(
                key=key,
                source_file="events.py",
                line=1,
                confidence=Confidence.HIGH
            )
            assert pact.key == key


class TestDiscoveredEnvVar:
    """Test suite for DiscoveredEnvVar struct"""
    
    def test_discovered_env_var_creation(self):
        """Test DiscoveredEnvVar creation with backend hint"""
        env_var = DiscoveredEnvVar(
            name="DATABASE_URL",
            source_file="config.py",
            line=8,
            backend_hint="POSTGRES",
            confidence=Confidence.HIGH
        )
        
        assert env_var.name == "DATABASE_URL"
        assert env_var.source_file == "config.py"
        assert env_var.line == 8
        assert env_var.backend_hint == "POSTGRES"
        assert env_var.confidence == Confidence.HIGH
    
    def test_discovered_env_var_no_backend_hint(self):
        """Test DiscoveredEnvVar without backend hint"""
        env_var = DiscoveredEnvVar(
            name="API_KEY",
            source_file="config.py",
            line=5,
            backend_hint=None,
            confidence=Confidence.MEDIUM
        )
        
        assert env_var.backend_hint is None


class TestDiscoveredSensitiveField:
    """Test suite for DiscoveredSensitiveField struct"""
    
    def test_discovered_sensitive_field_creation(self):
        """Test DiscoveredSensitiveField creation"""
        field = DiscoveredSensitiveField(
            field_name="ssn",
            source_file="models.py",
            line=20,
            pattern_matched="ssn|social_security",
            classification_hint="PII",
            confidence=Confidence.HIGH
        )
        
        assert field.field_name == "ssn"
        assert field.source_file == "models.py"
        assert field.line == 20
        assert field.pattern_matched == "ssn|social_security"
        assert field.classification_hint == "PII"
        assert field.confidence == Confidence.HIGH
    
    def test_discovered_sensitive_field_various_pii(self):
        """Test DiscoveredSensitiveField with various PII types"""
        pii_fields = [
            ("ssn", "PII"),
            ("credit_card", "FINANCIAL"),
            ("email", "CONTACT"),
            ("password", "CREDENTIAL")
        ]
        
        for field_name, classification in pii_fields:
            field = DiscoveredSensitiveField(
                field_name=field_name,
                source_file="models.py",
                line=1,
                pattern_matched=field_name,
                classification_hint=classification,
                confidence=Confidence.HIGH
            )
            assert field.field_name == field_name
            assert field.classification_hint == classification


class TestDiscoveryResult:
    """Test suite for DiscoveryResult struct"""
    
    def test_discovery_result_creation(self):
        """Test DiscoveryResult aggregates all discovery types"""
        result = DiscoveryResult(
            models=[],
            routes=[],
            components=[],
            pact_keys=[],
            env_vars=[],
            sensitive_fields=[]
        )
        
        assert isinstance(result.models, list)
        assert isinstance(result.routes, list)
        assert isinstance(result.components, list)
        assert isinstance(result.pact_keys, list)
        assert isinstance(result.env_vars, list)
        assert isinstance(result.sensitive_fields, list)
    
    def test_discovery_result_with_data(self):
        """Test DiscoveryResult with populated lists"""
        model = DiscoveredModel(
            name="User",
            source_file="models.py",
            line=1,
            orm=None,
            fields=[],
            confidence=Confidence.HIGH
        )
        
        route = DiscoveredRoute(
            path="/api/test",
            method="GET",
            handler="test",
            source_file="routes.py",
            line=1,
            framework="Flask",
            confidence=Confidence.HIGH
        )
        
        result = DiscoveryResult(
            models=[model],
            routes=[route],
            components=[],
            pact_keys=[],
            env_vars=[],
            sensitive_fields=[]
        )
        
        assert len(result.models) == 1
        assert len(result.routes) == 1
        assert result.models[0].name == "User"
        assert result.routes[0].path == "/api/test"


class TestCheckResult:
    """Test suite for CheckResult struct"""
    
    def test_check_result_creation(self):
        """Test CheckResult creation for compatibility check"""
        check = CheckResult(
            check_id="CHK001",
            target="UserService",
            severity=Severity.WARN,
            status="warning",
            message="Deprecated method used",
            tool="linter"
        )
        
        assert check.check_id == "CHK001"
        assert check.target == "UserService"
        assert check.severity == Severity.WARN
        assert check.status == "warning"
        assert check.message == "Deprecated method used"
        assert check.tool == "linter"
    
    def test_check_result_all_severities(self):
        """Test CheckResult with all severity levels"""
        severities = [Severity.FAIL, Severity.WARN, Severity.INFO]
        
        for severity in severities:
            check = CheckResult(
                check_id="CHK001",
                target="test",
                severity=severity,
                status="test",
                message="test message",
                tool="test_tool"
            )
            assert check.severity == severity


class TestCompatibilityReport:
    """Test suite for CompatibilityReport struct"""
    
    def test_compatibility_report_creation(self):
        """Test CompatibilityReport creation"""
        report = CompatibilityReport(
            generated="2024-01-01T00:00:00Z",
            checks=[],
            score_pass=5,
            score_warn=2,
            score_fail=1,
            total=8,
            recommendations=[]
        )
        
        assert report.generated == "2024-01-01T00:00:00Z"
        assert report.score_pass == 5
        assert report.score_warn == 2
        assert report.score_fail == 1
        assert report.total == 8
        assert isinstance(report.checks, list)
        assert isinstance(report.recommendations, list)
    
    def test_compatibility_report_with_checks(self):
        """Test CompatibilityReport with CheckResult objects"""
        check1 = CheckResult(
            check_id="CHK001",
            target="Service1",
            severity=Severity.FAIL,
            status="failed",
            message="Error",
            tool="tool1"
        )
        
        check2 = CheckResult(
            check_id="CHK002",
            target="Service2",
            severity=Severity.WARN,
            status="warning",
            message="Warning",
            tool="tool2"
        )
        
        report = CompatibilityReport(
            generated="2024-01-01T00:00:00Z",
            checks=[check1, check2],
            score_pass=0,
            score_warn=1,
            score_fail=1,
            total=2,
            recommendations=["Fix Service1"]
        )
        
        assert len(report.checks) == 2
        assert len(report.recommendations) == 1


class TestDraftField:
    """Test suite for DraftField struct"""
    
    def test_draft_field_creation(self):
        """Test DraftField creation with confidence"""
        draft = DraftField(
            value="test_value",
            confidence=Confidence.MEDIUM,
            note="Auto-generated"
        )
        
        assert draft.value == "test_value"
        assert draft.confidence == Confidence.MEDIUM
        assert draft.note == "Auto-generated"
    
    def test_draft_field_various_values(self):
        """Test DraftField with various value types"""
        values = [
            "string_value",
            123,
            {"key": "value"},
            ["list", "item"],
            True
        ]
        
        for val in values:
            draft = DraftField(
                value=val,
                confidence=Confidence.HIGH,
                note=None
            )
            assert draft.value == val


class TestDraftArtifact:
    """Test suite for DraftArtifact struct"""
    
    def test_draft_artifact_creation(self):
        """Test DraftArtifact base creation"""
        artifact = DraftArtifact(
            _draft=True,
            _generated_by="scanner",
            tool="cartographer",
            artifact_type="model",
            path="models/user.py",
            content={"name": "User", "fields": []}
        )
        
        assert artifact._draft is True
        assert artifact._generated_by == "scanner"
        assert artifact.tool == "cartographer"
        assert artifact.artifact_type == "model"
        assert artifact.path == "models/user.py"
        assert isinstance(artifact.content, dict)


# ============================================================================
# FUNCTION TESTS - score_pct
# ============================================================================

class TestScorePct:
    """Test suite for score_pct function"""
    
    def test_score_pct_happy_path(self):
        """Test score_pct returns correct percentage for typical compatibility report"""
        report = CompatibilityReport(
            generated="2024-01-01T00:00:00Z",
            checks=[],
            score_pass=7,
            score_warn=2,
            score_fail=1,
            total=10,
            recommendations=[]
        )
        
        result = report.score_pct()
        assert result == 70.0
    
    def test_score_pct_all_pass(self):
        """Test score_pct returns 100.0 when all checks pass"""
        report = CompatibilityReport(
            generated="2024-01-01T00:00:00Z",
            checks=[],
            score_pass=10,
            score_warn=0,
            score_fail=0,
            total=10,
            recommendations=[]
        )
        
        result = report.score_pct()
        assert result == 100.0
    
    def test_score_pct_empty_report(self):
        """Test score_pct returns 100.0 when total is 0 (no checks)"""
        report = CompatibilityReport(
            generated="2024-01-01T00:00:00Z",
            checks=[],
            score_pass=0,
            score_warn=0,
            score_fail=0,
            total=0,
            recommendations=[]
        )
        
        result = report.score_pct()
        assert result == 100.0
    
    def test_score_pct_all_fail(self):
        """Test score_pct returns 0.0 when all checks fail"""
        report = CompatibilityReport(
            generated="2024-01-01T00:00:00Z",
            checks=[],
            score_pass=0,
            score_warn=0,
            score_fail=10,
            total=10,
            recommendations=[]
        )
        
        result = report.score_pct()
        assert result == 0.0
    
    def test_score_pct_rounded(self):
        """Test score_pct rounds to 1 decimal place"""
        report = CompatibilityReport(
            generated="2024-01-01T00:00:00Z",
            checks=[],
            score_pass=2,
            score_warn=1,
            score_fail=0,
            total=3,
            recommendations=[]
        )
        
        result = report.score_pct()
        # 2/3 * 100 = 66.666... should round to 66.7
        assert result == 66.7
    
    def test_score_pct_range_postcondition(self):
        """Test score_pct always returns value in [0.0, 100.0] range"""
        test_cases = [
            (0, 0, 0, 0),  # Empty
            (10, 0, 0, 10),  # All pass
            (0, 0, 10, 10),  # All fail
            (5, 3, 2, 10),  # Mixed
            (1, 0, 0, 1),  # Single pass
            (0, 0, 1, 1),  # Single fail
        ]
        
        for pass_score, warn_score, fail_score, total in test_cases:
            report = CompatibilityReport(
                generated="2024-01-01T00:00:00Z",
                checks=[],
                score_pass=pass_score,
                score_warn=warn_score,
                score_fail=fail_score,
                total=total,
                recommendations=[]
            )
            
            result = report.score_pct()
            assert 0.0 <= result <= 100.0, f"Result {result} out of range for {test_cases}"
    
    def test_score_pct_one_pass_out_of_many(self):
        """Test score_pct with 1 pass out of 100"""
        report = CompatibilityReport(
            generated="2024-01-01T00:00:00Z",
            checks=[],
            score_pass=1,
            score_warn=0,
            score_fail=99,
            total=100,
            recommendations=[]
        )
        
        result = report.score_pct()
        assert result == 1.0


# ============================================================================
# FUNCTION TESTS - has_failures
# ============================================================================

class TestHasFailures:
    """Test suite for has_failures function"""
    
    def test_has_failures_with_failures(self):
        """Test has_failures returns True when score_fail > 0"""
        report = CompatibilityReport(
            generated="2024-01-01T00:00:00Z",
            checks=[],
            score_pass=5,
            score_warn=2,
            score_fail=3,
            total=10,
            recommendations=[]
        )
        
        result = report.has_failures()
        assert result is True
    
    def test_has_failures_no_failures(self):
        """Test has_failures returns False when score_fail = 0"""
        report = CompatibilityReport(
            generated="2024-01-01T00:00:00Z",
            checks=[],
            score_pass=8,
            score_warn=2,
            score_fail=0,
            total=10,
            recommendations=[]
        )
        
        result = report.has_failures()
        assert result is False
    
    def test_has_failures_edge_one(self):
        """Test has_failures returns True when score_fail = 1 (edge of boundary)"""
        report = CompatibilityReport(
            generated="2024-01-01T00:00:00Z",
            checks=[],
            score_pass=9,
            score_warn=0,
            score_fail=1,
            total=10,
            recommendations=[]
        )
        
        result = report.has_failures()
        assert result is True
    
    def test_has_failures_all_fail(self):
        """Test has_failures when all checks fail"""
        report = CompatibilityReport(
            generated="2024-01-01T00:00:00Z",
            checks=[],
            score_pass=0,
            score_warn=0,
            score_fail=100,
            total=100,
            recommendations=[]
        )
        
        result = report.has_failures()
        assert result is True
    
    def test_has_failures_empty_report(self):
        """Test has_failures on empty report"""
        report = CompatibilityReport(
            generated="2024-01-01T00:00:00Z",
            checks=[],
            score_pass=0,
            score_warn=0,
            score_fail=0,
            total=0,
            recommendations=[]
        )
        
        result = report.has_failures()
        assert result is False


# ============================================================================
# INVARIANT TESTS
# ============================================================================

class TestInvariants:
    """Test suite for contract invariants"""
    
    def test_compatibility_report_total_invariant(self):
        """Test invariant: total == score_pass + score_warn + score_fail"""
        test_cases = [
            (3, 4, 2, 9),
            (10, 0, 0, 10),
            (0, 0, 10, 10),
            (5, 5, 5, 15),
            (0, 0, 0, 0),
        ]
        
        for pass_s, warn_s, fail_s, total in test_cases:
            report = CompatibilityReport(
                generated="2024-01-01T00:00:00Z",
                checks=[],
                score_pass=pass_s,
                score_warn=warn_s,
                score_fail=fail_s,
                total=total,
                recommendations=[]
            )
            
            assert report.total == report.score_pass + report.score_warn + report.score_fail
    
    def test_enum_string_based(self):
        """Test invariant: All enum values are string-based"""
        # Test Confidence
        for member in Confidence:
            assert isinstance(member.value, str)
        
        # Test Severity
        for member in Severity:
            assert isinstance(member.value, str)
        
        # Test ComponentType
        for member in ComponentType:
            assert isinstance(member.value, str)
        
        # Test BackendType
        for member in BackendType:
            assert isinstance(member.value, str)
    
    def test_pydantic_basemodel_inheritance(self):
        """Test invariant: All Pydantic models inherit from BaseModel"""
        from pydantic import BaseModel
        
        # Test all struct types
        field = DiscoveredField(
            name="test",
            type=None,
            confidence=Confidence.HIGH,
            note=None,
            classification_hint=None
        )
        assert isinstance(field, BaseModel)
        
        model = DiscoveredModel(
            name="Test",
            source_file="test.py",
            line=1,
            orm=None,
            fields=[],
            confidence=Confidence.HIGH
        )
        assert isinstance(model, BaseModel)
        
        route = DiscoveredRoute(
            path="/test",
            method="GET",
            handler="test",
            source_file="test.py",
            line=1,
            framework="Flask",
            confidence=Confidence.HIGH
        )
        assert isinstance(route, BaseModel)
        
        component = DiscoveredComponent(
            name="Test",
            source_file="test.py",
            line=1,
            type=ComponentType.SERVICE,
            public_methods=[],
            dependencies=[],
            confidence=Confidence.HIGH,
            note=None
        )
        assert isinstance(component, BaseModel)
        
        check = CheckResult(
            check_id="CHK001",
            target="test",
            severity=Severity.INFO,
            status="ok",
            message="test",
            tool="test"
        )
        assert isinstance(check, BaseModel)
        
        report = CompatibilityReport(
            generated="2024-01-01T00:00:00Z",
            checks=[],
            score_pass=0,
            score_warn=0,
            score_fail=0,
            total=0,
            recommendations=[]
        )
        assert isinstance(report, BaseModel)
    
    def test_score_pct_range_invariant(self):
        """Test invariant: score_pct property returns value in range [0.0, 100.0]"""
        # Generate random test cases
        for _ in range(20):
            total = random.randint(0, 100)
            if total == 0:
                pass_s, warn_s, fail_s = 0, 0, 0
            else:
                pass_s = random.randint(0, total)
                remaining = total - pass_s
                warn_s = random.randint(0, remaining)
                fail_s = total - pass_s - warn_s
            
            report = CompatibilityReport(
                generated="2024-01-01T00:00:00Z",
                checks=[],
                score_pass=pass_s,
                score_warn=warn_s,
                score_fail=fail_s,
                total=total,
                recommendations=[]
            )
            
            result = report.score_pct()
            assert 0.0 <= result <= 100.0


# ============================================================================
# SERIALIZATION TESTS
# ============================================================================

class TestSerialization:
    """Test serialization/deserialization of models"""
    
    def test_discovered_field_serialization(self):
        """Test DiscoveredField can be serialized to dict"""
        field = DiscoveredField(
            name="test_field",
            type="str",
            confidence=Confidence.HIGH,
            note="test note",
            classification_hint="test"
        )
        
        # Pydantic models should support model_dump or dict()
        try:
            data = field.model_dump()
        except AttributeError:
            data = field.dict()
        
        assert data["name"] == "test_field"
        assert data["type"] == "str"
    
    def test_compatibility_report_serialization(self):
        """Test CompatibilityReport can be serialized to dict"""
        report = CompatibilityReport(
            generated="2024-01-01T00:00:00Z",
            checks=[],
            score_pass=5,
            score_warn=3,
            score_fail=2,
            total=10,
            recommendations=["Fix issue 1"]
        )
        
        try:
            data = report.model_dump()
        except AttributeError:
            data = report.dict()
        
        assert data["score_pass"] == 5
        assert data["total"] == 10
        assert "Fix issue 1" in data["recommendations"]


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests with complex nested objects"""
    
    def test_discovery_result_complete_integration(self):
        """Test DiscoveryResult with all nested types populated"""
        # Create nested objects
        field = DiscoveredField(
            name="id",
            type="int",
            confidence=Confidence.HIGH,
            note=None,
            classification_hint="identifier"
        )
        
        model = DiscoveredModel(
            name="User",
            source_file="models.py",
            line=10,
            orm="SQLAlchemy",
            fields=[field],
            confidence=Confidence.HIGH
        )
        
        route = DiscoveredRoute(
            path="/api/users",
            method="GET",
            handler="get_users",
            source_file="routes.py",
            line=25,
            framework="FastAPI",
            confidence=Confidence.HIGH
        )
        
        component = DiscoveredComponent(
            name="UserService",
            source_file="service.py",
            line=15,
            type=ComponentType.SERVICE,
            public_methods=["create_user"],
            dependencies=["database"],
            confidence=Confidence.HIGH,
            note=None
        )
        
        pact_key = DiscoveredPactKey(
            key="user.created",
            source_file="events.py",
            line=42,
            confidence=Confidence.MEDIUM
        )
        
        env_var = DiscoveredEnvVar(
            name="DATABASE_URL",
            source_file="config.py",
            line=8,
            backend_hint="POSTGRES",
            confidence=Confidence.HIGH
        )
        
        sensitive = DiscoveredSensitiveField(
            field_name="ssn",
            source_file="models.py",
            line=20,
            pattern_matched="ssn",
            classification_hint="PII",
            confidence=Confidence.HIGH
        )
        
        # Create discovery result
        result = DiscoveryResult(
            models=[model],
            routes=[route],
            components=[component],
            pact_keys=[pact_key],
            env_vars=[env_var],
            sensitive_fields=[sensitive]
        )
        
        # Verify all components
        assert len(result.models) == 1
        assert len(result.routes) == 1
        assert len(result.components) == 1
        assert len(result.pact_keys) == 1
        assert len(result.env_vars) == 1
        assert len(result.sensitive_fields) == 1
        
        # Verify nested data
        assert result.models[0].fields[0].name == "id"
        assert result.routes[0].path == "/api/users"
        assert result.components[0].type == ComponentType.SERVICE
    
    def test_compatibility_report_with_multiple_checks(self):
        """Test CompatibilityReport with multiple CheckResult objects"""
        checks = [
            CheckResult(
                check_id=f"CHK{i:03d}",
                target=f"Target{i}",
                severity=random.choice([Severity.FAIL, Severity.WARN, Severity.INFO]),
                status="checked",
                message=f"Check {i} message",
                tool="test_tool"
            )
            for i in range(10)
        ]
        
        score_fail = sum(1 for c in checks if c.severity == Severity.FAIL)
        score_warn = sum(1 for c in checks if c.severity == Severity.WARN)
        score_pass = sum(1 for c in checks if c.severity == Severity.INFO)
        
        report = CompatibilityReport(
            generated="2024-01-01T00:00:00Z",
            checks=checks,
            score_pass=score_pass,
            score_warn=score_warn,
            score_fail=score_fail,
            total=len(checks),
            recommendations=["Recommendation 1", "Recommendation 2"]
        )
        
        assert len(report.checks) == 10
        assert report.total == 10
        assert report.score_pass + report.score_warn + report.score_fail == 10


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

class TestEdgeCases:
    """Edge case tests for boundary conditions"""
    
    def test_line_number_edge_cases(self):
        """Test structs with edge case line numbers"""
        # Line 1 (minimum positive)
        model = DiscoveredModel(
            name="Test",
            source_file="test.py",
            line=1,
            orm=None,
            fields=[],
            confidence=Confidence.HIGH
        )
        assert model.line == 1
        
        # Large line number
        model = DiscoveredModel(
            name="Test",
            source_file="test.py",
            line=999999,
            orm=None,
            fields=[],
            confidence=Confidence.HIGH
        )
        assert model.line == 999999
    
    def test_empty_lists_and_dicts(self):
        """Test structs with empty collections"""
        # Empty fields
        model = DiscoveredModel(
            name="Empty",
            source_file="test.py",
            line=1,
            orm=None,
            fields=[],
            confidence=Confidence.LOW
        )
        assert len(model.fields) == 0
        
        # Empty dependencies
        component = DiscoveredComponent(
            name="Isolated",
            source_file="test.py",
            line=1,
            type=ComponentType.LIBRARY,
            public_methods=[],
            dependencies=[],
            confidence=Confidence.MEDIUM,
            note=None
        )
        assert len(component.dependencies) == 0
        assert len(component.public_methods) == 0
        
        # Empty content
        artifact = DraftArtifact(
            _draft=True,
            _generated_by="test",
            tool="test",
            artifact_type="test",
            path="test.py",
            content={}
        )
        assert len(artifact.content) == 0
    
    def test_confidence_levels_all_variants(self):
        """Test all confidence level variants work correctly"""
        confidences = [Confidence.HIGH, Confidence.MEDIUM, Confidence.LOW]
        
        for conf in confidences:
            field = DiscoveredField(
                name="test",
                type=None,
                confidence=conf,
                note=None,
                classification_hint=None
            )
            assert field.confidence == conf
    
    def test_special_characters_in_strings(self):
        """Test handling of special characters in string fields"""
        special_strings = [
            "test/path/with/slashes",
            "test\\path\\with\\backslashes",
            "test-path-with-dashes",
            "test_path_with_underscores",
            "test.path.with.dots",
            "test path with spaces",
            "test@path#with$special%chars"
        ]
        
        for special_str in special_strings:
            model = DiscoveredModel(
                name=special_str,
                source_file=special_str,
                line=1,
                orm=None,
                fields=[],
                confidence=Confidence.HIGH
            )
            assert model.name == special_str
            assert model.source_file == special_str


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestPerformance:
    """Performance tests to verify contract performance requirements"""
    
    def test_score_pct_performance(self):
        """Test score_pct meets p95<1ms requirement"""
        import time
        
        report = CompatibilityReport(
            generated="2024-01-01T00:00:00Z",
            checks=[],
            score_pass=50,
            score_warn=30,
            score_fail=20,
            total=100,
            recommendations=[]
        )
        
        # Run multiple times and measure
        times = []
        for _ in range(100):
            start = time.perf_counter()
            report.score_pct()
            end = time.perf_counter()
            times.append((end - start) * 1000)  # Convert to ms
        
        # Check p95
        times.sort()
        p95 = times[int(len(times) * 0.95)]
        
        # Should be well under 1ms (O(1) operation)
        assert p95 < 1.0, f"p95 latency {p95}ms exceeds 1ms requirement"
    
    def test_has_failures_performance(self):
        """Test has_failures meets p95<1ms requirement"""
        import time
        
        report = CompatibilityReport(
            generated="2024-01-01T00:00:00Z",
            checks=[],
            score_pass=50,
            score_warn=30,
            score_fail=20,
            total=100,
            recommendations=[]
        )
        
        # Run multiple times and measure
        times = []
        for _ in range(100):
            start = time.perf_counter()
            report.has_failures()
            end = time.perf_counter()
            times.append((end - start) * 1000)  # Convert to ms
        
        # Check p95
        times.sort()
        p95 = times[int(len(times) * 0.95)]
        
        # Should be well under 1ms (O(1) operation)
        assert p95 < 1.0, f"p95 latency {p95}ms exceeds 1ms requirement"
"""