# === Pact Compatibility Checker (src_cartographer_compatibility_pact_checker) v1 ===
#  Dependencies: re, pathlib, yaml, cartographer.compatibility.base, cartographer.config.loader, cartographer.models
# Validates PACT contract compliance by checking contract YAML files for required fields (data_access, authority) and scanning source code for PACT keys and event handlers. Extends CompatibilityChecker to provide contract-based compatibility verification.

# Module invariants:
#   - tool_name property always returns 'pact'
#   - All CheckResult instances have tool='pact'
#   - Contract auto-discovery checks directories in order: ['.pact', 'contracts', 'pact']
#   - Rationale is considered vague if less than 10 characters after stripping whitespace
#   - Source files are processed in sorted order for contracts
#   - Files matching exclusion patterns are always skipped

class PactChecker:
    """Compatibility checker for PACT contracts that validates contract files and source code compliance"""
    pass

def tool_name(
    self: PactChecker,
) -> str:
    """
    Returns the identifier for this checker tool

    Postconditions:
      - Returns the string 'pact'

    Side effects: none
    Idempotent: no
    """
    ...

def check(
    self: PactChecker,
    config: CartographerConfig,
    base_dir: Path,
) -> list[CheckResult]:
    """
    Main entry point that performs full PACT compatibility checking by validating contract files and source code. Auto-discovers contract directory if not configured, then delegates to _check_contracts and _check_source.

    Preconditions:
      - config.compatibility.pact_key_format must be a valid regex pattern
      - config.targets.source.dirs must be a list of directory paths

    Postconditions:
      - Returns list of CheckResult instances for all checks performed
      - Auto-discovers pact directory from ['.pact', 'contracts', 'pact'] if config.stack.pact_project_dir is None

    Errors:
      - regex_compile_error (re.error): config.compatibility.pact_key_format is invalid regex

    Side effects: Reads files from filesystem, Compiles regex pattern from config.compatibility.pact_key_format
    Idempotent: no
    """
    ...

def _check_contracts(
    self: PactChecker,
    contract_dir: Path,
) -> list[CheckResult]:
    """
    Validates PACT contract YAML files for required fields (data_access, authority) and checks data_access rationale quality. Returns CheckResult for each validation performed.

    Postconditions:
      - Returns empty list if contract_dir does not exist
      - Returns CheckResult for each YAML file found with check_id: contract_valid_yaml, contract_has_data_access, contract_data_access_rationale_not_vague, or contract_has_authority
      - Processes all *.yaml files recursively in sorted order

    Errors:
      - yaml_parse_error (Exception): YAML file is invalid or cannot be parsed
          handling: Caught and converted to FAIL CheckResult with check_id=contract_valid_yaml

    Side effects: Reads YAML files from filesystem, Opens files using yaml.safe_load
    Idempotent: no
    """
    ...

def _check_source(
    self: PactChecker,
    config: CartographerConfig,
    base_dir: Path,
    pact_key_re: re.Pattern,
) -> list[CheckResult]:
    """
    Scans Python source files for PACT keys matching the configured pattern and validates presence of event_handler and log_handler parameters in classes. Returns CheckResult for each validation issue found.

    Preconditions:
      - config.targets.source.dirs contains valid directory paths
      - config.targets.source.exclude contains exclusion patterns
      - pact_key_re is a compiled regex Pattern

    Postconditions:
      - Returns CheckResult for each source file with check_id: source_has_pact_key, pact_key_format_valid, source_has_event_handler, or source_has_log_handler
      - Only flags substantive modules (containing 'class ' or 'def ') for missing PACT keys
      - Skips files that match exclusion patterns or don't exist
      - Handles file read errors gracefully by continuing

    Errors:
      - file_read_error (OSError): OSError occurs when reading file
          handling: Caught and file is skipped, processing continues

    Side effects: Reads Python source files from filesystem, Performs regex matching on file contents
    Idempotent: no
    """
    ...

# ── REQUIRED EXPORTS ──────────────────────────────────
# Your implementation module MUST export ALL of these names
# with EXACTLY these spellings. Tests import them by name.
# __all__ = ['PactChecker', 'tool_name', 'check', '_check_contracts', '_check_source']
