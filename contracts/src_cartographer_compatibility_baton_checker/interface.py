# === Baton Compatibility Checker (src_cartographer_compatibility_baton_checker) v1 ===
#  Dependencies: pathlib, yaml, cartographer.compatibility.base, cartographer.config.loader, cartographer.models
# Validates baton.yaml configuration files for schema version compliance, node configuration completeness (data_access, authority, openapi_spec), and global endpoint configuration (arbiter, ledger, audit_channel). Produces CheckResult reports with varying severity levels.

# Module invariants:
#   - All CheckResult objects have tool field set to 'baton'
#   - Default baton version is '1.0' if not specified in config
#   - Config file search order: config.stack.baton_config, baton.yaml, baton.yml
#   - Unknown node names default to 'unknown'
#   - Empty global config defaults to empty dict if not dict type

class BatonChecker:
    """Compatibility checker for baton configuration files. Inherits from CompatibilityChecker."""
    pass

def tool_name(
    self: BatonChecker,
) -> str:
    """
    Returns the string identifier for this compatibility checker tool

    Postconditions:
      - Returns the literal string 'baton'

    Side effects: none
    Idempotent: yes
    """
    ...

def check(
    self: BatonChecker,
    config: CartographerConfig,
    base_dir: Path,
) -> list[CheckResult]:
    """
    Performs compatibility checks on a baton.yaml file, validating schema version, node configurations, and global settings. Returns a list of CheckResult objects detailing findings.

    Preconditions:
      - base_dir must be a valid Path object
      - config.compatibility.min_baton_schema_version must be accessible

    Postconditions:
      - Returns a non-empty list containing at least one CheckResult
      - If baton config not found, returns list with single INFO CheckResult
      - If YAML is invalid, returns list with single FAIL CheckResult
      - Each CheckResult has tool field set to 'baton'

    Errors:
      - yaml_parse_error (CheckResult with FAIL severity): When yaml.safe_load raises any Exception
          check_id: baton_yaml_valid
          status: FAIL
          message: Invalid YAML

    Side effects: Reads baton.yaml file from filesystem
    Idempotent: yes
    """
    ...

def _find_baton_config(
    config: CartographerConfig,
    base_dir: Path,
) -> Path | None:
    """
    Locates the baton configuration file by checking the configured path or searching for baton.yaml/baton.yml in base_dir. Returns None if not found.

    Preconditions:
      - config.stack.baton_config is accessible (may be None or empty)
      - base_dir must be a valid Path object

    Postconditions:
      - If config.stack.baton_config is truthy and exists, returns that Path
      - If config.stack.baton_config is truthy but doesn't exist as absolute, returns base_dir / path
      - Otherwise searches for baton.yaml then baton.yml in base_dir
      - Returns None if no config file found

    Side effects: Checks filesystem for file existence
    Idempotent: yes
    """
    ...

def _version_lt(
    a: str,
    b: str,
) -> bool:
    """
    Compares two version strings (e.g., '1.2.3'). Returns True if version a is less than version b. Falls back to lexicographic comparison if parsing fails.

    Postconditions:
      - Returns True if a < b numerically (when parseable as dot-separated integers)
      - Returns True if a < b lexicographically (when ValueError occurs during parsing)
      - Returns False otherwise

    Errors:
      - version_parse_failure (ValueError (caught internally)): When version strings cannot be parsed as integers separated by dots
          fallback: lexicographic comparison

    Side effects: none
    Idempotent: yes
    """
    ...

# ── REQUIRED EXPORTS ──────────────────────────────────
# Your implementation module MUST export ALL of these names
# with EXACTLY these spellings. Tests import them by name.
# __all__ = ['BatonChecker', 'tool_name', 'check', 'CheckResult with FAIL severity', '_find_baton_config', '_version_lt', 'ValueError (caught internally)']
