"""Bounded canonical editor-evidence transport and governed catalog views."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

try:
    from .canonical_core import canonical_source_id
except ImportError:  # pragma: no cover - source-tree script fallback
    from canonical_core import canonical_source_id


EDITOR_CONTRACT_VERSION = "1.0.0"
EDITOR_PROJECTION_VERSION = "1.1.0"
TOKEN_TYPES = (
    "string",
    "number",
    "operator",
    "regexp",
    "keyword",
    "function",
    "variable",
    "comment",
)
TOKEN_MODIFIERS: tuple[str, ...] = ()
DEFAULT_MAX_SOURCE_BYTES = 1_048_576
DEFAULT_TIMEOUT_SECONDS = 5.0
MAX_COMPLETION_ITEMS = 256
MAX_TOKENS = 16_384
MAX_SYMBOLS = 4_096
MAX_CAPTURE_LOCATIONS = 16_384
MAX_REWRITE_ACTIONS = 256

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _resource_path(environment_name: str, repository_path: Path) -> Path:
    configured = os.environ.get(environment_name)
    if configured:
        return Path(configured).expanduser().resolve()
    return repository_path


SIMPLY_PROTOCOL_PATH = _resource_path(
    "STRLING_SIMPLY_PROTOCOL_PATH",
    REPOSITORY_ROOT / "spec" / "frontends" / "simply" / "1.1" / "protocol.json",
)
STDLIB_REGISTRY_PATH = _resource_path(
    "STRLING_STDLIB_REGISTRY_PATH",
    REPOSITORY_ROOT / "spec" / "stdlib" / "registry" / "1.0" / "registry.json",
)


class EditorServiceError(RuntimeError):
    """A process, validation, or resource failure outside language semantics."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class CatalogDefinition:
    path: Path
    start: int
    end: int
    canonical_id: str


ProcessObserver = Callable[[subprocess.Popen[bytes] | None], None]


def discover_editor_command() -> tuple[str, ...] | None:
    configured = os.environ.get("STRLING_EDITOR_CORE")
    if configured:
        candidate = Path(configured).expanduser()
        return (str(candidate.resolve()),) if candidate.is_file() else None

    executable = "strling-editor-core.exe" if os.name == "nt" else "strling-editor-core"
    for profile in ("debug", "release"):
        candidate = REPOSITORY_ROOT / "core" / "target" / profile / executable
        if candidate.is_file():
            return (str(candidate),)
    installed = shutil.which("strling-editor-core")
    return (installed,) if installed else None


