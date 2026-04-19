"""AdapterBase ABC, WalkerContext, and AdapterError — shared by all adapters."""

import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass
class WalkerContext:
    """File counts produced by the walker. Passed to adapters for confidence scoring."""

    total_files: int
    files_by_language: dict[str, int]  # e.g. {"python": 89, "typescript": 41}


class AdapterError(Exception):
    """
    Raised by adapter run() on subprocess failure, non-zero exit, bad output,
    or missing configuration. reason_code maps to skipped_layers schema.
    """

    def __init__(self, message: str, reason_code: str = "parse_error") -> None:
        super().__init__(message)
        self.reason_code = reason_code


# reason_code values used in skipped_layers:
#   not_installed  — analyzer binary/library not found
#   timeout        — subprocess exceeded adapter.timeout
#   parse_error    — subprocess ran but output could not be parsed
#   no_config      — analyzer found but required config file missing
#   unsupported_repo — repo type not supported by this adapter


class AdapterBase(ABC):
    """
    Base class for all repo-cart analyzers.

    Concrete adapters must:
      - Implement the name/language/layer properties
      - Implement check(), run(), parse(), confidence()
      - Call self._run_subprocess() instead of subprocess.run directly

    Adapter discovery flow (orchestrator):
      1. check() — is the analyzer available?
      2. run(path) — invoke it, returns raw output string
      3. parse(raw) — normalize to layer data dict
      4. confidence(parsed, ctx) — score 0.0–1.0

    Errors from run()/parse() are caught by the orchestrator and recorded in
    skipped_layers with the reason_code from AdapterError.
    """

    # Override per adapter class if the analyzer is consistently slow.
    timeout: int = 30

    @property
    @abstractmethod
    def name(self) -> str:
        """Adapter identifier, e.g. 'radon'. Enforced at class definition time."""
        ...

    @property
    @abstractmethod
    def language(self) -> str:
        """Target language: 'python' | 'js' | 'ts' | 'any'."""
        ...

    @property
    @abstractmethod
    def layer(self) -> str:
        """Key in snapshot['layers'], e.g. 'complexity'."""
        ...

    @abstractmethod
    def check(self) -> bool:
        """Return True if the analyzer binary/library is available."""
        ...

    @abstractmethod
    def run(self, path: Path) -> str:
        """
        Invoke the analyzer via self._run_subprocess().
        Returns raw output string for parse() to consume.
        Raises AdapterError on failure, missing config, or timeout.
        """
        ...

    @abstractmethod
    def parse(self, raw: str) -> dict:
        """Normalize raw output string into the layer data schema."""
        ...

    @abstractmethod
    def confidence(self, parsed: dict, ctx: WalkerContext) -> float:
        """
        Return 0.0–1.0 coverage score.

        Always guard against zero denominator:
            total = ctx.files_by_language.get(self.language, 0)
            return files_parsed / total if total > 0 else 0.0
        """
        ...

    def _run_subprocess(self, cmd: list[str], cwd: Path) -> str:
        """
        DRY subprocess helper. All adapters call this instead of subprocess.run directly.

        Captures both stdout and stderr (tsc writes errors to stderr).
        Raises AdapterError on non-zero exit or timeout.
        Returns stdout + stderr concatenated — adapters parse whichever they need.
        """
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired:
            raise AdapterError(
                f"{self.name} timed out after {self.timeout}s",
                reason_code="timeout",
            )
        if result.returncode != 0:
            raise AdapterError(
                result.stderr or result.stdout or f"{self.name} exited with non-zero status",
                reason_code="parse_error",
            )
        return result.stdout + result.stderr
