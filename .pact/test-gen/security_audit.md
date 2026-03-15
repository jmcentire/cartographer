# Security Audit Report

**Generated:** 2026-03-15T15:25:11.099191

## Summary

- Critical: 1
- High: 0
- Medium: 0
- Low: 0
- Info: 0
- **Total: 1**

## CRITICAL (1)

- **_collect_files** (src/cartographer/discovery/scanner.py:40) [NOT COVERED]
  - Pattern: variable: root
  - Complexity: 6
  - Suggestion: Ensure branch on 'root' is tested with both truthy and falsy values
