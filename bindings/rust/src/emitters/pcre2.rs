//! PCRE2 Emitter - Generate PCRE2-compatible regex patterns
//!
//! This module implements code generation for the PCRE2 regex engine.
//! It transforms the intermediate representation (IR) into PCRE2 syntax.

use crate::core::errors::{STRlingCompilationError, STRlingWarning};
use crate::core::ir::*;
use crate::core::nodes::Flags;

/// Default upper bound on AST/IR nesting depth before the PCRE2 emitter
/// aborts. Mirrors `DEFAULT_MAX_DEPTH` in the TypeScript SSOT and the
/// matching constants in the Python and Java bindings.
pub const DEFAULT_MAX_DEPTH: usize = 250;

const REDOS_MESSAGE: &str = "The pattern contains overlapping alternations or nested unbounded quantifiers (e.g., (a+)+). This can lead to catastrophic backtracking and exponential CPU spikes. Consider using possessive quantifiers (++ or *+) or atomic groups to guarantee execution safety.";

/// Result of a successful emit pass: pattern plus any non-fatal
/// diagnostics collected during emission.
#[derive(Debug, Clone)]
pub struct EmitResult {
    pub pattern: String,
    pub warnings: Vec<STRlingWarning>,
}

/// Mutable context threaded through emission so the depth, lookbehind,
/// and warning-collection guards can fire without polluting the public
/// signature. Constructed once per emit pass; never exposed to callers.
struct EmitContext {
    depth: usize,
    max_depth: usize,
    in_lookbehind: bool,
    warnings: Vec<STRlingWarning>,
}

impl EmitContext {
    fn new(max_depth: Option<usize>) -> Self {
        Self {
            depth: 0,
            max_depth: max_depth.filter(|d| *d > 0).unwrap_or(DEFAULT_MAX_DEPTH),
            in_lookbehind: false,
            warnings: Vec::new(),
        }
    }

    /// Append `REDOS_RISK` once per pass — repeated nested-unbounded
    /// shapes inside the same pattern report a single warning so the
    /// caller is not flooded.
    fn push_redos_warning(&mut self) {
        if self.warnings.iter().any(|w| w.code == "REDOS_RISK") {
            return;
        }
        self.warnings.push(STRlingWarning::new("REDOS_RISK", REDOS_MESSAGE));
    }
}

/// True iff a quantifier has an unbounded upper bound (`*`, `+`, `{n,}`).
fn is_unbounded_quant(q: &IRQuant) -> bool {
    matches!(q.max, IRMaxBound::Infinite(_))
}

/// True iff a quantifier matches a variable number of characters.
fn is_variable_length_quant(q: &IRQuant) -> bool {
    match &q.max {
        IRMaxBound::Infinite(_) => true,
        IRMaxBound::Finite(n) => q.min != *n,
    }
}

/// Mirror of `_isFixedLengthBody` in the TS SSOT. Returns `true` when
/// `node` consumes a fixed (statically known) number of characters and
/// is therefore safe inside a PCRE2 lookbehind.
fn is_fixed_length_body(node: &IROp) -> bool {
    match node {
        IROp::Quant(q) => !is_variable_length_quant(q) && is_fixed_length_body(&q.child),
        IROp::Seq(seq) => seq.parts.iter().all(is_fixed_length_body),
        // Conservative parity with TS: every branch must be fixed-length;
        // the per-branch length-equality check is delegated to PCRE2.
        IROp::Alt(alt) => alt.branches.iter().all(is_fixed_length_body),
        IROp::Group(g) => is_fixed_length_body(&g.body),
        // Nested lookarounds are zero-width, hence safe inside a lookbehind.
        IROp::Look(_) => true,
        // Lit, Dot, CharClass, Anchor, Backref are single- or zero-width.
        _ => true,
    }
}

/// Mirror of `_hasNestedUnboundedQuant` in the TS SSOT. Detects an
/// unbounded quantifier reachable from `child` via single-child
/// wrappers (Group, single-element Seq) or any branch of an Alt.
/// Used to flag the canonical `(a+)+` ReDoS shape ONLY when the outer
/// quantifier is itself unbounded.
fn has_nested_unbounded_quant(child: &IROp) -> bool {
    match child {
        IROp::Quant(q) => is_unbounded_quant(q),
        IROp::Group(g) => has_nested_unbounded_quant(&g.body),
        IROp::Seq(seq) => {
            if seq.parts.len() == 1 {
                has_nested_unbounded_quant(&seq.parts[0])
            } else {
                false
            }
        }
        IROp::Alt(alt) => alt.branches.iter().any(has_nested_unbounded_quant),
        _ => false,
    }
}

