// Package emitters contains code generators that transform IR to target regex flavors.
package emitters

import (
	"fmt"
	"regexp"
	"strconv"
	"strings"

	"github.com/strling-lang/strling/bindings/go/core"
)

// STRling PCRE2 Emitter - IR to PCRE2 Pattern String
//
// This module implements the emitter that transforms STRling's Intermediate
// Representation (IR) into PCRE2-compatible regex pattern strings. The emitter:
//   - Converts IR operations to PCRE2 syntax
//   - Handles proper escaping of metacharacters
//   - Manages character classes and ranges
//   - Emits quantifiers, groups, and lookarounds
//   - Applies regex flags as needed
//
// The emitter is the final stage of the compilation pipeline, producing actual
// regex patterns that can be used with PCRE2-compatible regex engines (which
// includes most modern regex implementations).

// escapeLiteral escapes PCRE2 metacharacters outside character classes.
// Does NOT escape dashes (-) as they're not special outside character classes.
func escapeLiteral(s string) string {
	// Use regexp.QuoteMeta which escapes regex metacharacters
	escaped := regexp.QuoteMeta(s)
	// Remove unnecessary escaping for dashes
	escaped = strings.ReplaceAll(escaped, `\-`, "-")
	return escaped
}

// escapeClassChar escapes a character for use inside [...] per PCRE2 rules.
// Inside [], ], \, -, and ^ are special and need escaping for safety.
func escapeClassChar(ch string) string {
	if len(ch) == 0 {
		return ""
	}

	c := ch[0]

	// ] and \ ALWAYS need escaping
	if c == '\\' || c == ']' {
		return "\\" + ch
	}
	// - and ^ should be escaped to avoid ambiguity
	if c == '-' {
		return "\\-"
	}
	if c == '^' {
		return "\\^"
	}

	// Handle non-printable chars / whitespace for clarity
	switch c {
	case '\n':
		return `\n`
	case '\r':
		return `\r`
	case '\t':
		return `\t`
	case '\f':
		return `\f`
	case '\v':
		return `\v`
	}

	// Other non-printable characters
	if c < 32 || !strconv.IsPrint(rune(c)) {
		return fmt.Sprintf("\\x%02x", c)
	}

	// All other characters are literal within [] including ., *, ?, [, etc.
	return ch
}

// emitClass emits a PCRE2 character class.
// If the class is exactly one shorthand escape (like \d or \p{Lu}),
// prefer the shorthand (with negation flipping) instead of a bracketed class.
func emitClass(cc core.IRCharClass) string {
	items := cc.Items

	// Single-item shorthand optimization
	if len(items) == 1 {
		if esc, ok := items[0].(core.IRClassEscape); ok {
			k := esc.Type
			prop := esc.Property

			if k == "d" || k == "w" || k == "s" {
				// Flip to uppercase negated forms when the entire class is negated
				if cc.Negated {
					if k == "d" {
						return `\D`
					} else if k == "w" {
						return `\W`
					} else if k == "s" {
						return `\S`
					}
				}
				return "\\" + k
			}

			if k == "D" || k == "W" || k == "S" {
				// Already-negated shorthands; flip back if the class itself is negated
				base := strings.ToLower(k)
				if cc.Negated {
					return "\\" + base
				}
				return "\\" + k
			}

			if (k == "p" || k == "P") && prop != nil {
				// For \p{..}/\P{..}, flip p<->P iff exactly-negated class
				use := "p"
				if cc.Negated != (k == "P") { // XOR
					use = "P"
				}
				return fmt.Sprintf("\\%s{%s}", use, *prop)
			}
		}
	}

	// General case: build a bracket class
	var parts []string
	for _, it := range items {
		switch item := it.(type) {
		case core.IRClassLiteral:
			parts = append(parts, escapeClassChar(item.Ch))
		case core.IRClassRange:
			parts = append(parts, fmt.Sprintf("%s-%s",
				escapeClassChar(item.FromCh),
				escapeClassChar(item.ToCh)))
		case core.IRClassEscape:
			// Shorthands like \d, \p{L} are used directly
			if item.Type == "d" || item.Type == "D" || item.Type == "w" ||
				item.Type == "W" || item.Type == "s" || item.Type == "S" {
				parts = append(parts, "\\"+item.Type)
			} else if (item.Type == "p" || item.Type == "P") && item.Property != nil {
				parts = append(parts, fmt.Sprintf("\\%s{%s}", item.Type, *item.Property))
			} else {
				parts = append(parts, "\\"+item.Type)
			}
		}
	}

	inner := strings.Join(parts, "")
	negPrefix := ""
	if cc.Negated {
		negPrefix = "^"
	}
	return fmt.Sprintf("[%s%s]", negPrefix, inner)
}

