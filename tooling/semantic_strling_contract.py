#!/usr/bin/env python3
"""Certify the Semantic STRling 1.0 specification without parsing the DSL."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker, RefResolver

ROOT = Path(__file__).resolve().parents[1]
LANGUAGE_ROOT = ROOT / "spec" / "frontends" / "semantic" / "1.0"

EXPECTED_FILES = (
    "README.md",
    "case.schema.json",
    "formatting.md",
    "grammar.ebnf",
    "language.json",
    "language.schema.json",
    "mapping.json",
    "mapping.schema.json",
    "fixtures/negative.json",
    "fixtures/positive.json",
)

EXPECTED_ENUM_COVERAGE = {
    "case_matching": ["insensitive", "sensitive"],
    "line_terminators": ["exclude", "include"],
    "builtin_class_names": ["digit", "whitespace", "word"],
    "character_domains": ["ascii", "unicode"],
    "repetition_modes": ["greedy", "lazy", "possessive"],
    "position_kinds": [
        "end_before_final_line_terminator",
        "input_end",
        "input_start",
        "line_end",
        "line_start",
        "not_word_boundary",
        "word_boundary",
    ],
    "lookaround_directions": ["ahead", "behind"],
    "lookaround_polarities": ["negative", "positive"],
}


class SemanticStrlingContractError(ValueError):
    """The Semantic STRling contract is malformed or incomplete."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SemanticStrlingContractError(f"cannot read {path}: {error}") from error
    if not isinstance(value, dict):
        raise SemanticStrlingContractError(f"{path}: root must be an object")
    return value


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _json_path(parts: Iterable[Any]) -> str:
    return "$" + "".join(
        f"[{part}]" if isinstance(part, int) else f".{part}" for part in parts
    )


def utf8_boundaries(text: str) -> set[int]:
    boundaries = {0}
    current = 0
    for scalar in text:
        current += len(scalar.encode("utf-8"))
        boundaries.add(current)
    return boundaries