/// PCRE2 emitter that generates PCRE2-compatible regex patterns from IR
pub struct PCRE2Emitter {
    flags: Flags,
}

impl PCRE2Emitter {
    /// Create a new PCRE2 emitter with the given flags
    pub fn new(flags: Flags) -> Self {
        Self { flags }
    }

    /// Emit PCRE2 pattern from IR.
    ///
    /// # Panics
    ///
    /// Panics with the inner [`STRlingCompilationError`] if a
    /// safety guard rejects the IR (variable-length lookbehind or AST
    /// depth exceeded). Callers that need recoverable error handling
    /// must use [`Self::emit_with_diagnostics`] instead. This shape is
    /// preserved for back-compat with the existing infallible callers in
    /// `tests/`, `examples/`, and downstream crates.
    pub fn emit(&self, ir: &IROp) -> String {
        match self.emit_with_diagnostics(ir, None) {
            Ok(result) => result.pattern,
            Err(e) => panic!("{}", e),
        }
    }

    /// Emit a PCRE2 pattern *and* return any non-fatal diagnostics.
    ///
    /// This is the recoverable entry point used by the conformance test
    /// runner and any caller that needs to surface `REDOS_RISK` (or
    /// future warnings) to the end user. Pass `Some(n)` for `max_depth`
    /// to override [`DEFAULT_MAX_DEPTH`] — primarily used by the
    /// pathological fixture to exercise the depth guard with a small AST.
    pub fn emit_with_diagnostics(
        &self,
        ir: &IROp,
        max_depth: Option<usize>,
    ) -> Result<EmitResult, STRlingCompilationError> {
        let mut ctx = EmitContext::new(max_depth);
        let body = self.emit_node(ir, &mut ctx)?;
        Ok(EmitResult {
            pattern: body,
            warnings: ctx.warnings,
        })
    }

    /// Emit a single IR node
    fn emit_node(&self, node: &IROp, ctx: &mut EmitContext) -> Result<String, STRlingCompilationError> {
        // Depth tracking surfaces the offending depth as a Signpost-pattern
        // error rather than letting the host stack overflow. Use a struct
        // guard so every return path stays balanced even on early return.
        ctx.depth += 1;
        if ctx.depth > ctx.max_depth {
            ctx.depth -= 1;
            return Err(STRlingCompilationError::new(
                format!(
                    "Maximum AST depth exceeded (limit: {}). \
 This pattern is too deeply nested and risks host stack exhaustion \
 during emission. Refactor the pattern to reduce nesting, or flatten \
 capturing groups where possible.",
                    ctx.max_depth
                ),
                "MAX_DEPTH",
            ));
        }

        let result = self.emit_node_inner(node, ctx);
        ctx.depth -= 1;
        result
    }

