package simply

import (
	"github.com/strling-lang/strling/bindings/go/core"
)

// =============================================================================
// Standard Library — Essential Patterns
//
// The following helpers expose canonical, RFC-grounded patterns for the most
// commonly validated string formats. Each helper composes existing Simply
// primitives so the compiled output flows through the standard pipeline and no
// raw regex leaks into the public API.
// =============================================================================

// internal helpers — character classes used by the Essential 5.

func charClassRanges(negated bool, items ...core.ClassItem) Pattern {
	return Pattern{node: core.CharClass{Negated: negated, Items: items}}
}

func letterClass() core.ClassItem {
	return core.ClassRange{FromCh: "A", ToCh: "Z"}
}

func letterClassLower() core.ClassItem {
	return core.ClassRange{FromCh: "a", ToCh: "z"}
}

func digitEsc() core.ClassItem {
	return core.ClassEscape{Type: "d"}
}

func quantPattern(p Pattern, min int, max interface{}) Pattern {
	if min == 1 && max == 1 {
		return p
	}
	return Pattern{node: core.Quant{
		Child: p.node,
		Min:   min,
		Max:   max,
		Mode:  "Greedy",
	}}
}

func letters(min int, max interface{}) Pattern {
	cc := charClassRanges(false, letterClass(), letterClassLower())
	return quantPattern(cc, min, max)
}

func digits(min int, max interface{}) Pattern {
	cc := charClassRanges(false, digitEsc())
	return quantPattern(cc, min, max)
}

func hexDigits(min int, max interface{}) Pattern {
	cc := charClassRanges(false,
		core.ClassRange{FromCh: "A", ToCh: "F"},
		core.ClassRange{FromCh: "a", ToCh: "f"},
		core.ClassRange{FromCh: "0", ToCh: "9"},
	)
	return quantPattern(cc, min, max)
}

func alt(branches ...Pattern) Pattern {
	nodes := make([]core.Node, len(branches))
	for i, b := range branches {
		nodes[i] = b.node
	}
	return Pattern{node: core.Alt{Branches: nodes}}
}

func lit(text string) Pattern {
	return Pattern{node: core.Lit{Value: text}}
}

// Email matches an email address (RFC 5322 addr-spec, basic structure).
//
// Accepts a local part of letters, digits, and the punctuation `. _ % + -`,
// followed by `@`, a domain of letters, digits, dots, and hyphens, and a
// top-level domain of two or more letters. Quoted local parts and
// internationalized (IDN) labels are intentionally out of scope.
func Email() Pattern {
	localItems := []core.ClassItem{
		letterClass(), letterClassLower(), digitEsc(),
		core.ClassLiteral{Ch: "."}, core.ClassLiteral{Ch: "_"},
		core.ClassLiteral{Ch: "%"}, core.ClassLiteral{Ch: "+"},
		core.ClassLiteral{Ch: "-"},
	}
	domainItems := []core.ClassItem{
		letterClass(), letterClassLower(), digitEsc(),
		core.ClassLiteral{Ch: "."}, core.ClassLiteral{Ch: "-"},
	}
	local := quantPattern(Pattern{node: core.CharClass{Items: localItems}}, 1, "Inf")
	domain := quantPattern(Pattern{node: core.CharClass{Items: domainItems}}, 1, "Inf")
	tld := letters(2, "Inf")
	return Merge(local, lit("@"), domain, lit("."), tld)
}

