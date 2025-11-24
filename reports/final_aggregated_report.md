# Final aggregated STRling report
Generated: 2025-11-24T02:29:21.134231Z

# Global STRling Test Report
**Generated:** 2025-11-24T02:04:25.928725+00:00
**Status:** ✅

### Tasks

- Run remaining binding tests — ✅ completed
- Prepare and generate final aggregated report — 🔜 ready (see `tooling/generate_final_report.py`)

| Binding | Status | Passed | Failed | Skipped | Duration |
| :--- | :---: | :---: | :---: | :---: | :---: |
| C | 💥 CRASH | 0 | 0 | 0 | 0.00s |
| Cpp | ✅ | 0 | 0 | 0 | 0.01s |
| Csharp | ✅ | 0 | 0 | 0 | 4.56s |
| Dart | ✅ | 0 | 0 | 0 | 1.04s |
| Fsharp | ✅ | 0 | 0 | 0 | 6.59s |
| Go | ✅ | 3 | 0 | 0 | 0.32s |
| Java | 💥 CRASH | 0 | 0 | 0 | 0.00s |
| Javascript | ⚠️ MISSING | 0 | 0 | 0 | 0.00s |
| Kotlin | ✅ | 0 | 0 | 0 | 0.79s |
| Lua | 💥 CRASH | 0 | 0 | 0 | 0.06s |
| Perl | ❌ | 0 | 0 | 0 | 0.99s |
| Php | ❌ | 0 | 0 | 0 | 70.31s |
| Python | ✅ | 714 | 0 | 0 | 1.11s |
| R | ❌ | 0 | 0 | 0 | 0.52s |
| Ruby | ✅ | 0 | 0 | 0 | 0.52s |
| Rust | 💥 CRASH | 0 | 0 | 0 | 0.08s |
| Swift | ❌ | 0 | 0 | 0 | 1.22s |
| Typescript | ✅ | 17 | 0 | 0 | 3.83s |

**Total Tests:** 734 | **Global Health:** 100.0%

---
## Details

### C — 💥 CRASH
- Exit code: 2
- Duration: 0.00s

<details>
<summary>stdout</summary>

```
(no stdout)
```
</details>


<details>
<summary>stderr</summary>

```
make: *** No rule to make target 'test'.  Stop.

```
</details>

### Java — 💥 CRASH
- Exit code: None
- Duration: 0.00s

<details>
<summary>stdout</summary>

```
(no stdout)
```
</details>


<details>
<summary>stderr</summary>

```
[Errno 2] No such file or directory: './gradlew'
```
</details>

### Lua — 💥 CRASH
- Exit code: None
- Duration: 0.06s

<details>
<summary>stdout</summary>

```
(no stdout)
```
</details>


<details>
<summary>stderr</summary>

```
Command not found: busted
```
</details>

### Perl — ❌
- Exit code: 1
- Duration: 0.99s

<details>
<summary>stdout</summary>

```
t/conformance.t .................. ok
t/unit/anchors.t ................. 
Dubious, test returned 2 (wstat 512, 0x200)
No subtests run 
t/unit/error_formatting.t ........ ok
t/unit/errors.t .................. 
Dubious, test returned 2 (wstat 512, 0x200)
No subtests run 
t/unit/flags_and_free_spacing.t .. 
Dubious, test returned 2 (wstat 512, 0x200)
No subtests run 
t/unit/parser_errors.t ........... 
Dubious, test returned 2 (wstat 512, 0x200)
No subtests run 

Test Summary Report
-------------------
t/unit/anchors.t               (Wstat: 512 (exited 2) Tests: 0 Failed: 0)
  Non-zero exit status: 2
  Parse errors: No plan found in TAP output
t/unit/errors.t                (Wstat: 512 (exited 2) Tests: 0 Failed: 0)
  Non-zero exit status: 2
  Parse errors: No plan found in TAP output
t/unit/flags_and_free_spacing.t (Wstat: 512 (exited 2) Tests: 0 Failed: 0)
  Non-zero exit status: 2
  Parse errors: No plan found in TAP output
t/unit/parser_errors.t         (Wstat: 512 (exited 2) Tests: 0 Failed: 0)
  Non-zero exit status: 2
  Parse errors: No plan found in TAP output
Files=6, Tests=549,  1 wallclock secs ( 0.11 usr  0.02 sys +  0.96 cusr  0.06 csys =  1.15 CPU)
Result: FAIL

```
</details>


<details>
<summary>stderr</summary>