// emitQuantSuffix emits *, +, ?, {m}, {m,}, {m,n} plus optional lazy/possessive suffix.
func emitQuantSuffix(minV interface{}, maxV interface{}, mode string) string {
	var q string

	min, _ := minV.(int)

	// Check if max is "Inf" (string) or an int
	maxIsInf := false
	maxInt := 0
	if maxStr, ok := maxV.(string); ok && maxStr == "Inf" {
		maxIsInf = true
	} else if maxI, ok := maxV.(int); ok {
		maxInt = maxI
	}

	if min == 0 && maxIsInf {
		q = "*"
	} else if min == 1 && maxIsInf {
		q = "+"
	} else if min == 0 && maxInt == 1 {
		q = "?"
	} else if !maxIsInf && min == maxInt {
		q = fmt.Sprintf("{%d}", min)
	} else if maxIsInf {
		q = fmt.Sprintf("{%d,}", min)
	} else {
		q = fmt.Sprintf("{%d,%d}", min, maxInt)
	}

	if mode == "Lazy" {
		q += "?"
	} else if mode == "Possessive" {
		q += "+"
	}

	return q
}

// needsGroupForQuant returns true if 'child' needs a non-capturing group when quantifying.
// Literals of length > 1, Seq, Alt, and Look typically require grouping.
func needsGroupForQuant(child core.IROp) bool {
	switch c := child.(type) {
	case core.IRCharClass, core.IRDot, core.IRGroup, core.IRBackref, core.IRAnchor:
		return false
	case core.IRLit:
		return len(c.Value) > 1
	case core.IRAlt, core.IRLook:
		return true
	case core.IRSeq:
		return len(c.Parts) > 1
	}
	return false
}

// emitGroupOpen emits the opening syntax for a group.
func emitGroupOpen(g core.IRGroup) string {
	if g.Atomic != nil && *g.Atomic {
		return "(?>"
	}
	if g.Capturing {
		if g.Name != nil {
			return fmt.Sprintf("(?<%s>", *g.Name)
		}
		return "("
	}
	return "(?:"
}

// emitNode emits PCRE2 pattern string from an IR node.
//
// Deprecated wrapper used by the Emit fast path; new call sites should
// use emitNodeCtx so the depth, lookbehind and warning-collection
// guards activate.
func emitNode(node core.IROp, parentKind string) string {
	ctx := newEmitContext(0)
	return emitNodeCtx(node, parentKind, ctx)
}

// DEFAULT_MAX_DEPTH bounds AST/IR nesting depth before the emitter
// aborts. Mirrors the SSOT in the TypeScript reference and the
// matching constants in every other binding.
const DEFAULT_MAX_DEPTH = 250

const redosMessage = "The pattern contains overlapping alternations or nested unbounded quantifiers (e.g., (a+)+). This can lead to catastrophic backtracking and exponential CPU spikes. Consider using possessive quantifiers (++ or *+) or atomic groups to guarantee execution safety."

// emitContext is the mutable per-emit state threaded through emitNodeCtx
// so the depth, lookbehind, and warning-collection guards can fire
// without polluting the public API.
type emitContext struct {
	depth        int
	maxDepth     int
	inLookbehind bool
	warnings     []core.STRlingWarning
}