// URL matches an HTTP or HTTPS URL (RFC 3986 generic syntax).
//
// Components recognised: scheme (http/https), authority with optional port,
// optional path, optional query, and optional fragment.
func URL() Pattern {
	urlChars := func(extras ...string) []core.ClassItem {
		items := []core.ClassItem{
			letterClass(), letterClassLower(), digitEsc(),
			core.ClassLiteral{Ch: "/"}, core.ClassLiteral{Ch: "_"},
			core.ClassLiteral{Ch: "-"}, core.ClassLiteral{Ch: "."},
			core.ClassLiteral{Ch: "~"}, core.ClassLiteral{Ch: "%"},
			core.ClassLiteral{Ch: "&"}, core.ClassLiteral{Ch: "="},
			core.ClassLiteral{Ch: ":"}, core.ClassLiteral{Ch: "@"},
			core.ClassLiteral{Ch: "!"}, core.ClassLiteral{Ch: "$"},
			core.ClassLiteral{Ch: "'"}, core.ClassLiteral{Ch: "("},
			core.ClassLiteral{Ch: ")"}, core.ClassLiteral{Ch: "*"},
			core.ClassLiteral{Ch: "+"}, core.ClassLiteral{Ch: ","},
			core.ClassLiteral{Ch: ";"},
		}
		for _, e := range extras {
			items = append(items, core.ClassLiteral{Ch: e})
		}
		return items
	}
	hostItems := []core.ClassItem{
		letterClass(), letterClassLower(), digitEsc(),
		core.ClassLiteral{Ch: "."}, core.ClassLiteral{Ch: "-"},
	}
	host := quantPattern(Pattern{node: core.CharClass{Items: hostItems}}, 1, "Inf")
	port := May(Merge(lit(":"), digits(1, "Inf")))
	pathBody := quantPattern(Pattern{node: core.CharClass{Items: urlChars()}}, 0, "Inf")
	path := May(Merge(lit("/"), pathBody))
	queryBody := quantPattern(Pattern{node: core.CharClass{Items: urlChars("?")}}, 0, "Inf")
	query := May(Merge(lit("?"), queryBody))
	fragmentBody := quantPattern(Pattern{node: core.CharClass{Items: urlChars("?", "#")}}, 0, "Inf")
	fragment := May(Merge(lit("#"), fragmentBody))
	scheme := Merge(lit("http"), May(lit("s")))
	return Merge(scheme, lit("://"), host, port, path, query, fragment)
}

// UUID matches a UUID in the standard 8-4-4-4-12 hex format (RFC 4122).
//
// When `version` is 4, the pattern additionally enforces the version-4 layout:
// the third group's first hex digit is `4` and the fourth group's first hex
// digit is one of `8`, `9`, `a`, `b`. Any other version value yields the
// generic 8-4-4-4-12 pattern.
func UUID(version ...int) Pattern {
	dash := lit("-")
	if len(version) > 0 && version[0] == 4 {
		variant := Pattern{node: core.CharClass{Items: []core.ClassItem{
			core.ClassLiteral{Ch: "8"}, core.ClassLiteral{Ch: "9"},
			core.ClassLiteral{Ch: "A"}, core.ClassLiteral{Ch: "B"},
			core.ClassLiteral{Ch: "a"}, core.ClassLiteral{Ch: "b"},
		}}}
		return Merge(
			hexDigits(8, 8), dash,
			hexDigits(4, 4), dash,
			lit("4"), hexDigits(3, 3), dash,
			variant, hexDigits(3, 3), dash,
			hexDigits(12, 12),
		)
	}
	return Merge(
		hexDigits(8, 8), dash,
		hexDigits(4, 4), dash,
		hexDigits(4, 4), dash,
		hexDigits(4, 4), dash,
		hexDigits(12, 12),
	)
}

// IP matches an IPv4 (RFC 791) or full-form IPv6 (RFC 4291) address.
//
// `version=4` restricts to IPv4 dot-decimal; `version=6` restricts to the
// eight-group IPv6 colon-hex form. Omitting the argument accepts either
// family. Compressed IPv6 forms (`::`) are out of scope for this basic helper.
func IP(version ...int) Pattern {
	ipv4 := Merge(
		digits(1, 3), lit("."),
		digits(1, 3), lit("."),
		digits(1, 3), lit("."),
		digits(1, 3),
	)
	ipv6 := Merge(
		hexDigits(1, 4), lit(":"),
		hexDigits(1, 4), lit(":"),
		hexDigits(1, 4), lit(":"),
		hexDigits(1, 4), lit(":"),
		hexDigits(1, 4), lit(":"),
		hexDigits(1, 4), lit(":"),
		hexDigits(1, 4), lit(":"),
		hexDigits(1, 4),
	)
	if len(version) > 0 {
		switch version[0] {
		case 4:
			return ipv4
		case 6:
			return ipv6
		}
	}
	return alt(ipv4, ipv6)
}

// DateTime matches an ISO 8601 / RFC 3339 datetime: YYYY-MM-DDTHH:MM:SS with
// optional fractional seconds and timezone designator (`Z` or `±HH:MM`).
func DateTime() Pattern {
	tzSign := Pattern{node: core.CharClass{Items: []core.ClassItem{
		core.ClassLiteral{Ch: "+"}, core.ClassLiteral{Ch: "-"},
	}}}
	return Merge(
		digits(4, 4), lit("-"), digits(2, 2), lit("-"), digits(2, 2),
		lit("T"),
		digits(2, 2), lit(":"), digits(2, 2), lit(":"), digits(2, 2),
		May(Merge(lit("."), digits(1, "Inf"))),
		May(alt(lit("Z"), Merge(tzSign, digits(2, 2), lit(":"), digits(2, 2)))),
	)
}