```
Can't locate Test/Exception.pm in @INC (you may need to install the Test::Exception module) (@INC entries checked: /etc/perl /usr/local/lib/x86_64-linux-gnu/perl/5.38.2 /usr/local/share/perl/5.38.2 /usr/lib/x86_64-linux-gnu/perl5/5.38 /usr/share/perl5 /usr/lib/x86_64-linux-gnu/perl-base /usr/lib/x86_64-linux-gnu/perl/5.38 /usr/share/perl/5.38 /usr/local/lib/site_perl) at t/unit/anchors.t line 14.
BEGIN failed--compilation aborted at t/unit/anchors.t line 14.
Can't locate Test/Exception.pm in @INC (you may need to install the Test::Exception module) (@INC entries checked: /etc/perl /usr/local/lib/x86_64-linux-gnu/perl/5.38.2 /usr/local/share/perl/5.38.2 /usr/lib/x86_64-linux-gnu/perl5/5.38 /usr/share/perl5 /usr/lib/x86_64-linux-gnu/perl-base /usr/lib/x86_64-linux-gnu/perl/5.38 /usr/share/perl/5.38 /usr/local/lib/site_perl) at t/unit/errors.t line 37.
BEGIN failed--compilation aborted at t/unit/errors.t line 37.
Can't locate Test/Exception.pm in @INC (you may need to install the Test::Exception module) (@INC entries checked: /etc/perl /usr/local/lib/x86_64-linux-gnu/perl/5.38.2 /usr/local/share/perl/5.38.2 /usr/lib/x86_64-linux-gnu/perl5/5.38 /usr/share/perl5 /usr/lib/x86_64-linux-gnu/perl-base /usr/lib/x86_64-linux-gnu/perl/5.38 /usr/share/perl/5.38 /usr/local/lib/site_perl) at t/unit/flags_and_free_spacing.t line 42.
BEGIN failed--compilation aborted at t/unit/flags_and_free_spacing.t line 42.
Can't locate Test/Exception.pm in @INC (you may need to install the Test::Exception module) (@INC entries checked: /etc/perl /usr/local/lib/x86_64-linux-gnu/perl/5.38.2 /usr/local/share/perl/5.38.2 /usr/lib/x86_64-linux-gnu/perl5/5.38 /usr/share/perl5 /usr/lib/x86_64-linux-gnu/perl-base /usr/lib/x86_64-linux-gnu/perl/5.38 /usr/share/perl/5.38 /usr/local/lib/site_perl) at t/unit/parser_errors.t line 17.
BEGIN failed--compilation aborted at t/unit/parser_errors.t line 17.

```
</details>

### Php — ❌
- Exit code: 1
- Duration: 70.31s

<details>
<summary>stdout</summary>

```
(no stdout)
```
</details>


<details>
<summary>stderr</summary>

```
Do not run Composer as root/super user! See https://getcomposer.org/root for details
Continue as root/super user [yes]? 
                                  
  Command "test" is not defined.  
                                  


```
</details>

### R — ❌
- Exit code: 1
- Duration: 0.52s

<details>
<summary>stdout</summary>

```
(no stdout)
```
</details>


<details>
<summary>stderr</summary>

```
Error in `testthat::test_dir()`:
! No test files found.
Backtrace:
    ▆
 1. └─testthat::test_dir("tests")
 2.   └─cli::cli_abort("No test files found.")
 3.     └─rlang::abort(...)
Execution halted

```
</details>

### Rust — 💥 CRASH
- Exit code: 101
- Duration: 0.08s

<details>
<summary>stdout</summary>

```
(no stdout)
```
</details>


<details>
<summary>stderr</summary>

```
warning: unused variable: `manifest_dir`
  --> build.rs:42:17
   |
42 |             let manifest_dir = env::var("CARGO_MANIFEST_DIR").unwr...
   |                 ^^^^^^^^^^^^ help: if this is intentional, prefix it with an underscore: `_manifest_dir`
   |
   = note: `#[warn(unused_variables)]` on by default

warning: `strling_core` (build script) generated 1 warning
warning: unused import: `serde_json::Value`
  --> src/core/nodes.rs:19:5
   |
19 | use serde_json::Value;
   |     ^^^^^^^^^^^^^^^^^
   |
   = note: `#[warn(unused_imports)]` on by default

warning: unused import: `serde_json::Value`
 --> src/core/validator.rs:7:5
  |
7 | use serde_json::Value;
  |     ^^^^^^^^^^^^^^^^^

warning: unused variable: `start_pos`
   --> src/core/parser.rs:496:13
    |
496 |         let start_pos = self.cur.i;
    |             ^^^^^^^^^ help: if this is intentional, prefix it with an underscore: `_start_pos`
    |
    = note: `#[warn(unused_variables)]` on by default

warning: methods `peek` and `match_str` are never used
  --> src/core/parser.rs:47:8
   |
