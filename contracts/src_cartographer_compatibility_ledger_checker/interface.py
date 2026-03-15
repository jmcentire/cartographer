# === Ledger Compatibility Checker (src_cartographer_compatibility_ledger_checker) v1 ===
#  Dependencies: pathlib.Path, yaml, cartographer.compatibility.base.CompatibilityChecker, cartographer.config.loader.CartographerConfig, cartographer.models.CheckResult, cartographer.models.Severity
# A compatibility checker module for validating ledger schema files. It scans YAML schema files in a ledger registry to verify field classifications, check for annotation conflicts (gdpr_erasable vs immutable), validate GDPR erasure methods, and ensure audit fields have retention policies. Returns structured CheckResult objects with severity levels.

# Module invariants:
#   - tool_name always returns 'ledger'
#   - check() always returns at least one CheckResult
#   - All CheckResult objects have tool='ledger'
#   - Registry search order: config.stack.ledger_registry, .ledger/registry, .ledger
#   - Classification FAIL severity when missing_classification > len(fields) // 2, otherwise WARN
#   - Annotation conflicts between gdpr_erasable and immutable always result in FAIL severity
#   - GDPR and audit policy violations result in WARN severity

class LedgerChecker:
    """A compatibility checker class that extends CompatibilityChecker base class. Validates ledger schema files for field classifications, annotation conflicts, and policy compliance."""
    pass

def tool_name(
    self: LedgerChecker,
) -> str:
    """
    Property method that returns the identifier for this compatibility checker tool

    Postconditions:
      - Returns the string 'ledger'

    Side effects: none
    Idempotent: no
    """
    ...

def check(
    self: LedgerChecker,
    config: CartographerConfig,
    base_dir: Path,
) -> list[CheckResult]:
    """
    Performs compatibility checks on ledger schema files. Searches for a ledger registry, loads YAML schema files, and validates field classifications, annotation conflicts, GDPR erasure methods, and audit retention policies.

    Preconditions:
      - config must be a valid CartographerConfig instance
      - base_dir must be a valid Path object

    Postconditions:
      - Returns a non-empty list containing at least one CheckResult
      - If no registry found, returns single INFO CheckResult with check_id 'ledger_registry_exists'
      - Each CheckResult has tool field set to 'ledger'
      - Classification check creates one result per schema file
      - Annotation conflicts create FAIL results for conflicting fields
      - GDPR erasable fields without erasure_method create WARN results
      - Audit fields without retention_policy create WARN results

    Errors:
      - yaml_parse_error (Exception): YAML file cannot be parsed
          handling: silently caught and ignored with pass statement
      - file_read_error (Exception): File cannot be opened or read
          handling: silently caught and ignored with pass statement

    Side effects: Reads YAML files from filesystem in registry_path, Traverses directory tree using rglob('*.yaml')
    Idempotent: no
    """
    ...

def _find_registry(
    config: CartographerConfig,
    base_dir: Path,
) -> Path | None:
    """
    Locates the ledger registry directory by checking configuration settings and common default paths. First checks config.stack.ledger_registry, then falls back to '.ledger/registry' and '.ledger' directories.

    Preconditions:
      - config must be a valid CartographerConfig instance
      - base_dir must be a valid Path object

    Postconditions:
      - Returns Path object if registry exists, otherwise None
      - Returned Path exists on filesystem if not None
      - Checks config.stack.ledger_registry first if present
      - Falls back to '.ledger/registry' then '.ledger' in base_dir

    Side effects: Checks filesystem for directory existence
    Idempotent: no
    """
    ...

# ── REQUIRED EXPORTS ──────────────────────────────────
# Your implementation module MUST export ALL of these names
# with EXACTLY these spellings. Tests import them by name.
# __all__ = ['LedgerChecker', 'tool_name', 'check', '_find_registry']