func newEmitContext(maxDepth int) *emitContext {
	if maxDepth <= 0 {
		maxDepth = DEFAULT_MAX_DEPTH
	}
	return &emitContext{maxDepth: maxDepth}
}

// isUnboundedQuant reports whether a quantifier has an unbounded upper bound.
func isUnboundedQuant(q core.IRQuant) bool {
	if s, ok := q.Max.(string); ok {
		return s == "Inf"
	}
	return false
}

// isVariableLengthQuant reports whether a quantifier matches a variable
// number of characters.
func isVariableLengthQuant(q core.IRQuant) bool {
	if isUnboundedQuant(q) {
		return true
	}
	if maxI, ok := q.Max.(int); ok {
		return maxI != q.Min
	}
	// Unknown shape — be conservative.
	return true
}

// isFixedLengthBody mirrors `_isFixedLengthBody` in the TS SSOT. Returns
// true when `node` consumes a fixed number of characters and is
// therefore safe inside a PCRE2 lookbehind.
func isFixedLengthBody(node core.IROp) bool {
	switch n := node.(type) {
	case core.IRQuant:
		return !isVariableLengthQuant(n) && isFixedLengthBody(n.Child)
	case core.IRSeq:
		for _, p := range n.Parts {
			if !isFixedLengthBody(p) {
				return false
			}
		}
		return true
	case core.IRAlt:
		for _, b := range n.Branches {
			if !isFixedLengthBody(b) {
				return false
			}
		}
		return true
	case core.IRGroup:
		return isFixedLengthBody(n.Body)
	case core.IRLook:
		// Nested lookarounds are zero-width.
		return true
	}
	return true
}

// hasNestedUnboundedQuant mirrors `_hasNestedUnboundedQuant` in the TS
// SSOT. Detects an unbounded quantifier reachable via single-child
// wrappers or any branch of an Alt.
func hasNestedUnboundedQuant(child core.IROp) bool {
	switch n := child.(type) {
	case core.IRQuant:
		return isUnboundedQuant(n)
	case core.IRGroup:
		return hasNestedUnboundedQuant(n.Body)
	case core.IRSeq:
		return len(n.Parts) == 1 && hasNestedUnboundedQuant(n.Parts[0])
	case core.IRAlt:
		for _, b := range n.Branches {
			if hasNestedUnboundedQuant(b) {
				return true
			}
		}
		return false
	}
	return false
}

// pushReDoSWarning appends a single REDOS_RISK warning, deduplicated per pass.
func pushReDoSWarning(ctx *emitContext) {
	for _, w := range ctx.warnings {
		if w.Code == "REDOS_RISK" {
			return
		}
	}
	ctx.warnings = append(ctx.warnings, core.STRlingWarning{Code: "REDOS_RISK", Message: redosMessage})
}

