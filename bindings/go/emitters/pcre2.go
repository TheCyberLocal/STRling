// Package emitters contains code generators that transform IR to target regex flavors.
package emitters

import (
	"fmt"
	"regexp"
	"strconv"
	"strings"
	
	"github.com/thecyberlocal/strling/bindings/go/core"
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
func emitNode(node core.IROp, parentKind string) string {
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
	
	body := emitNode(irRoot, "")
	return prefix + body
}
