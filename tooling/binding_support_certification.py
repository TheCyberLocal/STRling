#!/usr/bin/env python3
"""Build and certify the final P17 host-binding evidence matrix."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator

try:
    from tooling.architecture_fitness import binding_semantic_path_findings
    from tooling.governance import matches_any
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from architecture_fitness import binding_semantic_path_findings
    from governance import matches_any


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_ROOT = ROOT / "tests" / "adapters" / "binding-support-4.0"
SCHEMA_PATH = EVIDENCE_ROOT / "evidence.schema.json"
MANIFEST_PATH = EVIDENCE_ROOT / "manifest.json"
EVIDENCE_PATH = EVIDENCE_ROOT / "evidence.json"


class BindingSupportCertificationError(RuntimeError):
    """Raised when the P17-T08 evidence cannot be certified."""


@dataclass(frozen=True)
class BindingSupportCertificationReport:
    binding_count: int
    supported_candidate_count: int
    preview_candidate_count: int
    public_surface_count: int
    enforced_public_surface_count: int
    forbidden_product_path_count: int
    blocking_requirement_count: int
    fingerprint: str

    def as_dict(self) -> dict[str, object]:
        return {
            "binding_count": self.binding_count,
            "supported_candidate_count": self.supported_candidate_count,
            "preview_candidate_count": self.preview_candidate_count,
            "public_surface_count": self.public_surface_count,
            "enforced_public_surface_count": self.enforced_public_surface_count,
            "forbidden_product_path_count": self.forbidden_product_path_count,
            "blocking_requirement_count": self.blocking_requirement_count,
            "fingerprint": self.fingerprint,
        }


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise BindingSupportCertificationError(
            f"cannot read {path}: {error}"
        ) from error
    if not isinstance(value, dict):
        raise BindingSupportCertificationError(f"{path} must contain one JSON object")
    return value


def _fingerprint_json(
    value: Mapping[str, Any], excluded: set[str] | None = None
) -> str:
    normalized = {
        key: item for key, item in value.items() if key not in (excluded or set())
    }
    encoded = json.dumps(
        normalized, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _git_files(root: Path, path: str) -> tuple[str, ...]:
    completed = subprocess.run(
        ["git", "ls-files", "--", path],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise BindingSupportCertificationError(completed.stderr.strip())
    return tuple(line for line in completed.stdout.splitlines() if line)


def _semantic_path_findings(
    root: Path, configuration: Mapping[str, object]
) -> list[str]:
    return sorted(
        {
            path or message
            for message, path in binding_semantic_path_findings(
                root, configuration, matches_any
            )
        }
    )


def _load_task_record(root: Path, relative: str) -> dict[str, Any]:
    try:
        import yaml

        value = yaml.safe_load((root / relative).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise BindingSupportCertificationError(
            f"cannot read task record {relative}: {error}"
        ) from error
    if not isinstance(value, dict):
        raise BindingSupportCertificationError(
            f"task record {relative} is not an object"
        )
    return value


def _build_evidence(
    root: Path = ROOT, manifest: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    declared = dict(manifest or _read_json(MANIFEST_PATH))
    toolchain = _read_json(root / "toolchain.json")
    public_registry = _read_json(root / "governance" / "public-surfaces.json")
    architecture_registry = _read_json(root / "governance" / "architecture-rules.json")

    bindings_config = toolchain.get("bindings")
    surfaces = public_registry.get("surfaces")
    rules = architecture_registry.get("rules")
    if not isinstance(bindings_config, dict):
        raise BindingSupportCertificationError("toolchain bindings must be an object")
    if not isinstance(surfaces, list) or not isinstance(rules, list):
        raise BindingSupportCertificationError("governance registries are malformed")

    surface_by_id = {str(item["id"]): item for item in surfaces}
    rule_by_id = {str(item["id"]): item for item in rules}
    semantic_rule = rule_by_id.get("duplicated-binding-compilers")
    if not isinstance(semantic_rule, dict) or not isinstance(
        semantic_rule.get("configuration"), dict
    ):
        raise BindingSupportCertificationError(
            "duplicated-binding-compilers rule is missing or malformed"
        )
    semantic_configuration = semantic_rule["configuration"]
    rows: list[dict[str, Any]] = []
    migration_cache: dict[str, dict[str, Any]] = {}

    for item in declared["bindings"]:
        identifier = item["id"]
        config = bindings_config.get(identifier)
        if not isinstance(config, dict):
            raise BindingSupportCertificationError(
                f"toolchain binding {identifier} is missing"
            )
        record_path = item["migration_record"]
        record = migration_cache.setdefault(
            record_path, _load_task_record(root, record_path)
        )
        public_rows: list[dict[str, Any]] = []
        for surface_id in item["public_surfaces"]:
            surface = surface_by_id.get(surface_id)
            if not isinstance(surface, dict):
                raise BindingSupportCertificationError(
                    f"public surface {surface_id} is missing"
                )
            snapshot_path = str(surface["snapshot_path"])
            public_rows.append(
                {
                    "id": surface_id,
                    "enforcement": surface["enforcement"],
                    "snapshot_path": snapshot_path,
                    "snapshot_exists": (root / snapshot_path).is_file(),
                }
            )
        files = config.get("files")
        capabilities = config.get("capabilities")
        dependency = config.get("dependency_resolution")
        assert isinstance(files, dict)
        assert isinstance(capabilities, dict)
        assert isinstance(dependency, dict)
        rows.append(
            {
                **item,
                "package": {
                    "path": config["path"],
                    "dependency_model": dependency["model"],
                    "manifests": files.get("manifests", []),
                    "locks": files.get("locks", []),
                    "configured_operations": sorted(
                        name
                        for name, status in capabilities.items()
                        if status in {"configured", "enforced"}
                    ),
                },
                "public_contracts": public_rows,
                "migration": {
                    "status": record.get("status"),
                    "readiness": (record.get("readiness") or {}).get("status"),
                },
            }
        )

    architecture_rows = []
    for rule_id in declared["required_architecture_rules"]:
        rule = rule_by_id.get(rule_id)
        if not isinstance(rule, dict):
            raise BindingSupportCertificationError(
                f"architecture rule {rule_id} is missing"
            )
        architecture_rows.append(
            {"id": rule_id, "kind": rule["kind"], "status": rule["status"]}
        )

    blockers: list[str] = []
    public_rows = [surface for row in rows for surface in row["public_contracts"]]
    if any(
        surface["enforcement"] != "enforced" or not surface["snapshot_exists"]
        for surface in public_rows
    ):
        blockers.append("all-language-public-surfaces-enforced")
    if any(row["migration"]["status"] != "complete" for row in rows):
        blockers.append("all-adapter-migrations-complete")
    if any(row["status"] != "enforced" for row in architecture_rows):
        blockers.append("all-adapter-boundaries-enforced")
    transports = declared.get("supporting_transports", [])
    if not isinstance(transports, list):
        raise BindingSupportCertificationError("supporting transports must be an array")
    transport_ids = {
        str(item.get("id")) for item in transports if isinstance(item, dict)
    }
    expected_products = [
        identifier for identifier in bindings_config if identifier not in transport_ids
    ]
    product_ids = [str(item.get("id")) for item in declared["bindings"]]
    if product_ids != expected_products or (
        set(bindings_config) - set(product_ids) - transport_ids
    ):
        blockers.append("all-registered-binding-routes-classified")
    allowed_transports = {"rust_kernel", "c_abi", "wasm_abi"}
    if any(
        not isinstance(item, dict)
        or item.get("adapter_contract") != "thin"
        or item.get("canonical_transport") not in allowed_transports
        or not isinstance(rule_by_id.get(str(item.get("route_rule_id"))), dict)
        or rule_by_id[str(item.get("route_rule_id"))].get("status") != "enforced"
        for item in [*declared["bindings"], *transports]
    ):
        blockers.append("all-binding-routes-thin-and-canonical")
    semantic_paths = _semantic_path_findings(root, semantic_configuration)
    if semantic_paths:
        blockers.append("zero-forbidden-product-semantic-paths")

    evidence: dict[str, Any] = {
        "$schema": "evidence.schema.json",
        "suite_id": "strling.binding-support-certification",
        "suite_version": "4.0.0",
        "policy_boundary": declared["policy_boundary"],
        "semantic_domains": declared["semantic_domains"],
        "bindings": rows,
        "supporting_transports": transports,
        "semantic_ownership": {
            "architecture_rules": architecture_rows,
            "forbidden_product_paths": semantic_paths,
            "permitted_facade_paths": list(semantic_configuration["permitted_paths"]),
        },
        "counts": {
            "bindings": len(rows),
            "supported_candidates": sum(
                row["certification_tier"] == "supported_candidate" for row in rows
            ),
            "preview_candidates": sum(
                row["certification_tier"] == "preview_candidate" for row in rows
            ),
            "legacy_candidates": sum(
                row["certification_tier"] == "legacy_candidate" for row in rows
            ),
            "public_surfaces": len(public_rows),
            "enforced_public_surfaces": sum(
                surface["enforcement"] == "enforced" and surface["snapshot_exists"]
                for surface in public_rows
            ),
            "forbidden_product_paths": len(semantic_paths),
        },
        "readiness": {
            "status": "ready" if not blockers else "not_ready",
            "blocking_requirements": blockers,
        },
    }
    evidence["fingerprint"] = _fingerprint_json(evidence)
    return evidence


def _validate_documents(
    schema: Mapping[str, Any],
    manifest: Mapping[str, Any],
    evidence: Mapping[str, Any],
    *,
    expected_evidence: Mapping[str, Any],
    require_ready: bool = False,
) -> BindingSupportCertificationReport:
    Draft202012Validator.check_schema(schema)
    errors = sorted(
        Draft202012Validator(schema).iter_errors(evidence),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        raise BindingSupportCertificationError(errors[0].message)
    ids = [row["id"] for row in manifest["bindings"]]
    evidence_ids = [row["id"] for row in evidence["bindings"]]
    if len(ids) != len(set(ids)) or evidence_ids != ids:
        raise BindingSupportCertificationError(
            "binding evidence must cover every unique manifest route in registry order"
        )
    transport_ids = [row["id"] for row in manifest["supporting_transports"]]
    evidence_transport_ids = [row["id"] for row in evidence["supporting_transports"]]
    if len(transport_ids) != len(set(transport_ids)) or (
        evidence_transport_ids != transport_ids
    ):
        raise BindingSupportCertificationError(
            "binding evidence must cover every unique supporting transport"
        )
    if evidence != expected_evidence:
        raise BindingSupportCertificationError(
            "checked-in binding support evidence does not reproduce"
        )
    if evidence["fingerprint"] != _fingerprint_json(evidence, {"fingerprint"}):
        raise BindingSupportCertificationError("evidence fingerprint is not canonical")
    if require_ready and evidence["readiness"]["status"] != "ready":
        blockers = ", ".join(evidence["readiness"]["blocking_requirements"])
        raise BindingSupportCertificationError(
            f"binding certification is not ready: {blockers}"
        )
    counts = evidence["counts"]
    return BindingSupportCertificationReport(
        binding_count=counts["bindings"],
        supported_candidate_count=counts["supported_candidates"],
        preview_candidate_count=counts["preview_candidates"],
        public_surface_count=counts["public_surfaces"],
        enforced_public_surface_count=counts["enforced_public_surfaces"],
        forbidden_product_path_count=counts["forbidden_product_paths"],
        blocking_requirement_count=len(evidence["readiness"]["blocking_requirements"]),
        fingerprint=evidence["fingerprint"],
    )


class BindingSupportCertificationSuite:
    def __init__(self, root: Path = ROOT) -> None:
        self.root = root

    def certify(
        self, *, require_ready: bool = False
    ) -> BindingSupportCertificationReport:
        schema = _read_json(self.root / SCHEMA_PATH.relative_to(ROOT))
        manifest = _read_json(self.root / MANIFEST_PATH.relative_to(ROOT))
        evidence = _read_json(self.root / EVIDENCE_PATH.relative_to(ROOT))
        return _validate_documents(
            schema,
            manifest,
            evidence,
            expected_evidence=_build_evidence(self.root, manifest),
            require_ready=require_ready,
        )

    def certify_documents(
        self,
        schema: Mapping[str, Any],
        manifest: Mapping[str, Any],
        evidence: Mapping[str, Any],
        *,
        expected_evidence: Mapping[str, Any],
        require_ready: bool = False,
    ) -> BindingSupportCertificationReport:
        return _validate_documents(
            schema,
            manifest,
            evidence,
            expected_evidence=expected_evidence,
            require_ready=require_ready,
        )


def _write_evidence(root: Path = ROOT) -> dict[str, Any]:
    manifest = _read_json(root / MANIFEST_PATH.relative_to(ROOT))
    evidence = _build_evidence(root, manifest)
    path = root / EVIDENCE_PATH.relative_to(ROOT)
    path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=4) + "\n", encoding="utf-8"
    )
    node = shutil.which("node")
    prettier = root / "node_modules" / "prettier" / "bin" / "prettier.cjs"
    if node is None or not prettier.is_file():
        raise BindingSupportCertificationError(
            "pinned Node and node_modules/prettier are required to format evidence"
        )
    formatted = subprocess.run(
        [node, str(prettier), "--write", str(path)],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if formatted.returncode != 0:
        raise BindingSupportCertificationError(
            f"cannot format generated evidence: {formatted.stderr.strip()}"
        )
    return evidence


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-evidence", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.write_evidence:
            _write_evidence()
        report = BindingSupportCertificationSuite().certify(
            require_ready=args.require_ready
        )
    except BindingSupportCertificationError as error:
        if args.json:
            print(json.dumps({"status": "failed", "error": str(error)}))
        else:
            print(f"binding support certification failed: {error}", file=sys.stderr)
        return 1
    payload = {"status": "passed", **report.as_dict()}
    print(json.dumps(payload, sort_keys=True) if args.json else payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
