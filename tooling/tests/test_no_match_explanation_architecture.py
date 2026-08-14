from __future__ import annotations

import unittest

from tooling.core_stage_boundaries import no_match_explanation_boundary_violation


SOURCE_PATH = "core/src/no_match_explanation.rs"
VALID_SOURCE = """
use std::time::Instant;
use crate::explanation::{ExplanationDocument};
use crate::semantic::{SemanticProgram};
use crate::source::{NodeId, SourceSpan};
use crate::target::{TargetProfileReference};
use crate::validation::{canonical_sha256, Validate};

pub const MAX_NO_MATCH_SUBJECT_UTF8_BYTES: usize = 16 * 1024;
pub const MAX_NO_MATCH_SUBJECT_UNICODE_SCALARS: usize = 4_096;
pub const MAX_NO_MATCH_STEPS: u64 = 100_000;
pub const MAX_NO_MATCH_DEPTH: usize = 128;
pub const MAX_NO_MATCH_BRANCH_EXPANSIONS: u64 = 4_096;
pub const MAX_NO_MATCH_FINDINGS: usize = 32;
pub const MAX_NO_MATCH_ELAPSED_MILLISECONDS: u64 = 250;

pub fn explain_no_match() {
    let _started = Instant::now();
    let _identity = canonical_sha256(&());
}
"""


class NoMatchExplanationArchitectureTests(unittest.TestCase):
    def test_absent_future_implementation_does_not_block_contract_first_cp2(
        self,
    ) -> None:
        self.assertIsNone(no_match_explanation_boundary_violation({}))

    def test_canonical_bounded_source_passes(self) -> None:
        self.assertIsNone(
            no_match_explanation_boundary_violation({SOURCE_PATH: VALID_SOURCE})
        )

    def test_each_required_canonical_input_or_limit_is_enforced(self) -> None:
        markers = (
            "crate::explanation::{",
            "crate::semantic::{",
            "crate::source::{",
            "crate::target::{",
            "crate::validation::{",
            "canonical_sha256",
            "std::time::Instant",
            "MAX_NO_MATCH_SUBJECT_UTF8_BYTES",
            "MAX_NO_MATCH_SUBJECT_UNICODE_SCALARS",
            "MAX_NO_MATCH_STEPS",
            "MAX_NO_MATCH_DEPTH",
            "MAX_NO_MATCH_BRANCH_EXPANSIONS",
            "MAX_NO_MATCH_FINDINGS",
            "MAX_NO_MATCH_ELAPSED_MILLISECONDS",
        )
        for marker in markers:
            with self.subTest(marker=marker):
                candidate = VALID_SOURCE.replace(marker, "removed")
                self.assertIsNotNone(
                    no_match_explanation_boundary_violation({SOURCE_PATH: candidate})
                )

    def test_frontend_runtime_target_and_product_dependencies_are_rejected(
        self,
    ) -> None:
        forbidden = (
            "use crate::regex_frontend;",
            "use crate::semantic_frontend;",
            "use crate::semantic_conversion;",
            "use crate::capability_evaluation;",
            "use crate::target_lowering;",
            "use crate::target_serialization;",
            "use crate::kernel;",
            "use crate::protocol;",
            "use std::fs;",
            "use std::process;",
            "use std::time::SystemTime;",
            "let emitted_pattern = value;",
            "let backtracking_trace = value;",
            "let widget = value;",
        )
        for marker in forbidden:
            with self.subTest(marker=marker):
                candidate = VALID_SOURCE + "\n" + marker
                self.assertIsNotNone(
                    no_match_explanation_boundary_violation({SOURCE_PATH: candidate})
                )


if __name__ == "__main__":
    unittest.main()