class SemanticStrlingContractSuite:
    """Load and certify the complete specification-authored frontend bundle."""

    def __init__(self, language_root: Path = LANGUAGE_ROOT) -> None:
        self.language_root = language_root
        self.schemas = {
            name: load_json(language_root / name)
            for name in (
                "language.schema.json",
                "mapping.schema.json",
                "case.schema.json",
            )
        }
        for schema in self.schemas.values():
            try:
                Draft202012Validator.check_schema(schema)
            except Exception as error:
                raise SemanticStrlingContractError(
                    f"invalid JSON Schema {schema.get('$id', '<unknown>')}: {error}"
                ) from error
        store = {schema["$id"]: schema for schema in self.schemas.values()}
        self.validators = {
            name: Draft202012Validator(
                schema,
                resolver=RefResolver.from_schema(schema, store=store),
                format_checker=FormatChecker(),
            )
            for name, schema in self.schemas.items()
        }
        self.language = load_json(language_root / "language.json")
        self.mapping = load_json(language_root / "mapping.json")
        self.positive = load_json(language_root / "fixtures" / "positive.json")
        self.negative = load_json(language_root / "fixtures" / "negative.json")
        self.manifest = load_json(language_root / "fixtures" / "manifest.json")
        self.semantic_schema = load_json(
            ROOT / "spec" / "contracts" / "1.0" / "semantic-ir.schema.json"
        )
        try:
            self.grammar = (language_root / "grammar.ebnf").read_text(
                encoding="utf-8"
            )
        except OSError as error:
            raise SemanticStrlingContractError(
                f"cannot read {language_root / 'grammar.ebnf'}: {error}"
            ) from error

    def _validate(self, schema_name: str, value: Mapping[str, Any]) -> None:
        errors = sorted(
            self.validators[schema_name].iter_errors(value),
            key=lambda error: list(error.absolute_path),
        )
        if errors:
            error = errors[0]
            raise SemanticStrlingContractError(
                f"{schema_name} {_json_path(error.absolute_path)}: {error.message}"
            )

    @staticmethod
    def _require_unique(values: list[str], location: str) -> None:
        if len(values) != len(set(values)):
            raise SemanticStrlingContractError(
                f"{location} must contain unique identities"
            )

    @staticmethod
    def _require_sorted_unique(values: list[str], location: str) -> None:
        if values != sorted(values) or len(values) != len(set(values)):
            raise SemanticStrlingContractError(
                f"{location} must be sorted and contain unique identities"
            )

    def _grammar_rules(self) -> tuple[dict[str, str], set[str]]:
        without_comments = re.sub(r"\(\*.*?\*\)", "", self.grammar, flags=re.DOTALL)
        matches = list(
            re.finditer(
                r"(?m)^([A-Z][A-Za-z0-9]*)\s*=\s*(.*?);\s*$",
                without_comments,
                flags=re.DOTALL,
            )
        )
        rules = {match.group(1): match.group(2) for match in matches}
        if not rules or len(rules) != len(matches):
            raise SemanticStrlingContractError(
                "grammar rules must have unique names and end with semicolons"
            )

        references: dict[str, set[str]] = {}
        for name, expression in rules.items():
            structural = re.sub(r"'(?:[^'\\]|\\.)*'", "", expression)
            structural = re.sub(r'"(?:[^"\\]|\\.)*"', "", structural)
            structural = re.sub(r"\?.*?\?", "", structural, flags=re.DOTALL)
            references[name] = set(re.findall(r"\b[A-Z][A-Za-z0-9]*\b", structural))
        undefined = sorted(set().union(*references.values()) - set(rules))
        if undefined:
            raise SemanticStrlingContractError(
                f"grammar references undefined productions: {undefined}"
            )

        reachable: set[str] = set()
        pending = ["Program"]
        while pending:
            name = pending.pop()
            if name in reachable:
                continue
            reachable.add(name)
            pending.extend(sorted(references[name] - reachable))
        unreachable = sorted(set(rules) - reachable)
        if unreachable:
            raise SemanticStrlingContractError(
                f"grammar contains unreachable productions: {unreachable}"
            )
        return rules, reachable

    def _validate_language(self, rules: Mapping[str, str]) -> set[str]:
        self._validate("language.schema.json", self.language)
        if self.language["authority"] != {
            "syntax_authority": True,
            "mapping_authority": True,
            "canonical_semantic_authority": False,
            "target_authority": False,
            "runtime_authority": False,
            "parser_implementation": False,
            "formatter_implementation": False,
            "lowering_destination": "semantic-ir",
        }:
            raise SemanticStrlingContractError(
                "language authority must remain syntax-and-mapping only"
            )

        grammar_before_strings = re.split(
            r"(?m)^String\s*=", self.grammar, maxsplit=1
        )[0]
        keywords = set(re.findall(r'"([a-z]+)"', grammar_before_strings))
        reserved = self.language["reserved_words"]
        self._require_sorted_unique(reserved, "language.reserved_words")
        if set(reserved) != keywords:
            raise SemanticStrlingContractError(
                "reserved words must exactly equal grammar keyword terminals"
            )

        phrases = self.language["construct_phrases"]
        self._require_sorted_unique(phrases, "language.construct_phrases")
        tokenized = [phrase.split() for phrase in phrases]
        for index, left in enumerate(tokenized):
            for right in tokenized[index + 1 :]:
                shorter, longer = (left, right) if len(left) <= len(right) else (right, left)
                if longer[: len(shorter)] == shorter:
                    raise SemanticStrlingContractError(
                        "construct phrases must be prefix-disjoint: "
                        + " ".join(shorter)
                        + " / "
                        + " ".join(longer)
                    )

        diagnostics = self.language["diagnostics"]
        codes = [entry["code"] for entry in diagnostics]
        ids = [entry["id"] for entry in diagnostics]
        self._require_sorted_unique(codes, "language.diagnostics.code")
        self._require_unique(ids, "language.diagnostics.id")
        known_codes = set(codes)
        deferred = self.language["deferred_constructs"]
        deferred_ids = [entry["id"] for entry in deferred]
        self._require_sorted_unique(deferred_ids, "language.deferred_constructs")
        for entry in deferred:
            if entry["diagnostic_code"] not in known_codes:
                raise SemanticStrlingContractError(
                    f"{entry['id']}: deferred construct uses unknown diagnostic"
                )

        if "|" in self.language["structure"]["composition"]:
            raise SemanticStrlingContractError("composition cannot be regex-shaped")
        if not set(rules).issuperset({"Program", "Node", "String", "Identifier"}):
            raise SemanticStrlingContractError("grammar lacks required root productions")
        return known_codes

    @staticmethod
    def _schema_const_values(
        schema: Mapping[str, Any], references: list[Mapping[str, Any]]
    ) -> set[str]:
        values = set()
        for reference in references:
            name = reference["$ref"].rsplit("/", maxsplit=1)[1]
            values.add(schema["$defs"][name]["properties"]["kind"]["const"])
        return values

    def _validate_mapping(self, rules: Mapping[str, str]) -> set[str]:
        self._validate("mapping.schema.json", self.mapping)
        if self.mapping["authority"] != {
            "frontend_mapping": True,
            "canonical_semantics": False,
            "target_behavior": False,
        }:
            raise SemanticStrlingContractError(
                "mapping must not claim canonical semantic or target authority"
            )

        node_entries = self.mapping["node_mappings"]
        member_entries = self.mapping["member_mappings"]
        node_ids = [entry["id"] for entry in node_entries]
        member_ids = [entry["id"] for entry in member_entries]
        program_ids = [entry["id"] for entry in self.mapping["program_mappings"]]
        self._require_sorted_unique(node_ids, "mapping.node_mappings")
        self._require_sorted_unique(member_ids, "mapping.member_mappings")
        self._require_sorted_unique(program_ids, "mapping.program_mappings")

        expected_nodes = self._schema_const_values(
            self.semantic_schema,
            self.semantic_schema["$defs"]["Node"]["oneOf"],
        )
        expected_members = self._schema_const_values(
            self.semantic_schema,
            self.semantic_schema["$defs"]["CharacterSetMember"]["oneOf"],
        )
        actual_nodes = {entry["node_kind"] for entry in node_entries}
        actual_members = {entry["member_kind"] for entry in member_entries}
        if actual_nodes != expected_nodes or len(actual_nodes) != len(node_entries):
            raise SemanticStrlingContractError(
                "mapping must cover every canonical node kind exactly once"
            )
        if actual_members != expected_members or len(actual_members) != len(member_entries):
            raise SemanticStrlingContractError(
                "mapping must cover every set-member kind exactly once"
            )

        for entry in [*self.mapping["program_mappings"], *node_entries, *member_entries]:
            if entry["production"] not in rules:
                raise SemanticStrlingContractError(
                    f"{entry['id']}: unknown grammar production {entry['production']}"
                )
        if self.mapping["enum_coverage"] != EXPECTED_ENUM_COVERAGE:
            raise SemanticStrlingContractError(
                "mapping enum coverage is incomplete or not canonical"
            )
        return set(program_ids + node_ids + member_ids)

    def _validate_fixtures(
        self,
        rules: Mapping[str, str],
        mapping_ids: set[str],
        diagnostic_codes: set[str],
    ) -> tuple[int, int]:
        self._validate("case.schema.json", self.positive)
        self._validate("case.schema.json", self.negative)
        if self.positive["kind"] != "positive" or self.negative["kind"] != "negative":
            raise SemanticStrlingContractError("fixture documents have swapped kinds")

        all_case_ids: list[str] = []
        positive_productions: set[str] = set()
        negative_productions: set[str] = set()
        covered_mappings: set[str] = set()
        covered_diagnostics: set[str] = set()
        for document in (self.positive, self.negative):
            case_ids = [case["id"] for case in document["cases"]]
            self._require_unique(case_ids, f"fixtures.{document['kind']}.cases")
            all_case_ids.extend(case_ids)
            for case in document["cases"]:
                productions = case["production_ids"]
                self._require_sorted_unique(productions, f"{case['id']}.production_ids")
                unknown_productions = sorted(set(productions) - set(rules))
                if unknown_productions:
                    raise SemanticStrlingContractError(
                        f"{case['id']}: unknown productions {unknown_productions}"
                    )
                expected = case["expected"]
                if document["kind"] == "positive":
                    positive_productions.update(productions)
                    case_mappings = expected["mapping_ids"]
                    self._require_sorted_unique(
                        case_mappings, f"{case['id']}.mapping_ids"
                    )
                    unknown_mappings = sorted(set(case_mappings) - mapping_ids)
                    if unknown_mappings:
                        raise SemanticStrlingContractError(
                            f"{case['id']}: unknown mappings {unknown_mappings}"
                        )
                    covered_mappings.update(case_mappings)
                else:
                    negative_productions.update(productions)
                    code = expected["diagnostic_code"]
                    if code not in diagnostic_codes:
                        raise SemanticStrlingContractError(
                            f"{case['id']}: unknown diagnostic {code}"
                        )
                    offset = expected["byte_offset"]
                    if offset not in utf8_boundaries(case["source"]):
                        raise SemanticStrlingContractError(
                            f"{case['id']}: byte offset is not a UTF-8 boundary"
                        )
                    if offset > len(case["source"].encode("utf-8")):
                        raise SemanticStrlingContractError(
                            f"{case['id']}: byte offset exceeds source"
                        )
                    covered_diagnostics.add(code)

        if len(all_case_ids) != len(set(all_case_ids)):
            raise SemanticStrlingContractError("fixture case identities must be global unique")
        missing_positive = sorted(set(rules) - positive_productions)
        missing_negative = sorted(set(rules) - negative_productions)
        if missing_positive:
            raise SemanticStrlingContractError(
                f"grammar productions lack positive fixtures: {missing_positive}"
            )
        if missing_negative:
            raise SemanticStrlingContractError(
                f"grammar productions lack negative fixtures: {missing_negative}"
            )
        if covered_mappings != mapping_ids:
            raise SemanticStrlingContractError(
                f"mapping entries lack positive fixtures: {sorted(mapping_ids - covered_mappings)}"
            )
        required_diagnostics = {
            entry["code"]
            for entry in self.language["diagnostics"]
            if entry["fixture_required"]
        }
        if not required_diagnostics.issubset(covered_diagnostics):
            raise SemanticStrlingContractError(
                "fixture-required diagnostics lack negative cases: "
                + str(sorted(required_diagnostics - covered_diagnostics))
            )
        return len(self.positive["cases"]), len(self.negative["cases"])

    def _validate_manifest(self, positive_count: int, negative_count: int) -> str:
        expected_keys = {
            "manifest_kind",
            "manifest_version",
            "contract_version",
            "authorship",
            "files",
            "case_counts",
        }
        if set(self.manifest) != expected_keys:
            raise SemanticStrlingContractError("fixture manifest keys are invalid")
        if self.manifest["manifest_kind"] != "strling.semantic-language-fixtures":
            raise SemanticStrlingContractError("fixture manifest kind is invalid")
        for key in ("manifest_version", "contract_version"):
            if self.manifest[key] != "1.0.0":
                raise SemanticStrlingContractError(f"fixture manifest {key} is invalid")
        if self.manifest["authorship"] != "specification-authored":
            raise SemanticStrlingContractError(
                "fixture authorship must be specification-owned"
            )
        if self.manifest["case_counts"] != {
            "negative": negative_count,
            "positive": positive_count,
        }:
            raise SemanticStrlingContractError("fixture manifest case counts are stale")

        entries = self.manifest["files"]
        paths = [entry.get("path") for entry in entries if isinstance(entry, dict)]
        if paths != list(EXPECTED_FILES):
            raise SemanticStrlingContractError(
                "fixture manifest paths must exactly cover governed specification inputs"
            )
        for entry in entries:
            if set(entry) != {"path", "sha256"}:
                raise SemanticStrlingContractError(
                    f"manifest entry for {entry.get('path')} has invalid keys"
                )
            path = self.language_root / entry["path"]
            try:
                actual = sha256_bytes(path.read_bytes())
            except OSError as error:
                raise SemanticStrlingContractError(
                    f"cannot fingerprint {entry['path']}: {error}"
                ) from error
            if entry["sha256"] != actual:
                raise SemanticStrlingContractError(
                    f"fixture manifest fingerprint is stale for {entry['path']}"
                )
        certification = {
            "language": self.language,
            "manifest": self.manifest,
            "mapping": self.mapping,
        }
        return sha256_bytes(canonical_json(certification))

    def certify(self) -> dict[str, Any]:
        rules, _ = self._grammar_rules()
        diagnostic_codes = self._validate_language(rules)
        mapping_ids = self._validate_mapping(rules)
        positive_count, negative_count = self._validate_fixtures(
            rules, mapping_ids, diagnostic_codes
        )
        fingerprint = self._validate_manifest(positive_count, negative_count)
        return {
            "contract_version": self.language["contract_version"],
            "dialect_version": self.language["frontend"]["dialect_version"],
            "schemas": len(self.schemas),
            "productions": len(rules),
            "mappings": len(mapping_ids),
            "diagnostics": len(diagnostic_codes),
            "deferred": len(self.language["deferred_constructs"]),
            "positive": positive_count,
            "negative": negative_count,
            "fingerprint": fingerprint,
        }


def main() -> int:
    try:
        result = SemanticStrlingContractSuite().certify()
    except SemanticStrlingContractError as error:
        print(f"SEMANTIC_STRLING_CONTRACT status=failed error={error}")
        return 1
    print(
        "SEMANTIC_STRLING_CONTRACT status=passed "
        f"version={result['dialect_version']} schemas={result['schemas']} "
        f"productions={result['productions']} mappings={result['mappings']} "
        f"diagnostics={result['diagnostics']} deferred={result['deferred']} "
        f"positive={result['positive']} negative={result['negative']} "
        f"fingerprint={result['fingerprint']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
