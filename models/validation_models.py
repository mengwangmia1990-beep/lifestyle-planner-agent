from dataclasses import dataclass, field

# final validation result
@dataclass
class ValidationResult:
    valid: bool
    checks: dict[str, bool]
    errors: list[str] = field(default_factory=list)

# each validation check result
@dataclass
class CheckResult:
    name: str
    passed: bool
    errors: list[str] = field(default_factory=list)
