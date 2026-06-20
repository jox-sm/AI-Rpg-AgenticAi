---
name: assessment
description: Deprecated alias for the enhanced `self-assessment` skill. Kept for backwards compatibility; delegates to `self-assessment`.
---

# Assessment (deprecated)

This skill is deprecated. The enhanced behavior has moved to `self-assessment`, which now covers personality profiling, technical architecture, UI, security, performance, and prioritized remediation outputs.

## Recommended Usage
Use `self-assessment` instead:

```yaml
skill: self-assessment
action: run
repo: "."
focus: ["security","performance"]
```

## Backwards Compatibility
If callers still reference `assessment`, the agent should delegate to `self-assessment` and preserve input/output shape. Prefer updating callers to use `self-assessment` directly.

## Notes for Maintainers
- Consider removing this alias after clients have migrated.
- If you want to keep a lightweight wrapper, implement an automated delegation that calls `self-assessment` internally.
