# === Cartographer Compatibility Base (src_cartographer_compatibility_base) v1 ===
#  Dependencies: abc, pathlib, cartographer.config.loader, cartographer.models
# Base abstract interface for tool-specific compatibility checkers. Defines the contract that all compatibility checker implementations must follow, requiring a tool_name property and a check method that validates configuration against a specific stack tool.

# Module invariants:
#   - CompatibilityChecker is an abstract base class and cannot be instantiated directly
#   - All concrete subclasses must implement both tool_name property and check method
#   - tool_name must return a string identifying the tool
#   - check must return a list of CheckResult objects

class CompatibilityChecker:
    """Abstract base class for tool-specific compatibility checkers. Subclasses must implement tool_name property and check method."""
    pass

def tool_name(
    self: CompatibilityChecker,
) -> str:
    """
    Property that returns the name of the stack tool this checker validates against. Must be implemented by subclasses.

    Preconditions:
      - Must be implemented by concrete subclass (abstract method)

    Postconditions:
      - Returns a non-empty string identifying the tool name

    Errors:
      - not_implemented (NotImplementedError): Called on abstract base class or subclass without implementation

    Side effects: none
    Idempotent: no
    """
    ...

def check(
    self: CompatibilityChecker,
    config: CartographerConfig,
    base_dir: Path,
) -> list[CheckResult]:
    """
    Runs compatibility checks for the tool against the provided configuration and project directory. Must be implemented by subclasses.

    Preconditions:
      - Must be implemented by concrete subclass (abstract method)
      - config must be a valid CartographerConfig instance
      - base_dir must be a valid Path object

    Postconditions:
      - Returns a list of CheckResult objects (may be empty)
      - Each CheckResult represents a validation finding

    Errors:
      - not_implemented (NotImplementedError): Called on abstract base class or subclass without implementation

    Side effects: none
    Idempotent: no
    """
    ...

# ── REQUIRED EXPORTS ──────────────────────────────────
# Your implementation module MUST export ALL of these names
# with EXACTLY these spellings. Tests import them by name.
# __all__ = ['CompatibilityChecker', 'tool_name', 'check']