// emitNodeCtx is the depth-tracking, guard-aware emitter core. Panics
// with a *core.STRlingCompilationError on guard violations; the public
// EmitWithDiagnostics entry point recovers and returns it as an error.
func emitNodeCtx(node core.IROp, parentKind string, ctx *emitContext) string {
	ctx.depth++
	defer func() { ctx.depth-- }()
	if ctx.depth > ctx.maxDepth {
		panic(core.NewSTRlingCompilationError(
			fmt.Sprintf("Maximum AST depth exceeded (limit: %d). This pattern is too deeply nested and risks host stack exhaustion during emission. Refactor the pattern to reduce nesting, or flatten capturing groups where possible.", ctx.maxDepth),
			"MAX_DEPTH", ""))
	}
	switch n := node.(type) {
	case core.IRLit:
		return escapeLiteral(n.Value)

	case core.IRDot:
		return "."

	case core.IRAnchor:
		mapping := map[string]string{
			"Start":                 "^",
			"End":                   "$",
			"WordBoundary":          `\b`,
			"NotWordBoundary":       `\B`,
			"AbsoluteStart":         `\A`,
			"EndBeforeFinalNewline": `\Z`,
			"AbsoluteEnd":           `\z`,
		}
		if val, ok := mapping[n.At]; ok {
			return val
		}
		return ""

	case core.IRBackref:
		if n.ByName != nil {
			return fmt.Sprintf(`\k<%s>`, *n.ByName)
		}
		if n.ByIndex != nil {
			return fmt.Sprintf(`\%d`, *n.ByIndex)
		}
		return ""

	case core.IRCharClass:
		return emitClass(n)

	case core.IRSeq:
		var parts []string
		for _, p := range n.Parts {
			parts = append(parts, emitNodeCtx(p, "Seq", ctx))
		}
		return strings.Join(parts, "")

	case core.IRAlt:
		var branches []string
		for _, b := range n.Branches {
			branches = append(branches, emitNodeCtx(b, "Alt", ctx))
		}
		body := strings.Join(branches, "|")
		if parentKind == "Seq" || parentKind == "Quant" {
			return "(?:" + body + ")"
		}
		return body

	case core.IRQuant:
		// ReDoS guard: only flag when the *outer* quantifier is itself
		// unbounded (e.g. `(a+)+`). A bounded outer like `(a+){0,3}`
		// cannot produce exponential backtracking on its own.
		if isUnboundedQuant(n) && hasNestedUnboundedQuant(n.Child) {
			pushReDoSWarning(ctx)
		}
		childStr := emitNodeCtx(n.Child, "Quant", ctx)
		if needsGroupForQuant(n.Child) {
			if _, ok := n.Child.(core.IRGroup); !ok {
				childStr = "(?:" + childStr + ")"
			}
		}
		return childStr + emitQuantSuffix(n.Min, n.Max, n.Mode)

	case core.IRGroup:
		return emitGroupOpen(n) + emitNodeCtx(n.Body, "Group", ctx) + ")"

	case core.IRLook:
		// Variable-length lookbehind guard: PCRE2 mandates a fixed-width
		// lookbehind body. Detect the violation here so the user sees a
		// Signpost-pattern error rather than an opaque PCRE2 compile
		// failure leaking from the runtime.
		if n.Dir == "Behind" && !isFixedLengthBody(n.Body) {
			panic(core.NewSTRlingCompilationError(
				"PCRE2 does not support variable-length lookbehinds. The lookbehind body contains a quantifier that makes its length unpredictable. Rewrite the assertion using a fixed-length range (e.g. `{1,8}` instead of `+`), or restructure the pattern using a Lookahead, or extract the quantified portion outside the assertion.",
				"VLB_NOT_SUPPORTED", ""))
		}
		wasInLb := ctx.inLookbehind
		if n.Dir == "Behind" {
			ctx.inLookbehind = true
		}
		defer func() { ctx.inLookbehind = wasInLb }()
		var op string
		if n.Dir == "Ahead" && !n.Neg {
			op = "?="
		} else if n.Dir == "Ahead" && n.Neg {
			op = "?!"
		} else if n.Dir == "Behind" && !n.Neg {
			op = "?<="
		} else {
			op = "?<!"
		}
		return "(" + op + emitNodeCtx(n.Body, "Look", ctx) + ")"
	}

	return ""
}

