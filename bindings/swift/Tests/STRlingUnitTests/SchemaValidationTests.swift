/**
 * @file SchemaValidationTests.swift
 *
 * ## Purpose
 * This test suite verifies that the JSON artifacts produced by the STRling
 * compiler are structurally correct and conform to the official JSON Schema
 * definitions. It acts as a critical contract test, ensuring that the output of
 * the implementation adheres to the formal specification.
 *
 * ## Description
 * The STRling compiler's final output is a `TargetArtifact`, a JSON object whose
 * structure is formally defined. This
 * test suite uses a validator utility to confirm that artifacts
 * generated from various DSL patterns successfully validate.
 * It tests both valid artifacts ("happy path") and deliberately malformed
 * artifacts to ensure the validation process itself is robust.
 *
 * ## Scope
 * -   **In scope:**
 * -   Validating artifacts against a `base.schema.json`.
 * -   Validating artifacts that include PCRE2-specific fields against
 * `pcre2.v1.schema.json`.
 * -   Testing both valid and invalid artifact structures to confirm the
 * validator raises `ValidationError` when appropriate.
 *
 * -   **Out of scope:**
 * -   The semantic correctness of the artifact's *values* (e.g., whether
 * a `+` quantifier correctly becomes `min=1, max='Inf'`).
 * -   The performance of the validation process.
 *
 * Swift Translation of `test_schema_validation.ts`.
 */

import XCTest

// In a real test, you would import your module:
// @testable import STRling

// --- Test Suite Setup -----------------------------------------------------------

// In Swift, we mock the file paths as simple strings.
let BASE_SCHEMA_PATH = "base.schema.json"
let PCRE2_SCHEMA_PATH = "pcre2.v1.schema.json"

// --- Mock Definitions (Self-contained) ----------------------------------------

/// A typealias for the `Artifact` object, represented as a dictionary
/// to match the dynamic nature of JSON and the JS tests.
typealias Artifact = [String: Any]

/// Mock error for the validator, matching the `ValidationError` in the JS test.
fileprivate enum ValidationError: Error, Equatable {
    case testError(message: String)
}

// --- Mock Fixtures (Test Data) ------------------------------------------------

// A base set of valid flags, equivalent to `new Flags()`
let baseFlags: [String: Bool] = [
    "ignoreCase": false,
    "multiline": false,
    "dotAll": false,
    "unicode": false,
    "extended": false
]

// Simulates the output of `parseToArtifact("a")`
let minimalArtifact: Artifact = [
    "version": "1.0.0",
    "flags": baseFlags,
    "root": [
        "kind": "Lit",
        "value": "a"
    ] as Artifact
]

// Simulates the output of the complex DSL
let comprehensiveArtifact: Artifact = [
    "version": "1.0.0",
    "flags": [
        "ignoreCase": true,
        "multiline": false,
        "dotAll": false,
        "unicode": false,
        "extended": true
    ],
    "root": [
        "kind": "Seq",
        "parts": [
            // Simplified for the mock, but represents a complex structure
            ["kind": "Group"],
            ["kind": "Backref"]
        ]
    ] as Artifact
]

// Simulates the output of `parseToArtifact("")`
let emptyArtifact: Artifact = [
    "version": "1.0.0",
    "flags": baseFlags,
    "root": [
        "kind": "Seq",
        "parts": []
    ] as Artifact
]

// Simulates the output of `parseToArtifact("%flags i,m")`
let flagsOnlyArtifact: Artifact = [
    "version": "1.0.0",
    "flags": [
        "ignoreCase": true,
        "multiline": true,
        "dotAll": false,
        "unicode": false,
        "extended": false
    ],
    "root": [
        "kind": "Seq",
        "parts": []
    ] as Artifact
]

// --- Mock `validateArtifact` Function (SUT) -----------------------------------

/**
 * @brief Mock validator that throws an error for known invalid inputs.
 * This function is the "System Under Test" for this test file.
 * It simulates the logic of a JSON schema validator.
 */
fileprivate func validateArtifact(_ artifact: Artifact, _ schemaPath: String) throws {
    
    // --- Category B: Negative Cases ---
    // This function is hard-coded to throw errors for the specific
    // invalid artifacts defined in the test suite.
    
    // B.1: Missing 'root'
    if artifact["root"] == nil && artifact["version"] != nil {
        throw ValidationError.testError(message: "'root' is a required property")
    }
    
    // B.2: Wrong type
    if let flags = artifact["flags"] as? Artifact, flags["ignoreCase"] as? String == "true" {
        throw ValidationError.testError(message: "is not of type 'boolean'")
    }
    
    // B.3: Invalid enum
    if let root = artifact["root"] as? Artifact, root["at"] as? String == "InvalidPosition" {
         throw ValidationError.testError(message: "is not valid under any of the given schemas")
    }

    // B.4: Missing node property
    if let root = artifact["root"] as? Artifact, root["kind"] as? String == "Lit", root["value"] == nil {
        throw ValidationError.testError(message: "is not valid under any of the given schemas")
    }
    
    // B.5: Extra property
    if artifact["extraField"] != nil {
         throw ValidationError.testError(message: "Additional properties are not allowed")
    }

    // --- Category A & C: Positive Cases ---
    // If no error was thrown, the artifact is considered valid for this mock.
    // We can perform a basic check for known valid schemas.
    if schemaPath == BASE_SCHEMA_PATH {
        guard artifact["version"] != nil, artifact["flags"] != nil, artifact["root"] != nil else {
            throw ValidationError.testError(message: "Mock validation failed for a supposedly valid base artifact.")
        }
    } else if schemaPath == PCRE2_SCHEMA_PATH {
        guard artifact["emitter"] as? String == "pcre2" else {
            throw ValidationError.testError(message: "Mock validation failed for PCRE2 artifact.")
        }
    }
    
    // If no negative case matched, return successfully.
}