    fn emit_node_inner(&self, node: &IROp, ctx: &mut EmitContext) -> Result<String, STRlingCompilationError> {
        let out = match node {
            IROp::Lit(lit) => self.emit_literal(&lit.value),
            IROp::Dot(_) => ".".to_string(),
            IROp::Anchor(anchor) => match anchor.at.as_str() {
                "Start" => "^".to_string(),
                "End" => "$".to_string(),
                "WordBoundary" => "\\b".to_string(),
                "NotWordBoundary" => "\\B".to_string(),
                "AbsoluteStart" => "\\A".to_string(),
                "EndBeforeFinalNewline" => "\\Z".to_string(),
                "AbsoluteEnd" => "\\z".to_string(),
                _ => panic!("Unknown anchor type: {}", anchor.at),
            },
            IROp::Seq(seq) => {
                let mut parts = Vec::with_capacity(seq.parts.len());
                for p in &seq.parts {
                    parts.push(self.emit_node(p, ctx)?);
                }
                parts.join("")
            }
            IROp::Alt(alt) => {
                let mut branches = Vec::with_capacity(alt.branches.len());
                for b in &alt.branches {
                    branches.push(self.emit_node(b, ctx)?);
                }
                branches.join("|")
            }
            IROp::Quant(quant) => {
                // ReDoS guard: only flag when the *outer* quantifier is
                // itself unbounded (e.g. `(a+)+`). A bounded outer like
                // `(a+){0,3}` cannot produce exponential backtracking on
                // its own.
                if is_unbounded_quant(quant) && has_nested_unbounded_quant(&quant.child) {
                    ctx.push_redos_warning();
                }

                let child = self.emit_node(&quant.child, ctx)?;
                let quantifier = match (&quant.max, quant.min) {
                    (IRMaxBound::Infinite(_), 0) => "*".to_string(),
                    (IRMaxBound::Infinite(_), 1) => "+".to_string(),
                    (IRMaxBound::Finite(1), 0) => "?".to_string(),
                    (IRMaxBound::Infinite(_), min) => format!("{{{},}}", min),
                    (IRMaxBound::Finite(max), min) if min == *max => format!("{{{}}}", min),
                    (IRMaxBound::Finite(max), min) => format!("{{{},{}}}", min, max),
                };

                let mode_suffix = match quant.mode.as_str() {
                    "Lazy" => "?",
                    "Possessive" => "+",
                    _ => "",  // Greedy has no suffix
                };

                format!("{}{}{}", child, quantifier, mode_suffix)
            }
            IROp::Group(group) => {
                let body = self.emit_node(&group.body, ctx)?;
                if group.atomic {
                    format!("(?>{})", body)
                } else if let Some(name) = &group.name {
                    format!("(?<{}>{})", name, body)
                } else if !group.capturing {
                    format!("(?:{})", body)
                } else {
                    format!("({})", body)
                }
            }
            IROp::Look(look) => {
                // Variable-length lookbehind guard: PCRE2 mandates a
                // fixed-width lookbehind body. Detect the violation here
                // so the user sees a Signpost-pattern error rather than
                // an opaque PCRE2 compile failure leaking from the runtime.
                if look.dir == "Behind" && !is_fixed_length_body(&look.body) {
                    return Err(STRlingCompilationError::new(
                        "PCRE2 does not support variable-length lookbehinds. \
 The lookbehind body contains a quantifier that makes its length \
 unpredictable. Rewrite the assertion using a fixed-length range \
 (e.g. `{1,8}` instead of `+`), or restructure the pattern using a \
 Lookahead, or extract the quantified portion outside the assertion.",
                        "VLB_NOT_SUPPORTED",
                    ));
                }

                let was_in_lookbehind = ctx.in_lookbehind;
                if look.dir == "Behind" {
                    ctx.in_lookbehind = true;
                }
                let body_result = self.emit_node(&look.body, ctx);
                ctx.in_lookbehind = was_in_lookbehind;
                let body = body_result?;

                match (look.dir.as_str(), look.neg) {
                    ("Ahead", false) => format!("(?={})", body),
                    ("Ahead", true) => format!("(?!{})", body),
                    ("Behind", false) => format!("(?<={})", body),
                    ("Behind", true) => format!("(?<!{})", body),
                    _ => panic!("Unknown lookaround type"),
                }
            }
            IROp::Backref(backref) => {
                if let Some(name) = &backref.by_name {
                    format!("\\k<{}>", name)
                } else if let Some(num) = backref.by_index {
                    format!("\\{}", num)
                } else {
                    panic!("Backref must have either name or index")
                }
            }
            IROp::CharClass(cc) => {
                let mut result = String::from("[");
                if cc.negated {
                    result.push('^');
                }
                for item in &cc.items {
                    result.push_str(&self.emit_class_item(item));
                }
                result.push(']');
                result
            }
        };
        Ok(out)
    }