class CanonicalIntelligence:
    """Invoke one canonical editor projection for one immutable source unit."""

    def __init__(
        self,
        command: Sequence[str] | None = None,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_source_bytes: int = DEFAULT_MAX_SOURCE_BYTES,
    ) -> None:
        self.command = (
            tuple(command) if command is not None else discover_editor_command()
        )
        self.timeout_seconds = timeout_seconds
        self.max_source_bytes = max_source_bytes

    def project(
        self,
        source: str,
        *,
        frontend: str,
        cursor_byte: int | None = None,
        timeout_seconds: float | None = None,
        process_observer: ProcessObserver | None = None,
    ) -> dict[str, Any]:
        encoded = source.encode("utf-8")
        if len(encoded) > self.max_source_bytes:
            raise EditorServiceError(
                "input_limit",
                f"source exceeds the {self.max_source_bytes}-byte editor limit",
            )
        if frontend not in {"regex", "semantic"}:
            raise EditorServiceError("frontend", f"unsupported frontend {frontend!r}")
        if cursor_byte is not None and (
            cursor_byte < 0
            or cursor_byte > len(encoded)
            or cursor_byte not in _utf8_boundaries(source)
        ):
            raise EditorServiceError("cursor", "cursor is not a UTF-8 boundary")
        if not self.command:
            self.command = discover_editor_command()
        if not self.command:
            raise EditorServiceError(
                "unavailable",
                "strling-editor-core is unavailable; configure STRLING_EDITOR_CORE or build the kernel",
            )

        request: dict[str, Any] = {
            "contract_version": EDITOR_CONTRACT_VERSION,
            "source_id": canonical_source_id(source),
            "frontend": frontend,
            "source": source,
        }
        if cursor_byte is not None:
            request["cursor_byte"] = cursor_byte
        payload = json.dumps(
            request, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        try:
            process = subprocess.Popen(
                self.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except OSError as error:
            raise EditorServiceError("unavailable", str(error)) from error
        if process_observer is not None:
            process_observer(process)
        try:
            stdout, stderr = process.communicate(
                payload,
                timeout=self.timeout_seconds
                if timeout_seconds is None
                else timeout_seconds,
            )
        except subprocess.TimeoutExpired as error:
            process.kill()
            process.communicate()
            raise EditorServiceError(
                "timeout", "canonical editor projection timed out"
            ) from error
        finally:
            if process_observer is not None:
                process_observer(None)
        if process.returncode != 0:
            detail = stderr.decode("utf-8", errors="replace").strip()
            raise EditorServiceError(
                "transport",
                f"canonical editor projection exited {process.returncode}"
                + (f": {detail}" if detail else ""),
            )
        if stderr:
            raise EditorServiceError(
                "transport", "canonical editor projection wrote standard error"
            )
        try:
            result = json.loads(stdout.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise EditorServiceError(
                "malformed_result",
                "canonical editor projection returned malformed JSON",
            ) from error
        self._validate(result, source, frontend, cursor_byte)
        return result

    def _validate(
        self,
        result: Any,
        source: str,
        frontend: str,
        cursor_byte: int | None,
    ) -> None:
        if not isinstance(result, dict):
            raise EditorServiceError(
                "malformed_result", "editor evidence is not an object"
            )
        required = {
            "contract_version",
            "projection_version",
            "source_id",
            "frontend",
            "parse_status",
            "tokens",
            "symbols",
            "captures",
            "completions",
            "rewrite_actions",
            "truncated",
        }
        if not required <= result.keys():
            raise EditorServiceError(
                "malformed_result", "editor evidence fields are missing"
            )
        if result["contract_version"] != EDITOR_CONTRACT_VERSION:
            raise EditorServiceError("malformed_result", "unsupported editor contract")
        if result["projection_version"] != EDITOR_PROJECTION_VERSION:
            raise EditorServiceError(
                "malformed_result", "unsupported editor projection"
            )
        if result["source_id"] != canonical_source_id(source):
            raise EditorServiceError(
                "malformed_result", "editor source identity is stale"
            )
        if result["frontend"] != frontend:
            raise EditorServiceError("malformed_result", "editor frontend is stale")
        if result["parse_status"] not in {"complete", "incomplete"}:
            raise EditorServiceError("malformed_result", "invalid editor parse status")
        if not isinstance(result["truncated"], bool):
            raise EditorServiceError("malformed_result", "invalid truncation marker")
        source_size = len(source.encode("utf-8"))
        boundaries = _utf8_boundaries(source)
        self._validate_tokens(result["tokens"], source_size, boundaries)
        self._validate_symbols(result["symbols"], source_size, boundaries)
        self._validate_captures(result["captures"], source_size, boundaries)
        self._validate_completions(result["completions"])
        formatted = result.get("formatted_source")
        if frontend == "regex" or result["parse_status"] == "incomplete":
            if formatted is not None:
                raise EditorServiceError(
                    "malformed_result", "unsupported editor formatting evidence"
                )
        elif not isinstance(formatted, str) or len(formatted.encode("utf-8")) > (
            self.max_source_bytes * 6 + 4096
        ):
            raise EditorServiceError(
                "malformed_result", "formatted source evidence is invalid or unbounded"
            )
        self._validate_rewrite_actions(
            result["rewrite_actions"], result["source_id"], source, frontend
        )
        replacement = result.get("replacement_span")
        if cursor_byte is None:
            if replacement is not None or result["completions"]:
                raise EditorServiceError(
                    "malformed_result", "cursorless evidence has completion state"
                )
        else:
            start, end = _validate_span(replacement, source_size, boundaries)
            if not start <= cursor_byte <= end:
                raise EditorServiceError(
                    "malformed_result", "replacement span does not contain cursor"
                )

    def _validate_tokens(
        self, value: Any, source_size: int, boundaries: set[int]
    ) -> None:
        if not isinstance(value, list) or len(value) > MAX_TOKENS:
            raise EditorServiceError("malformed_result", "token collection is invalid")
        previous_end = 0
        for token in value:
            if not isinstance(token, dict) or token.get("type") not in TOKEN_TYPES:
                raise EditorServiceError("malformed_result", "token type is invalid")
            start, end = _validate_span(token.get("span"), source_size, boundaries)
            if start < previous_end or start == end:
                raise EditorServiceError(
                    "malformed_result", "tokens overlap or contain an empty span"
                )
            previous_end = end

    def _validate_symbols(
        self, value: Any, source_size: int, boundaries: set[int]
    ) -> None:
        if not isinstance(value, list):
            raise EditorServiceError("malformed_result", "symbols are not a list")
        count = 0

        def visit(symbols: list[Any]) -> None:
            nonlocal count
            for symbol in symbols:
                count += 1
                if count > MAX_SYMBOLS or not isinstance(symbol, dict):
                    raise EditorServiceError(
                        "malformed_result", "symbol collection is invalid or unbounded"
                    )
                if not all(
                    isinstance(symbol.get(key), str)
                    for key in ("node_id", "kind", "name")
                ):
                    raise EditorServiceError(
                        "malformed_result", "symbol identity is invalid"
                    )
                start, end = _validate_span(symbol.get("span"), source_size, boundaries)
                selection_start, selection_end = _validate_span(
                    symbol.get("selection_span"), source_size, boundaries
                )
                if not start <= selection_start <= selection_end <= end:
                    raise EditorServiceError(
                        "malformed_result", "symbol selection is outside its range"
                    )
                children = symbol.get("children")
                if not isinstance(children, list):
                    raise EditorServiceError(
                        "malformed_result", "symbol children are invalid"
                    )
                visit(children)

        visit(value)

    def _validate_captures(
        self, value: Any, source_size: int, boundaries: set[int]
    ) -> None:
        if not isinstance(value, list):
            raise EditorServiceError("malformed_result", "capture links are not a list")
        locations = 0
        identities: set[str] = set()
        for capture in value:
            if not isinstance(capture, dict) or not isinstance(
                capture.get("capture_id"), str
            ):
                raise EditorServiceError(
                    "malformed_result", "capture identity is invalid"
                )
            if capture["capture_id"] in identities:
                raise EditorServiceError(
                    "malformed_result", "duplicate capture identity"
                )
            identities.add(capture["capture_id"])
            _validate_span(capture.get("declaration"), source_size, boundaries)
            references = capture.get("references")
            if not isinstance(references, list):
                raise EditorServiceError(
                    "malformed_result", "capture references are invalid"
                )
            previous_end = 0
            for reference in references:
                start, end = _validate_span(reference, source_size, boundaries)
                if start < previous_end:
                    raise EditorServiceError(
                        "malformed_result", "capture references are unsorted"
                    )
                previous_end = end
            locations += len(references) + 1
        if locations > MAX_CAPTURE_LOCATIONS:
            raise EditorServiceError(
                "malformed_result", "capture locations are unbounded"
            )

    def _validate_completions(self, value: Any) -> None:
        if not isinstance(value, list) or len(value) > MAX_COMPLETION_ITEMS:
            raise EditorServiceError(
                "malformed_result", "completion collection is invalid"
            )
        identities: set[str] = set()
        for completion in value:
            if not isinstance(completion, dict) or not all(
                isinstance(completion.get(key), str)
                for key in ("identity", "label", "tier", "detail")
            ):
                raise EditorServiceError(
                    "malformed_result", "completion item is invalid"
                )
            if completion["tier"] not in {
                "parser_expected_terminal",
                "canonical_capture_identity",
            }:
                raise EditorServiceError(
                    "malformed_result", "completion tier is invalid"
                )
            if completion["identity"] in identities:
                raise EditorServiceError(
                    "malformed_result", "duplicate completion identity"
                )
            identities.add(completion["identity"])

    def _validate_rewrite_actions(
        self, value: Any, source_id: str, source: str, frontend: str
    ) -> None:
        if not isinstance(value, list) or len(value) > MAX_REWRITE_ACTIONS:
            raise EditorServiceError(
                "malformed_result", "rewrite action collection is invalid"
            )
        if frontend != "semantic" and value:
            raise EditorServiceError(
                "malformed_result", "regex editor evidence contains rewrite actions"
            )
        source_bytes = source.encode("utf-8")
        boundaries = _utf8_boundaries(source)
        previous: tuple[int, int, str] | None = None
        for action in value:
            if not isinstance(action, dict):
                raise EditorServiceError(
                    "malformed_result", "rewrite action is not an object"
                )
            required_strings = (
                "source_id",
                "diagnostic_code",
                "strategy_id",
                "strategy_fingerprint",
                "semantic_program",
                "removed_wrapper_node_id",
                "replacement_node_id",
                "replacement_text",
                "explanation",
            )
            if not all(isinstance(action.get(key), str) for key in required_strings):
                raise EditorServiceError(
                    "malformed_result", "rewrite action identity is invalid"
                )
            if (
                action["source_id"] != source_id
                or action["diagnostic_code"] != "STRL-QUALITY-0002"
                or action["strategy_id"] != "rewrite.repeat_exactly_once.elide.v1"
                or not action["explanation"]
            ):
                raise EditorServiceError(
                    "malformed_result", "rewrite action authority is invalid or stale"
                )
            for fingerprint_key in ("strategy_fingerprint", "semantic_program"):
                fingerprint = action[fingerprint_key]
                if len(fingerprint) != 64 or any(
                    character not in "0123456789abcdef" for character in fingerprint
                ):
                    raise EditorServiceError(
                        "malformed_result", "rewrite fingerprint is invalid"
                    )
            wrapper_start, wrapper_end = _validate_span(
                action.get("wrapper_span"), len(source_bytes), boundaries
            )
            replacement_start, replacement_end = _validate_span(
                action.get("replacement_span"), len(source_bytes), boundaries
            )
            if not (
                wrapper_start <= replacement_start <= replacement_end <= wrapper_end
            ):
                raise EditorServiceError(
                    "malformed_result", "rewrite replacement is outside its wrapper"
                )
            replacement = source_bytes[replacement_start:replacement_end].decode(
                "utf-8"
            )
            if action["replacement_text"] != replacement:
                raise EditorServiceError(
                    "malformed_result", "rewrite replacement text is not current source"
                )
            if action.get("proof_conditions") != [
                "original_node_is_repeat",
                "direct_body_relationship",
                "bounds_exactly_one",
                "mode_non_possessive",
            ]:
                raise EditorServiceError(
                    "malformed_result", "rewrite proof conditions are incomplete"
                )
            order = (
                wrapper_start,
                wrapper_end,
                action["removed_wrapper_node_id"],
            )
            if previous is not None and order <= previous:
                raise EditorServiceError(
                    "malformed_result", "rewrite actions are duplicated or unsorted"
                )
            previous = order


def _utf8_boundaries(source: str) -> set[int]:
    boundaries = {0}
    size = 0
    for character in source:
        size += len(character.encode("utf-8"))
        boundaries.add(size)
    return boundaries


def _validate_span(
    value: Any, source_size: int, boundaries: set[int]
) -> tuple[int, int]:
    if not isinstance(value, Mapping):
        raise EditorServiceError("malformed_result", "source span is not an object")
    start = value.get("start")
    end = value.get("end")
    if (
        not isinstance(start, int)
        or isinstance(start, bool)
        or not isinstance(end, int)
        or isinstance(end, bool)
        or not 0 <= start <= end <= source_size
        or start not in boundaries
        or end not in boundaries
    ):
        raise EditorServiceError("malformed_result", "source span is invalid")
    return start, end


@lru_cache(maxsize=1)
def _simply_protocol() -> dict[str, Any]:
    return json.loads(SIMPLY_PROTOCOL_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _stdlib_registry() -> dict[str, Any]:
    return json.loads(STDLIB_REGISTRY_PATH.read_text(encoding="utf-8"))


def host_completion(
    source: str, cursor_byte: int, *, binding_id: str
) -> dict[str, Any] | None:
    if len(source.encode("utf-8")) > DEFAULT_MAX_SOURCE_BYTES:
        return None
    boundaries = _utf8_boundaries(source)
    if cursor_byte not in boundaries:
        return None
    encoded = source.encode("utf-8")
    start = cursor_byte
    while start > 0 and _identifier_byte(encoded[start - 1]):
        start -= 1
    end = cursor_byte
    while end < len(encoded) and _identifier_byte(encoded[end]):
        end += 1
    if encoded[:start][-2:] != b"s.":
        return None
    prefix = encoded[start:cursor_byte].decode("ascii")
    operations = [
        {
            "identity": f"simply:{operation['id']}",
            "label": operation["id"],
            "tier": "simply_operation_or_stdlib_helper",
            "detail": f"Simply 1.1 operation → {operation['destination']}",
        }
        for operation in _simply_protocol()["operations"]
    ]
    registry = _stdlib_registry()
    binding = next(
        (
            candidate
            for candidate in registry["host_bindings"]
            if candidate["binding_id"] == binding_id
        ),
        None,
    )
    helpers: list[dict[str, str]] = []
    if binding is not None:
        by_id = {helper["id"]: helper for helper in registry["helpers"]}
        for exposure in binding["exposures"]:
            helper = by_id[exposure["helper_id"]]
            for public_name in exposure["public_names"]:
                helpers.append(
                    {
                        "identity": helper["id"],
                        "label": public_name,
                        "tier": "simply_operation_or_stdlib_helper",
                        "detail": helper["documentation"]["summary"],
                    }
                )
    completions = sorted(
        (
            candidate
            for candidate in [*operations, *helpers]
            if candidate["label"].startswith(prefix)
        ),
        key=lambda candidate: (candidate["label"], candidate["identity"]),
    )[:MAX_COMPLETION_ITEMS]
    return {
        "completions": completions,
        "replacement_span": {"start": start, "end": end},
    }


def catalog_definition(word: str, *, binding_id: str) -> CatalogDefinition | None:
    for operation in _simply_protocol()["operations"]:
        if operation["id"] == word:
            return _catalog_location(
                SIMPLY_PROTOCOL_PATH, "id", operation["id"], operation["id"]
            )
    registry = _stdlib_registry()
    binding = next(
        (
            candidate
            for candidate in registry["host_bindings"]
            if candidate["binding_id"] == binding_id
        ),
        None,
    )
    if binding is None:
        return None
    for exposure in binding["exposures"]:
        if word in exposure["public_names"]:
            return _catalog_location(
                STDLIB_REGISTRY_PATH,
                "id",
                exposure["helper_id"],
                exposure["helper_id"],
            )
    return None


def _catalog_location(
    path: Path, key: str, value: str, canonical_id: str
) -> CatalogDefinition:
    text = path.read_text(encoding="utf-8")
    needle = f'"{key}": "{value}"'
    character_start = text.find(needle)
    if character_start < 0:
        raise EditorServiceError(
            "catalog", f"canonical declaration {canonical_id!r} is missing"
        )
    start = len(text[:character_start].encode("utf-8"))
    end = start + len(needle.encode("utf-8"))
    return CatalogDefinition(path=path, start=start, end=end, canonical_id=canonical_id)


def _identifier_byte(value: int) -> bool:
    return chr(value).isalnum() or value == ord("_")