// emitNodeLegacy is the original guard-free implementation. Retained
// only as a reference; not used by the public API.
func emitNodeLegacy(node core.IROp, parentKind string) string {
	switch n := node.(type) {
	case core.IRLit:
		return escapeLiteral(n.Value)

	case core.IRDot:
		return "."

	case core.IRAnchor:
		mapping := map[string]string{
			"Start":                   "^",
			"End":                     "$",
			"WordBoundary":            `\b`,
			"NotWordBoundary":         `\B`,
			"AbsoluteStart":           `\A`,
			"EndBeforeFinalNewline":   `\Z`,
			"AbsoluteEnd":             `\z`,
		}
		if val, ok := mapping[n.At]; ok {
			return val
		}
		return ""

	case core.IRBackref:
		if n.ByName != nil {
			return fmt.Sprintf(`\k<%s>`, *n.ByName)
		}
		if n.ByIndex != nil {
			return fmt.Sprintf(`\%d`, *n.ByIndex)
		}
		return ""

	case core.IRCharClass:
		return emitClass(n)

	case core.IRSeq:
		var parts []string
		for _, p := range n.Parts {
			parts = append(parts, emitNode(p, "Seq"))
		}
		return strings.Join(parts, "")

	case core.IRAlt:
		var branches []string
		for _, b := range n.Branches {
			branches = append(branches, emitNode(b, "Alt"))
		}
		body := strings.Join(branches, "|")
		// Alt inside sequence/quant should be grouped
		if parentKind == "Seq" || parentKind == "Quant" {
			return "(?:" + body + ")"
		}
		return body

	case core.IRQuant:
		childStr := emitNode(n.Child, "Quant")
		if needsGroupForQuant(n.Child) {
			if _, ok := n.Child.(core.IRGroup); !ok {
				childStr = "(?:" + childStr + ")"
			}
		}
		return childStr + emitQuantSuffix(n.Min, n.Max, n.Mode)

	case core.IRGroup:
		return emitGroupOpen(n) + emitNode(n.Body, "Group") + ")"

	case core.IRLook:
		var op string
		if n.Dir == "Ahead" && !n.Neg {
			op = "?="
		} else if n.Dir == "Ahead" && n.Neg {
			op = "?!"
		} else if n.Dir == "Behind" && !n.Neg {
			op = "?<="
		} else {
			op = "?<!"
		}
		return "(" + op + emitNode(n.Body, "Look") + ")"
	}

	return ""
}

// emitPrefixFromFlags builds the inline prefix form expected by tests, e.g. "(?imx)".
func emitPrefixFromFlags(flags map[string]bool) string {
	letters := ""
	if flags["ignoreCase"] {
		letters += "i"
	}
	if flags["multiline"] {
		letters += "m"
	}
	if flags["dotAll"] {
		letters += "s"
	}
	if flags["unicode"] {
		letters += "u"
	}
	if flags["extended"] {
		letters += "x"
	}
	if letters != "" {
		return "(?" + letters + ")"
	}
	return ""
}

// Emit emits a PCRE2 pattern string from IR.
//
// If 'flags' is provided (as a Flags struct or map), it will be prefixed to the pattern.
func Emit(irRoot core.IROp, flags interface{}) string {
	res, err := EmitWithDiagnostics(irRoot, flags, 0)
	if err != nil {
		// Preserve panic-on-fatal semantics for legacy callers that do
		// not consume the structured result.
		panic(err)
	}
	return res.Pattern
}

// EmitWithDiagnostics emits a PCRE2 pattern string from IR and surfaces
// any non-fatal diagnostics (e.g. REDOS_RISK warnings) collected during
// emission. Pass maxDepth <= 0 to use DEFAULT_MAX_DEPTH.
func EmitWithDiagnostics(irRoot core.IROp, flags interface{}, maxDepth int) (result *core.CompileResult, err error) {
	var flagDict map[string]bool
	if flags != nil {
		switch f := flags.(type) {
		case map[string]bool:
			flagDict = f
		case core.Flags:
			flagDict = f.ToDict()
		}
	}
	prefix := ""
	if flagDict != nil {
		prefix = emitPrefixFromFlags(flagDict)
	}

	ctx := newEmitContext(maxDepth)
	defer func() {
		if r := recover(); r != nil {
			if ce, ok := r.(*core.STRlingCompilationError); ok {
				result = nil
				err = ce
				return
			}
			panic(r)
		}
	}()
	body := emitNodeCtx(irRoot, "", ctx)
	return &core.CompileResult{Pattern: prefix + body, Warnings: ctx.warnings}, nil
}