    /// Emit a character class item
    fn emit_class_item(&self, item: &IRClassItem) -> String {
        match item {
            IRClassItem::Char(lit) => self.escape_class_char(&lit.ch),
            IRClassItem::Range(range) => {
                format!("{}-{}", 
                    self.escape_class_char(&range.from_ch),
                    self.escape_class_char(&range.to_ch))
            }
            IRClassItem::Esc(esc) => {
                match esc.escape_type.as_str() {
                    "d" => "\\d".to_string(),
                    "D" => "\\D".to_string(),
                    "w" => "\\w".to_string(),
                    "W" => "\\W".to_string(),
                    "s" => "\\s".to_string(),
                    "S" => "\\S".to_string(),
                    "p" => format!("\\p{{{}}}", esc.property.as_ref().unwrap_or(&"".to_string())),
                    "P" => format!("\\P{{{}}}", esc.property.as_ref().unwrap_or(&"".to_string())),
                    _ => format!("\\{}", esc.escape_type),
                }
            }
        }
    }

    /// Escape a literal string for PCRE2
    fn emit_literal(&self, s: &str) -> String {
        let mut result = String::new();
        for ch in s.chars() {
            result.push_str(&self.escape_char(ch));
        }
        result
    }

    /// Escape a single character for PCRE2 pattern context
    fn escape_char(&self, ch: char) -> String {
        match ch {
            '.' | '*' | '+' | '?' | '^' | '$' | '|' | '(' | ')' | '[' | ']' | '{' | '}' | '\\' => {
                format!("\\{}", ch)
            }
            '\n' => "\\n".to_string(),
            '\r' => "\\r".to_string(),
            '\t' => "\\t".to_string(),
            '\u{000C}' => "\\f".to_string(),
            '\u{000B}' => "\\v".to_string(),
            _ => ch.to_string(),
        }
    }

    /// Escape a character for use inside a character class
    fn escape_class_char(&self, s: &str) -> String {
        let mut result = String::new();
        for ch in s.chars() {
            match ch {
                ']' | '\\' | '^' | '-' => result.push_str(&format!("\\{}", ch)),
                '\n' => result.push_str("\\n"),
                '\r' => result.push_str("\\r"),
                '\t' => result.push_str("\\t"),
                _ => result.push(ch),
            }
        }
        result
    }

    /// Get the flags string for the pattern
    pub fn get_flags_string(&self) -> String {
        let mut flags = String::new();
        if self.flags.ignore_case {
            flags.push('i');
        }
        if self.flags.multiline {
            flags.push('m');
        }
        if self.flags.dot_all {
            flags.push('s');
        }
        if self.flags.unicode {
            flags.push('u');
        }
        if self.flags.extended {
            flags.push('x');
        }
        flags
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_emit_literal() {
        let emitter = PCRE2Emitter::new(Flags::default());
        let ir = IROp::Lit(IRLit {
            value: "test".to_string(),
        });
        assert_eq!(emitter.emit(&ir), "test");
    }

    #[test]
    fn test_emit_dot() {
        let emitter = PCRE2Emitter::new(Flags::default());
        let ir = IROp::Dot(IRDot {});
        assert_eq!(emitter.emit(&ir), ".");
    }

    #[test]
    fn test_emit_anchor() {
        let emitter = PCRE2Emitter::new(Flags::default());
        let ir = IROp::Anchor(IRAnchor {
            at: "Start".to_string(),
        });
        assert_eq!(emitter.emit(&ir), "^");
    }

    #[test]
    fn test_emit_quantifier() {
        let emitter = PCRE2Emitter::new(Flags::default());
        let ir = IROp::Quant(IRQuant {
            child: Box::new(IROp::Lit(IRLit {
                value: "a".to_string(),
            })),
            min: 0,
            max: IRMaxBound::Infinite("Inf".to_string()),
            mode: "Greedy".to_string(),
        });
        assert_eq!(emitter.emit(&ir), "a*");
    }

    #[test]
    fn test_emit_group() {
        let emitter = PCRE2Emitter::new(Flags::default());
        let ir = IROp::Group(IRGroup {
            capturing: true,
            name: None,
            atomic: false,
            body: Box::new(IROp::Lit(IRLit {
                value: "test".to_string(),
            })),
        });
        assert_eq!(emitter.emit(&ir), "(test)");
    }

    #[test]
    fn test_emit_alternation() {
        let emitter = PCRE2Emitter::new(Flags::default());
        let ir = IROp::Alt(IRAlt {
            branches: vec![
                IROp::Lit(IRLit {
                    value: "a".to_string(),
                }),
                IROp::Lit(IRLit {
                    value: "b".to_string(),
                }),
            ],
        });
        assert_eq!(emitter.emit(&ir), "a|b");
    }
}