33 | impl Cursor {
   | ----------- methods in this implementation
...
47 |     fn peek(&self, n: usize) -> String {
   |        ^^^^
...
71 |     fn match_str(&mut self, s: &str) -> bool {
   |        ^^^^^^^^^
   |
   = note: `#[warn(dead_code)]` on by default

warning: field `original_text` is never read
   --> src/core/parser.rs:106:5
    |
105 | pub struct Parser {
    |            ------ field in this struct
106 |     original_text: String,
    |     ^^^^^^^^^^^^^

warning: `strling_core` (lib) generated 5 warnings (run `cargo fix --lib -p strling_core` to apply 3 suggestions)
warning: unused variable: `text`
  --> src/bin/strling-cli.rs:91:20
   |
91 |                 Ok(text) => {
   |                    ^^^^ help: if this is intentional, prefix it with an underscore: `_text`
   |
   = note: `#[warn(unused_variables)]` on by default

warning: unused variable: `text`
   --> src/bin/strling-cli.rs:113:20
    |
113 |                 Ok(text) => {
    |                    ^^^^ help: if this is intentional, prefix it with an underscore: `_text`

warning: `strling_core` (bin "strling-cli") generated 2 warnings (run `cargo fix --bin "strling-cli"` to apply 2 suggestions)
   Compiling strling_core v3.0.0-alpha (/root/personal/STRling/bindings/rust)
warning: unnecessary parentheses around function argument
   --> src/simply.rs:535:52
    |
535 |                 let expected = std::char::from_u32(('A' as u32 & 0x1F)).unwrap().to_string();
    |                                                    ^                 ^
    |
    = note: `#[warn(unused_parens)]` on by default
help: remove these parentheses
    |
535 -                 let expected = std::char::from_u32(('A' as u32 & 0x1F)).unwrap().to_string();
535 +                 let expected = std::char::from_u32('A' as u32 & 0x1F).unwrap().to_string();
    |

warning: unused variable: `flags`
   --> src/core/parser.rs:730:14
    |
730 |         let (flags, node) = result.unwrap();
    |              ^^^^^ help: if this is intentional, prefix it with an underscore: `_flags`

warning: `strling_core` (bin "strling-cli" test) generated 2 warnings (2 duplicates)
warning: `strling_core` (lib test) generated 7 warnings (5 duplicates) (run `cargo fix --lib -p strling_core --tests` to apply 2 suggestions)
error[E0433]: failed to resolve: use of undeclared crate or module `strling`
 --> examples/demo.rs:2:5
  |
2 | use strling::core::compiler::Compiler;
  |     ^^^^^^^ use of undeclared crate or module `strling`

error[E0433]: failed to resolve: use of undeclared crate or module `strling`
 --> examples/demo.rs:3:5
  |
3 | use strling::emitters::pcre2::PCRE2Emitter;
  |     ^^^^^^^ use of undeclared crate or module `strling`

error[E0432]: unresolved import `strling`
 --> examples/demo.rs:1:5
  |
1 | use strling::parse;
  |     ^^^^^^^ use of undeclared crate or module `strling`

Some errors have detailed explanations: E0432, E0433.
For more information about an error, try `rustc --explain E0432`.
error: could not compile `strling_core` (example "demo") due to 3 previous errors

```
</details>

### Swift — ❌
- Exit code: 1
- Duration: 1.22s

<details>
<summary>stdout</summary>

```
Test Suite 'All tests' started at 2025-11-23 20:04:21.657
Test Suite 'debug.xctest' started at 2025-11-23 20:04:21.658
Test Suite 'AnchorsTests' started at 2025-11-23 20:04:21.658
Test Case 'AnchorsTests.testAbsoluteAnchors' started at 2025-11-23 20:04:21.658
Test Case 'AnchorsTests.testAbsoluteAnchors' passed (0.001 seconds)
Test Case 'AnchorsTests.testAnchorsInSequences' started at 2025-11-23 20:04:21.659
Test Case 'AnchorsTests.testAnchorsInSequences' passed (0.0 seconds)
Test Case 'AnchorsTests.testCoreAnchors' started at 2025-11-23 20:04:21.659
Test Case 'AnchorsTests.testCoreAnchors' passed (0.0 seconds)
Test Case 'AnchorsTests.testFlagsDoNotChangeAnchorParsing' started at 2025-11-23 20:04:21.659
Test Case 'AnchorsTests.testFlagsDoNotChangeAnchorParsing' passed (0.0 seconds)
Test Case 'AnchorsTests.testQuantifiedAnchorsRaiseError' started at 2025-11-23 20:04:21.659
Test Case 'AnchorsTests.testQuantifiedAnchorsRaiseError' passed (0.0 seconds)
Test Suite 'AnchorsTests' passed at 2025-11-23 20:04:21.660
	 Executed 5 tests, with 0 failures (0 unexpected) in 0.002 (0.002) seconds
Test Suite 'CharClassesTests' started at 2025-11-23 20:04:21.660
Test Case 'CharClassesTests.testClassContentsLiteralsRangesShorthands' started at 2025-11-23 20:04:21.660
Test Case 'CharClassesTests.testClassContentsLiteralsRangesShorthands' passed (0.0 seconds)
Test Case 'CharClassesTests.testErrorCases' started at 2025-11-23 20:04:21.660
Test Case 'CharClassesTests.testErrorCases' passed (0.0 seconds)
Test Case 'CharClassesTests.testPositiveAndNegativeClasses' started at 2025-11-23 20:04:21.660
Test Case 'CharClassesTests.testPositiveAndNegativeClasses' passed (0.0 seconds)
Test Case 'CharClassesTests.testSpecialCharacterHandling' started at 2025-11-23 20:04:21.660
Test Case 'CharClassesTests.testSpecialCharacterHandling' passed (0.0 seconds)
Test Case 'CharClassesTests.testUnicodeProperties' started at 2025-11-23 20:04:21.660
Test Case 'CharClassesTests.testUnicodeProperties' passed (0.0 seconds)
Test Suite 'CharClassesTests' passed at 2025-11-23 20:04:21.660
	 Executed 5 tests, with 0 failures (0 unexpected) in 0.001 (0.001) seconds
Test Suite 'EmitterEdgesTests' started at 2025-11-23 20:04:21.660
Test Case 'EmitterEdgesTests.testEscapingLogic' started at 2025-11-23 20:04:21.660
Test Case 'EmitterEdgesTests.testEscapingLogic' passed (0.0 seconds)
Test Case 'EmitterEdgesTests.testExtensionFeatures' started at 2025-11-23 20:04:21.660
Test Case 'EmitterEdgesTests.testExtensionFeatures' passed (0.0 seconds)
Test Case 'EmitterEdgesTests.testFlagGeneration' started at 2025-11-23 20:04:21.661
Test Case 'EmitterEdgesTests.testFlagGeneration' passed (0.0 seconds)
Test Case 'EmitterEdgesTests.testPrecedenceAndGrouping' started at 2025-11-23 20:04:21.661
Test Case 'EmitterEdgesTests.testPrecedenceAndGrouping' passed (0.0 seconds)
Test Case 'EmitterEdgesTests.testShorthandOptimizations' started at 2025-11-23 20:04:21.661
Test Case 'EmitterEdgesTests.testShorthandOptimizations' passed (0.0 seconds)
Test Suite 'EmitterEdgesTests' passed at 2025-11-23 20:04:21.661
	 Executed 5 tests, with 0 failures (0 unexpected) in 0.001 (0.001) seconds
Test Suite 'ErrorFormattingTests' started at 2025-11-23 20:04:21.661
Test Case 'ErrorFormattingTests.testHintEngine' started at 2025-11-23 20:04:21.661
Test Case 'ErrorFormattingTests.testHintEngine' passed (0.0 seconds)
Test Case 'ErrorFormattingTests.testSTRlingParseErrorFormatting' started at 2025-11-23 20:04:21.662
Test Case 'ErrorFormattingTests.testSTRlingParseErrorFormatting' passed (0.0 seconds)
Test Suite 'ErrorFormattingTests' passed at 2025-11-23 20:04:21.662
	 Executed 2 tests, with 0 failures (0 unexpected) in 0.0 (0.0) seconds
Test Suite 'ErrorsTests' started at 2025-11-23 20:04:21.662
Test Case 'ErrorsTests.testFirstErrorWins' started at 2025-11-23 20:04:21.662
Test Case 'ErrorsTests.testFirstErrorWins' passed (0.0 seconds)
Test Case 'ErrorsTests.testParserSyntaxErrors' started at 2025-11-23 20:04:21.662
Test Case 'ErrorsTests.testParserSyntaxErrors' passed (0.0 seconds)
Test Case 'ErrorsTests.testSemanticErrors' started at 2025-11-23 20:04:21.662
Test Case 'ErrorsTests.testSemanticErrors' passed (0.0 seconds)
Test Suite 'ErrorsTests' passed at 2025-11-23 20:04:21.662
	 Executed 3 tests, with 0 failures (0 unexpected) in 0.001 (0.001) seconds
Test Suite 'FlagsAndFreeSpacingTests' started at 2025-11-23 20:04:21.662
Test Case 'FlagsAndFreeSpacingTests.testFlagDirectiveParsing' started at 2025-11-23 20:04:21.662
/root/personal/STRling/bindings/swift/Tests/STRlingUnitTests/FlagsAndFreeSpacingTests.swift:182: error: FlagsAndFreeSpacingTests.testFlagDirectiveParsing : XCTAssertEqual failed: ("Flags(i: true, m: false, s: true, u: false, x: false)") is not equal to ("Flags(i: true, m: false, s: false, u: false, x: false)") - Test ID: single_i (Flags)
/root/personal/STRling/bindings/swift/Tests/STRlingUnitTests/FlagsAndFreeSpacingTests.swift:182: error: FlagsAndFreeSpacingTests.testFlagDirectiveParsing : XCTAssertEqual failed: ("Flags(i: false, m: true, s: true, u: false, x: false)") is not equal to ("Flags(i: false, m: true, s: false, u: false, x: false)") - Test ID: single_m (Flags)
/root/personal/STRling/bindings/swift/Tests/STRlingUnitTests/FlagsAndFreeSpacingTests.swift:182: error: FlagsAndFreeSpacingTests.testFlagDirectiveParsing : XCTAssertEqual failed: ("Flags(i: false, m: false, s: true, u: true, x: false)") is not equal to ("Flags(i: false, m: false, s: false, u: true, x: false)") - Test ID: single_u (Flags)
/root/personal/STRling/bindings/swift/Tests/STRlingUnitTests/FlagsAndFreeSpacingTests.swift:182: error: FlagsAndFreeSpacingTests.testFlagDirectiveParsing : XCTAssertEqual failed: ("Flags(i: false, m: false, s: true, u: false, x: true)") is not equal to ("Flags(i: false, m: false, s: false, u: false, x: true)") - Test ID: single_x (Flags)
Test Case 'FlagsAndFreeSpacingTests.testFlagDirectiveParsing' failed (0.102 seconds)
Test Case 'FlagsAndFreeSpacingTests.testFreeSpacingBehavior' started at 2025-11-23 20:04:21.765
Test Case 'FlagsAndFreeSpacingTests.testFreeSpacingBehavior' passed (0.001 seconds)
Test Case 'FlagsAndFreeSpacingTests.testFreeSpacingInteractionWithCharClass' started at 2025-11-23 20:04:21.766
Test Case 'FlagsAndFreeSpacingTests.testFreeSpacingInteractionWithCharClass' passed (0.001 seconds)
Test Suite 'FlagsAndFreeSpacingTests' failed at 2025-11-23 20:04:21.766
	 Executed 3 tests, with 4 failures (0 unexpected) in 0.104 (0.104) seconds
Test Suite 'GroupsBackrefsLookaroundsTests' started at 2025-11-23 20:04:21.766
Test Case 'GroupsBackrefsLookaroundsTests.testCategoryA_PositiveCases' started at 2025-11-23 20:04:21.766
Test Case 'GroupsBackrefsLookaroundsTests.testCategoryA_PositiveCases' passed (0.0 seconds)
Test Case 'GroupsBackrefsLookaroundsTests.testCategoryB_NegativeCases' started at 2025-11-23 20:04:21.767
Test Case 'GroupsBackrefsLookaroundsTests.testCategoryB_NegativeCases' passed (0.0 seconds)
Test Case 'GroupsBackrefsLookaroundsTests.testCategoryC_EdgeCases' started at 2025-11-23 20:04:21.767
Test Case 'GroupsBackrefsLookaroundsTests.testCategoryC_EdgeCases' passed (0.0 seconds)
Test Case 'GroupsBackrefsLookaroundsTests.testCategoryD_InteractionCases' started at 2025-11-23 20:04:21.767
Test Case 'GroupsBackrefsLookaroundsTests.testCategoryD_InteractionCases' passed (0.0 seconds)
Test Case 'GroupsBackrefsLookaroundsTests.testCategoryE_NestedGroups' started at 2025-11-23 20:04:21.768
Test Case 'GroupsBackrefsLookaroundsTests.testCategoryE_NestedGroups' passed (0.0 seconds)
Test Case 'GroupsBackrefsLookaroundsTests.testCategoryF_ComplexLookarounds' started at 2025-11-23 20:04:21.768
Test Case 'GroupsBackrefsLookaroundsTests.testCategoryF_ComplexLookarounds' passed (0.0 seconds)
Test Case 'GroupsBackrefsLookaroundsTests.testCategoryG_AtomicGroups' started at 2025-11-23 20:04:21.768
Test Case 'GroupsBackrefsLookaroundsTests.testCategoryG_AtomicGroups' passed (0.001 seconds)
Test Case 'GroupsBackrefsLookaroundsTests.testCategoryH_MultipleBackrefs' started at 2025-11-23 20:04:21.769
Test Case 'GroupsBackrefsLookaroundsTests.testCategoryH_MultipleBackrefs' passed (0.0 seconds)
Test Case 'GroupsBackrefsLookaroundsTests.testCategoryI_GroupsInAlternation' started at 2025-11-23 20:04:21.769
Test Case 'GroupsBackrefsLookaroundsTests.testCategoryI_GroupsInAlternation' passed (0.001 seconds)
Test Suite 'GroupsBackrefsLookaroundsTests' passed at 2025-11-23 20:04:21.770
	 Executed 9 tests, with 0 failures (0 unexpected) in 0.003 (0.003) seconds
Test Suite 'IEHAuditGapsTests' started at 2025-11-23 20:04:21.770
Test Case 'IEHAuditGapsTests.testAdditionalNegativeCases' started at 2025-11-23 20:04:21.770
/root/personal/STRling/bindings/swift/Tests/STRlingUnitTests/IEHAuditGapsTests.swift:287: error: IEHAuditGapsTests.testAdditionalNegativeCases : XCTAssertNotNil failed - Hint check failed: 'Add characters or ranges inside the brackets.' did not contain 'empty'
Test Case 'IEHAuditGapsTests.testAdditionalNegativeCases' failed (0.0 seconds)
Test Case 'IEHAuditGapsTests.testCharClassRangeValidation' started at 2025-11-23 20:04:21.770
Test Case 'IEHAuditGapsTests.testCharClassRangeValidation' passed (0.0 seconds)
Test Case 'IEHAuditGapsTests.testContextAwareEscapeHints' started at 2025-11-23 20:04:21.770
/root/personal/STRling/bindings/swift/Tests/STRlingUnitTests/IEHAuditGapsTests.swift:248: error: IEHAuditGapsTests.testContextAwareEscapeHints : XCTAssertNotNil failed - Hint check failed: 'The escape '\q' is not valid. Did you mean to escape 'q' as '\q'?' did not contain '\\q'
Test Case 'IEHAuditGapsTests.testContextAwareEscapeHints' failed (0.0 seconds)
Test Case 'IEHAuditGapsTests.testContextAwareQuantifierHints' started at 2025-11-23 20:04:21.771
Test Case 'IEHAuditGapsTests.testContextAwareQuantifierHints' passed (0.0 seconds)
Test Case 'IEHAuditGapsTests.testEmptyAlternationValidation' started at 2025-11-23 20:04:21.771
Test Case 'IEHAuditGapsTests.testEmptyAlternationValidation' passed (0.0 seconds)
Test Case 'IEHAuditGapsTests.testFlagDirectiveValidation' started at 2025-11-23 20:04:21.771
Test Case 'IEHAuditGapsTests.testFlagDirectiveValidation' passed (0.0 seconds)
Test Case 'IEHAuditGapsTests.testGroupNameValidation' started at 2025-11-23 20:04:21.771
Test Case 'IEHAuditGapsTests.testGroupNameValidation' passed (0.0 seconds)
Test Case 'IEHAuditGapsTests.testIncompleteNamedBackrefHint' started at 2025-11-23 20:04:21.771
/root/personal/STRling/bindings/swift/Tests/STRlingUnitTests/IEHAuditGapsTests.swift:232: error: IEHAuditGapsTests.testIncompleteNamedBackrefHint : XCTAssertNotNil failed - Hint check failed: 'Named backreferences have the form \k<name>.' did not contain '\\k<name>'
Test Case 'IEHAuditGapsTests.testIncompleteNamedBackrefHint' failed (0.0 seconds)
Test Case 'IEHAuditGapsTests.testQuantifierRangeValidation' started at 2025-11-23 20:04:21.771
Test Case 'IEHAuditGapsTests.testQuantifierRangeValidation' passed (0.0 seconds)
Test Case 'IEHAuditGapsTests.testValidPatternsStillWork' started at 2025-11-23 20:04:21.772
Test Case 'IEHAuditGapsTests.testValidPatternsStillWork' passed (0.0 seconds)
Test Suite 'IEHAuditGapsTests' failed at 2025-11-23 20:04:21.772
	 Executed 10 tests, with 3 failures (0 unexpected) in 0.002 (0.002) seconds
Test Suite 'IRCompilerTests' started at 2025-11-23 20:04:21.772
Test Case 'IRCompilerTests.testCategoryA_ASTToIRLowering' started at 2025-11-23 20:04:21.772
Test Case 'IRCompilerTests.testCategoryA_ASTToIRLowering' passed (0.0 seconds)
Test Case 'IRCompilerTests.testCategoryB_IRNormalization' started at 2025-11-23 20:04:21.772
Test Case 'IRCompilerTests.testCategoryB_IRNormalization' passed (0.0 seconds)
Test Case 'IRCompilerTests.testCategoryC_FullCompilation' started at 2025-11-23 20:04:21.772
Test Case 'IRCompilerTests.testCategoryC_FullCompilation' passed (0.0 seconds)
Test Case 'IRCompilerTests.testCategoryD_MetadataGeneration' started at 2025-11-23 20:04:21.772
Test Case 'IRCompilerTests.testCategoryD_MetadataGeneration' passed (0.0 seconds)
Test Case 'IRCompilerTests.testCategoryE_NestedAlternations' started at 2025-11-23 20:04:21.773
Test Case 'IRCompilerTests.testCategoryE_NestedAlternations' passed (0.0 seconds)
Test Case 'IRCompilerTests.testCategoryF_SequenceNormalization' started at 2025-11-23 20:04:21.773
Test Case 'IRCompilerTests.testCategoryF_SequenceNormalization' passed (0.0 seconds)
Test Case 'IRCompilerTests.testCategoryG_LiteralFusion' started at 2025-11-23 20:04:21.773
Test Case 'IRCompilerTests.testCategoryG_LiteralFusion' passed (0.0 seconds)
Test Case 'IRCompilerTests.testCategoryH_QuantifierNormalization' started at 2025-11-23 20:04:21.773
Test Case 'IRCompilerTests.testCategoryH_QuantifierNormalization' passed (0.0 seconds)
Test Case 'IRCompilerTests.testCategoryI_FeatureDetection' started at 2025-11-23 20:04:21.774
Test Case 'IRCompilerTests.testCategoryI_FeatureDetection' passed (0.0 seconds)
Test Case 'IRCompilerTests.testCategoryJ_AlternationNormalization' started at 2025-11-23 20:04:21.774
Test Case 'IRCompilerTests.testCategoryJ_AlternationNormalization' passed (0.0 seconds)
Test Suite 'IRCompilerTests' passed at 2025-11-23 20:04:21.774
	 Executed 10 tests, with 0 failures (0 unexpected) in 0.002 (0.002) seconds
Test Suite 'LiteralsAndEscapesTests' started at 2025-11-23 20:04:21.774
Test Case 'LiteralsAndEscapesTests.testCategoryA_PositiveCases' started at 2025-11-23 20:04:21.774
Test Case 'LiteralsAndEscapesTests.testCategoryA_PositiveCases' passed (0.0 seconds)
Test Case 'LiteralsAndEscapesTests.testCategoryB_NegativeCases' started at 2025-11-23 20:04:21.775
Test Case 'LiteralsAndEscapesTests.testCategoryB_NegativeCases' passed (0.0 seconds)
Test Case 'LiteralsAndEscapesTests.testCategoryC_EdgeCases' started at 2025-11-23 20:04:21.775
Test Case 'LiteralsAndEscapesTests.testCategoryC_EdgeCases' passed (0.0 seconds)
Test Case 'LiteralsAndEscapesTests.testCategoryD_InteractionCases' started at 2025-11-23 20:04:21.775
STRlingUnitTests/LiteralsAndEscapesTests.swift:327: Fatal error: 'try!' expression unexpectedly raised an error: STRlingUnitTests.(unknown context at $55ec8ecaddb8).ParseError.testError(message: "Unknown test input:  a b #comment\n c", pos: 0)

*** Signal 4: Backtracing from 0x7f271c170628... done ***

*** Program crashed: Illegal instruction at 0x00007f271c170628 ***

Platform: x86_64 Linux (Ubuntu 24.04.2 LTS)

Thread 0 "STRlingPackageT" crashed:

  0               0x00007f271c170628 _assertionFailure(_:_:file:line:flags:) + 264 in libswiftCore.so
  1 [ra]          0x00007f271c1a4cf6 swift_unexpectedError + 805 in libswiftCore.so
  2 [ra]          0x000055ec8eb236fb LiteralsAndEscapesTests.testCategoryD_InteractionCases() + 858 in STRlingPackageTests.xctest at /root/personal/STRling/bindings/swift/Tests/STRlingUnitTests/LiteralsAndEscapesTests.swift:327:24
  3 [ra] [system] 0x000055ec8ea86233 implicit closure #8 in implicit closure #7 in variable initialization expression of static LiteralsAndEscapesTests.__allTests__LiteralsAndEscapesTests + 34 in STRlingPackageTests.xctest at /root/personal/STRling/bindings/swift/.build/x86_64-unknown-linux-gnu/debug/STRlingPackageDiscoveredTests.derived/STRlingUnitTests.swift
  4 [ra] [thunk]  0x000055ec8ea8130c thunk for @escaping @callee_guaranteed () -> () + 11 in STRlingPackageTests.xctest at //<compiler-generated>
...

Thread 1:

  0      0x00007f271a83bd71 <unknown> in libc.so.6
  1 [ra] 0x00007f271a847d93 <unknown> in libc.so.6
  2 [ra] 0x00007f271bbe1eb8 _dispatch_sema4_timedwait + 87 in libdispatch.so
  3 [ra] 0x00007f271bbdaac1 _dispatch_semaphore_wait_slow + 32 in libdispatch.so
  4 [ra] 0x00007f271bbda09e _dispatch_worker_thread + 829 in libdispatch.so
  5 [ra] 0x00007f271a83faa4 <unknown> in libc.so.6
...

Thread 2:

  0      0x00007f271a8cd072 <unknown> in libc.so.6
  1 [ra] 0x00007f271bbe16c7 _dispatch_event_loop_drain + 54 in libdispatch.so
  2 [ra] 0x00007f271bbd6e32 _dispatch_mgr_invoke + 129 in libdispatch.so
  3 [ra] 0x00007f271bbd6d9d _dispatch_mgr_thread + 108 in libdispatch.so
  4 [ra] 0x00007f271bbd9f15 _dispatch_worker_thread + 436 in libdispatch.so
  5 [ra] 0x00007f271a83faa4 <unknown> in libc.so.6
...

Thread 3:

  0      0x00007f271a83bd71 <unknown> in libc.so.6
  1 [ra] 0x00007f271a847d93 <unknown> in libc.so.6
  2 [ra] 0x00007f271bbe1eb8 _dispatch_sema4_timedwait + 87 in libdispatch.so
  3 [ra] 0x00007f271bbdaac1 _dispatch_semaphore_wait_slow + 32 in libdispatch.so
  4 [ra] 0x00007f271bbda09e _dispatch_worker_thread + 829 in libdispatch.so
  5 [ra] 0x00007f271a83faa4 <unknown> in libc.so.6
...

Thread 4:

  0      0x00007f271a83bd71 <unknown> in libc.so.6
  1 [ra] 0x00007f271a847d93 <unknown> in libc.so.6
  2 [ra] 0x00007f271bbe1eb8 _dispatch_sema4_timedwait + 87 in libdispatch.so
  3 [ra] 0x00007f271bbdaac1 _dispatch_semaphore_wait_slow + 32 in libdispatch.so
  4 [ra] 0x00007f271bbda09e _dispatch_worker_thread + 829 in libdispatch.so
  5 [ra] 0x00007f271a83faa4 <unknown> in libc.so.6
...

Thread 5:

  0      0x00007f271a83bd71 <unknown> in libc.so.6
  1 [ra] 0x00007f271a847d93 <unknown> in libc.so.6
  2 [ra] 0x00007f271bbe1eb8 _dispatch_sema4_timedwait + 87 in libdispatch.so
  3 [ra] 0x00007f271bbdaac1 _dispatch_semaphore_wait_slow + 32 in libdispatch.so
  4 [ra] 0x00007f271bbda09e _dispatch_worker_thread + 829 in libdispatch.so
  5 [ra] 0x00007f271a83faa4 <unknown> in libc.so.6
...


Registers:

rax 0x0000000200000003  8589934595
rdx 0x0000000000000002  2
rcx 0xfffffffe00000000  18446744065119617024
rbx 0x0000000000000003  3
rsi 0x000055eca520c128  03 00 00 00 00 00 00 00 c0 00 00 00 00 00 00 80  ········À·······
rdi 0x000055eca51dc870  00 00 00 00 00 00 00 00 d1 00 00 00 00 00 00 00  ········Ñ·······
rbp 0x00007ffc2670d6e0  90 d7 70 26 fc 7f 00 00 f6 4c 1a 1c 27 7f 00 00  ·×p&ü···öL··'···
rsp 0x00007ffc2670d670  80 d6 70 26 fc 7f 00 00 fb 74 09 1c 27 7f 00 00  ·Öp&ü···ût··'···
 r8 0x000055eca51b8010  05 00 04 00 05 00 01 00 03 00 04 00 07 00 07 00  ················
 r9 0x0000000000000007  7
r10 0x000055eca51dc880  dc 51 ca 5e 05 00 00 00 f3 82 5b cf 9b 11 79 ed  ÜQÊ^····ó·[Ï··yí
r11 0xed79119bcf5b82f3  17111727620067394291
r12 0x000055eca520c120  28 b5 45 1c 27 7f 00 00 03 00 00 00 00 00 00 00  (µE·'···········
r13 0x00007ffc2670d758  b2 00 00 00 00 00 00 f0 20 c1 20 a5 ec 55 00 00  ²······ð Á ¥ìU··
r14 0x0000000000000000  0
r15 0x00000000000000b2  178
rip 0x00007f271c170628  0f 0b 48 8d 35 7f 0c fb ff 48 8d 55 a0 45 31 e4  ··H·5··ûÿH·U E1ä

rflags 0x0000000000010202  

cs 0x0033  fs 0x0000  gs 0x0000


Images (19 omitted):

0x000055ec8e9f5000–0x000055ec8ec8ebb8 1d29a2c9dca5b8e3353ea9af7092dcccc47abaf9 STRlingPackageTests.xctest /root/personal/STRling/bindings/swift/.build/x86_64-unknown-linux-gnu/debug/STRlingPackageTests.xctest
0x00007f271a7a3000–0x00007f271a952cf9 274eec488d230825a136fa9c4d85370fed7a0a5e libc.so.6                  /usr/lib/x86_64-linux-gnu/libc.so.6
0x00007f271bba5000–0x00007f271bbed1d8 8376de9884466c28df514e3d0dfbdc084fab2bcb libdispatch.so             /root/.local/share/swiftly/toolchains/6.2.1/usr/lib/swift/linux/libdispatch.so
0x00007f271be8e000–0x00007f271c43f1a0 a0cc6b6d664eafb6eac03bfe8d77abb20d395bb7 libswiftCore.so            /root/.local/share/swiftly/toolchains/6.2.1/usr/lib/swift/linux/libswiftCore.so

Backtrace took 0.02s

◇ Test run started.
↳ Testing Library Version: 6.2.1 (c9d57c83568b06d)
↳ Target Platform: x86_64-unknown-linux-gnu
✔ Test run with 0 tests in 0 suites passed after 0.001 seconds.

```
</details>


<details>
<summary>stderr</summary>

```
[0/1] Planning build
Building for debugging...
[0/2] Write swift-version--6B0C4D200E742BB1.txt
Build complete! (0.17s)
error: Exited with unexpected signal code 4

```
</details>