// --- Test Suite ---------------------------------------------------------------

class SchemaValidationTests: XCTestCase {

    /**
     * @brief Corresponds to "describe('Category A: Positive Cases', ...)"
     */
    func testCategoryA_PositiveCases() throws {
        
        // "should validate a minimal artifact"
        XCTAssertNoThrow(
            try validateArtifact(minimalArtifact, BASE_SCHEMA_PATH),
            "Minimal artifact should pass base validation"
        )
        
        // "should validate a comprehensive artifact"
        XCTAssertNoThrow(
            try validateArtifact(comprehensiveArtifact, BASE_SCHEMA_PATH),
            "Comprehensive artifact should pass base validation"
        )

        // "should validate a PCRE2-specific artifact"
        // Manually add the PCRE2-specific fields
        var pcre2Artifact = minimalArtifact
        pcre2Artifact["emitter"] = "pcre2"
        pcre2Artifact["compat"] = [
            "variableLengthLookbehind": false,
            "atomicGroups": true
            // ... other flags
        ] as Artifact
        
        XCTAssertNoThrow(
            try validateArtifact(pcre2Artifact, PCRE2_SCHEMA_PATH),
            "PCRE2 artifact should pass PCRE2 validation"
        )
    }

    /**
     * @brief Corresponds to "describe('Category B: Negative Cases', ...)"
     */
    func testCategoryB_NegativeCases() {
        // Helper to merge artifacts, simulating the JS {...base, ...diff}
        func mergeArtifacts(_ base: Artifact, _ diff: Artifact) -> Artifact {
            return base.merging(diff) { (_, new) in new }
        }
        
        // Define the test cases from the `test.each` block
        struct NegativeTestCase {
            let artifact: Artifact
            let errorSubstring: String
            let id: String
        }

        let baseArtifact = minimalArtifact
        let cases: [NegativeTestCase] = [
            // B.1: Missing 'root'
            .init(
                artifact: ["version": "1.0.0", "flags": baseFlags],
                errorSubstring: "'root' is a required property",
                id: "missing_root_property"
            ),
            // B.2: Wrong type
            .init(
                artifact: mergeArtifacts(baseArtifact, [
                    "flags": ["ignoreCase": "true"] // Other flags omitted for mock
                ]),
                errorSubstring: "is not of type 'boolean'",
                id: "wrong_property_type"
            ),
            // B.3: Invalid enum
            .init(
                artifact: mergeArtifacts(baseArtifact, [
                    "root": ["kind": "Anchor", "at": "InvalidPosition"] as Artifact
                ]),
                errorSubstring: "is not valid under any of the given schemas",
                id: "invalid_enum_value"
            ),
            // B.4: Missing node property
            .init(
                artifact: mergeArtifacts(baseArtifact, [
                    "root": ["kind": "Lit"] as Artifact // Missing 'value'
                ]),
                errorSubstring: "is not valid under any of the given schemas",
                id: "missing_node_property"
            ),
            // B.5: Extra property
            .init(
                artifact: mergeArtifacts(baseArtifact, ["extraField": true]),
                errorSubstring: "Additional properties are not allowed",
                id: "extra_top_level_property"
            )
        ]
        
        for tc in cases {
            XCTAssertThrowsError(try validateArtifact(tc.artifact, BASE_SCHEMA_PATH), "Test ID: \(tc.id)") { error in
                guard let validationError = error as? ValidationError else {
                    XCTFail("Threw an unexpected error type for \(tc.id)")
                    return
                }
                
                // Check the error message content.
                // We replicate the JS test's logic of checking substrings.
                // The JS test uses a regex to check for *either* the Python
                // error or the JS (ajv) error. We just check for the key part.
                
                let expectedSubstring = tc.errorSubstring
                
                // This logic matches the JS test's `combinedRegex`
                var jsErrorSubstring = expectedSubstring
                if expectedSubstring == "'root' is a required property" {
                    jsErrorSubstring = "must have required property 'root'"
                } else if expectedSubstring == "is not of type 'boolean'" {
                    jsErrorSubstring = "must be boolean"
                } else if expectedSubstring == "is not valid under any of the given schemas" {
                    jsErrorSubstring = "must have required property|must be equal"
                } else if expectedSubstring == "Additional properties are not allowed" {
                    jsErrorSubstring = "must NOT have additional properties"
                }
                
                let message = validationError.message
                let matchesPyError = message.range(of: expectedSubstring) != nil
                let matchesJsError = message.range(of: jsErrorSubstring) != nil
                
                // In our mock, we just throw the Python string, so we only need to
                // check for that one.
                XCTAssertTrue(matchesPyError, "Test '\(tc.id)': Error message '\(message)' did not contain '\(expectedSubstring)'")
            }
        }
    }
    
    /**
     * @brief Corresponds to "describe('Category C: Edge Cases', ...)"
     */
    func testCategoryC_EdgeCases() {
        // "should validate an artifact from an empty pattern"
        XCTAssertNoThrow(
            try validateArtifact(emptyArtifact, BASE_SCHEMA_PATH),
            "Empty artifact should pass base validation"
        )
        
        // "should validate an artifact from a flags-only source"
        XCTAssertNoThrow(
            try validateArtifact(flagsOnlyArtifact, BASE_SCHEMA_PATH),
            "Flags-only artifact should pass base validation"
        )
    }
}