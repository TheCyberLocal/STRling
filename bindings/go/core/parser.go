// Package core contains the fundamental components of the STRling compiler.
//
// STRling Parser - Recursive Descent Parser for STRling DSL
//
// This module implements a hand-rolled recursive-descent parser that transforms
// STRling pattern syntax into Abstract Syntax Tree (AST) nodes. The parser handles:
//   - Alternation and sequencing
//   - Character classes and ranges
//   - Quantifiers (greedy, lazy, possessive)
//   - Groups (capturing, non-capturing, named, atomic)
//   - Lookarounds (lookahead and lookbehind, positive and negative)
//   - Anchors and special escapes
//   - Extended/free-spacing mode with comments
//
// The parser produces AST nodes (defined in nodes.go) that can be compiled
// to IR and ultimately emitted as target-specific regex patterns. It includes
// comprehensive error handling with position tracking for helpful diagnostics.
package core

import (
	"fmt"
	"regexp"
	"strings"
)

// ParseError is an alias for STRlingParseError for backward compatibility.
type ParseError = STRlingParseError

// Cursor represents the parser's position in the input text.
// It tracks the current position, extended mode status, and character class nesting.
type Cursor struct {
	text         string
	i            int
	extendedMode bool
	inClass      int // nesting count for char classes
}

// eof returns true if the cursor is at the end of the input.
func (c *Cursor) eof() bool {
	return c.i >= len(c.text)
}

// peek returns the character at offset n from the current position.
// Returns empty string if out of bounds.
func (c *Cursor) peek(n int) string {
	j := c.i + n
	if j >= len(c.text) {
		return ""
	}
	return string(c.text[j])
}

// take consumes and returns the next character, advancing the cursor.
// Returns empty string if at EOF.
func (c *Cursor) take() string {
	if c.eof() {
		return ""
	}
	ch := string(c.text[c.i])
	c.i++
	return ch
}

// match attempts to match a string at the current position.
// If successful, advances the cursor and returns true.
func (c *Cursor) match(s string) bool {
	if strings.HasPrefix(c.text[c.i:], s) {
		c.i += len(s)
		return true
	}
	return false
}

// skipWsAndComments skips whitespace and comments in extended mode.
// In free-spacing mode, ignores spaces/tabs/newlines and #-to-EOL comments.
func (c *Cursor) skipWsAndComments() {
	if !c.extendedMode || c.inClass > 0 {
		return
	}
	for !c.eof() {
		ch := c.peek(0)
		if ch == " " || ch == "\t" || ch == "\r" || ch == "\n" {
			c.i++
			continue
		}
		if ch == "#" {
			// skip comment to end of line
			for !c.eof() && c.peek(0) != "\r" && c.peek(0) != "\n" {
				c.i++
			}
			continue
		}
		break
	}
}

// Parser is the STRling parser that converts DSL syntax to AST.
type Parser struct {
	originalText string
	flags        Flags
	src          string
	cur          *Cursor
	capCount     int
	capNames     map[string]bool
	controlEscapes map[string]string
}

// NewParser creates a new Parser for the given input text.
func NewParser(text string) *Parser {
	p := &Parser{
		originalText: text,
		capNames:     make(map[string]bool),
		controlEscapes: map[string]string{
			"n": "\n",
			"r": "\r",
			"t": "\t",
			"f": "\f",
			"v": "\v",
		},
	}
	flags, src := p.parseDirectives(text)
	p.flags = flags
	p.src = src
	p.cur = &Cursor{
		text:         src,
		i:            0,
		extendedMode: flags.Extended,
		inClass:      0,
	}
	return p
}

// raiseError raises a STRlingParseError with an instructional hint.
func (p *Parser) raiseError(message string, pos int) error {
	hint := GetHintOrFallback(message, p.src, pos)
	return &STRlingParseError{
		Message: message,
		Pos:     pos,
		Text:    p.src,
		Hint:    hint,
	}
}

// parseDirectives extracts flags and pattern from the input text.
func (p *Parser) parseDirectives(text string) (Flags, string) {
	flags := Flags{}
	lines := strings.Split(text, "\n")
	var patternLines []string
	inPattern := false

	for lineNum, line := range lines {
		stripped := strings.TrimSpace(line)

		// Skip leading blank lines or comments
		if !inPattern && (stripped == "" || strings.HasPrefix(stripped, "#")) {
			continue
		}

		// Process directives (lines starting with %)
		if strings.HasPrefix(stripped, "%") {
			if inPattern {
				hint := GetHint("Directive after pattern", p.originalText, 0)
				panic(&STRlingParseError{
					Message: "Directive after pattern",
					Pos:     0,
					Text:    p.originalText,
					Hint:    hint,
				})
			}
			if !strings.HasPrefix(stripped, "%flags") {
				hint := GetHint("Malformed directive", p.originalText, 0)
				panic(&STRlingParseError{
					Message: "Malformed directive",
					Pos:     0,
					Text:    p.originalText,
					Hint:    hint,
				})
			}
			// It's %flags - process it
			idx := strings.Index(line, "%flags")
			after := line[idx+len("%flags"):]

			// Scan the remainder to separate flags from pattern
			allowed := " ,\t[]imsuxIMSUX"
			j := 0
			for j < len(after) && strings.ContainsRune(allowed, rune(after[j])) {
				j++
			}
			flagsToken := after[:j]
			remainder := after[j:]

			// Normalize and extract flag letters
			re := regexp.MustCompile(`[,\[\]\s]+`)
			letters := strings.ToLower(strings.TrimSpace(re.ReplaceAllString(flagsToken, " ")))
			validFlags := "imsux"

			if strings.ReplaceAll(letters, " ", "") == "" {
				if strings.TrimSpace(remainder) != "" {
					ch := strings.TrimLeft(remainder, " \t")[0:1]
					// Calculate position for error
					pos := 0
					for i := 0; i < lineNum; i++ {
						pos += len(lines[i]) + 1 // +1 for newline
					}
					pos += idx + j
					hint := GetHint(fmt.Sprintf("Invalid flag '%s'", ch), p.originalText, pos)
					panic(&STRlingParseError{
						Message: fmt.Sprintf("Invalid flag '%s'", ch),
						Pos:     pos,
						Text:    p.originalText,
						Hint:    hint,
					})
				}
			} else {
				// Validate flags
				for _, ch := range strings.ReplaceAll(letters, " ", "") {
					if ch != 0 && !strings.ContainsRune(validFlags, ch) {
						pos := 0
						for i := 0; i < lineNum; i++ {
							pos += len(lines[i]) + 1
						}
						pos += idx
						hint := GetHint(fmt.Sprintf("Invalid flag '%c'", ch), p.originalText, pos)
						panic(&STRlingParseError{
							Message: fmt.Sprintf("Invalid flag '%c'", ch),
							Pos:     pos,
							Text:    p.originalText,
							Hint:    hint,
						})
					}
				}
				flags = FromLetters(letters)
			}

			if strings.TrimSpace(remainder) != "" {
				patternLines = append(patternLines, remainder)
				inPattern = true
			}
		} else {
			// Check for mid-line directive
			if strings.Contains(stripped, "%flags") {
				hint := GetHint("Directive after pattern", p.originalText, 0)
				panic(&STRlingParseError{
					Message: "Directive after pattern",
					Pos:     0,
					Text:    p.originalText,
					Hint:    hint,
				})
			}
			patternLines = append(patternLines, line)
			inPattern = true
		}
	}

	src := strings.Join(patternLines, "\n")
	return flags, src
}

// Parse parses the STRling pattern and returns flags and AST.
func Parse(text string) (flags Flags, node Node, retErr error) {
	defer func() {
		if r := recover(); r != nil {
			if err, ok := r.(*STRlingParseError); ok {
				retErr = err
				return
			}
			panic(r)
		}
	}()

	p := NewParser(text)
	ast, err := p.parseAlt()
	if err != nil {
		return Flags{}, nil, err
	}

	if !p.cur.eof() {
		ch := p.cur.peek(0)
		if ch == ")" {
			return Flags{}, nil, p.raiseError("Unmatched ')'", p.cur.i)
		}
		return Flags{}, nil, p.raiseError("Unexpected trailing input", p.cur.i)
	}

	return p.flags, ast, nil
}

// parseAlt parses alternation (a|b|c).
func (p *Parser) parseAlt() (Node, error) {
	p.cur.skipWsAndComments()

	// Check for stray leading pipe
	if p.cur.peek(0) == "|" {
		return nil, p.raiseError("Alternation lacks left-hand side", p.cur.i)
	}

	branches := []Node{}
	first, err := p.parseSeq()
	if err != nil {
		return nil, err
	}
	branches = append(branches, first)

	for {
		p.cur.skipWsAndComments()
		if p.cur.peek(0) != "|" {
			break
		}
		pipePos := p.cur.i
		p.cur.take() // consume |
		p.cur.skipWsAndComments()

		// Empty alternation (||)
		if p.cur.peek(0) == "|" {
			return nil, p.raiseError("Empty alternation", pipePos)
		}
		// Trailing pipe
		if p.cur.eof() || p.cur.peek(0) == ")" {
			return nil, p.raiseError("Alternation lacks right-hand side", pipePos)
		}

		branch, err := p.parseSeq()
		if err != nil {
			return nil, err
		}
		branches = append(branches, branch)
	}

	if len(branches) == 1 {
		return branches[0], nil
	}
	return Alt{Branches: branches}, nil
}

// parseSeq parses a sequence of pattern elements.
func (p *Parser) parseSeq() (Node, error) {
	parts := []Node{}

	for {
		p.cur.skipWsAndComments()
		if p.cur.eof() {
			break
		}

		// Check for sequence terminators
		ch := p.cur.peek(0)
		if ch == "|" || ch == ")" {
			break
		}

		atom, err := p.parseAtom()
		if err != nil {
			return nil, err
		}

		// Check for quantifier
		quant, err := p.parseQuantifier(atom)
		if err != nil {
			return nil, err
		}

		parts = append(parts, quant)
	}

	if len(parts) == 0 {
		return Seq{Parts: parts}, nil
	}
	if len(parts) == 1 {
		return parts[0], nil
	}
	return Seq{Parts: parts}, nil
}

// parseAtom parses a single pattern element.
func (p *Parser) parseAtom() (Node, error) {
	p.cur.skipWsAndComments()

	if p.cur.eof() {
		return nil, p.raiseError("Unexpected end of pattern", p.cur.i)
	}

	ch := p.cur.peek(0)

	// Anchors
	if ch == "^" {
		p.cur.take()
		return Anchor{At: "Start"}, nil
	}
	if ch == "$" {
		p.cur.take()
		return Anchor{At: "End"}, nil
	}

	// Dot
	if ch == "." {
		p.cur.take()
		return Dot{}, nil
	}

	// Character class
	if ch == "[" {
		return p.parseCharClass()
	}

	// Group or lookaround
	if ch == "(" {
		return p.parseGroup()
	}

	// Backslash escapes
	if ch == "\\" {
		return p.parseEscape()
	}

	// Literal character
	return p.parseLiteral()
}

// parseEscape parses escape sequences.
func (p *Parser) parseEscape() (Node, error) {
	if !p.cur.match("\\") {
		return nil, p.raiseError("Expected backslash", p.cur.i)
	}

	if p.cur.eof() {
		return nil, p.raiseError("Unexpected end of pattern after backslash", p.cur.i-1)
	}

	ch := p.cur.take()

	// Word boundary anchors
	if ch == "b" {
		return Anchor{At: "WordBoundary"}, nil
	}
	if ch == "B" {
		return Anchor{At: "NotWordBoundary"}, nil
	}

	// Absolute anchors
	if ch == "A" {
		return Anchor{At: "AbsoluteStart"}, nil
	}
	if ch == "Z" {
		return Anchor{At: "EndBeforeFinalNewline"}, nil
	}

	// NOTE: lowercase '\z' is intentionally NOT treated as an anchor

	// Digit escapes
	if ch == "d" {
		return CharClass{
			Negated: false,
			Items:   []ClassItem{ClassEscape{Type: "d", Property: nil}},
		}, nil
	}
	if ch == "D" {
		return CharClass{
			Negated: false,
			Items:   []ClassItem{ClassEscape{Type: "D", Property: nil}},
		}, nil
	}

	// Word escapes
	if ch == "w" {
		return CharClass{
			Negated: false,
			Items:   []ClassItem{ClassEscape{Type: "w", Property: nil}},
		}, nil
	}
	if ch == "W" {
		return CharClass{
			Negated: false,
			Items:   []ClassItem{ClassEscape{Type: "W", Property: nil}},
		}, nil
	}

	// Space escapes
	if ch == "s" {
		return CharClass{
			Negated: false,
			Items:   []ClassItem{ClassEscape{Type: "s", Property: nil}},
		}, nil
	}
	if ch == "S" {
		return CharClass{
			Negated: false,
			Items:   []ClassItem{ClassEscape{Type: "S", Property: nil}},
		}, nil
	}

	// Backreference (numeric)
	if ch >= "1" && ch <= "9" {
		startPos := p.cur.i - 2
		num := int(ch[0] - '0')
		// Continue reading digits
		for !p.cur.eof() && p.cur.peek(0) >= "0" && p.cur.peek(0) <= "9" {
			ch = p.cur.take()
			num = num*10 + int(ch[0]-'0')
		}
		if num > p.capCount {
			return nil, p.raiseError(fmt.Sprintf("Backreference to undefined group \\%d", num), startPos)
		}
		return Backref{ByIndex: &num, ByName: nil}, nil
	}

	// Named backreference
	if ch == "k" {
		startPos := p.cur.i - 2
		if p.cur.peek(0) != "<" {
			return nil, p.raiseError("Expected '<' after \\k", p.cur.i)
		}
		p.cur.take() // consume <

		name := ""
		for !p.cur.eof() && p.cur.peek(0) != ">" {
			name += p.cur.take()
		}

		if p.cur.eof() {
			return nil, p.raiseError("Unterminated named backref", p.cur.i)
		}
		p.cur.take() // consume >

		if !p.capNames[name] {
			return nil, p.raiseError(fmt.Sprintf("Backreference to undefined group <%s>", name), startPos)
		}
		return Backref{ByIndex: nil, ByName: &name}, nil
	}

	// Control escapes
	if val, ok := p.controlEscapes[ch]; ok {
		return Lit{Value: val}, nil
	}

	// Null byte
	if ch == "0" {
		return Lit{Value: "\x00"}, nil
	}

	// Forbidden octal escape
	if ch >= "0" && ch <= "9" {
		return nil, p.raiseError(fmt.Sprintf("Forbidden octal escape \\%s", ch), p.cur.i-2)
	}

	// Hex escape
	if ch == "x" {
		startPos := p.cur.i - 2
		return p.parseHexEscape(startPos)
	}

	// Unicode escape
	if ch == "u" || ch == "U" {
		startPos := p.cur.i - 2
		return p.parseUnicodeEscape(ch, startPos)
	}

	// Unicode property
	if ch == "p" || ch == "P" {
		startPos := p.cur.i - 2
		if p.cur.peek(0) != "{" {
			return nil, p.raiseError("Expected { after \\p/\\P", startPos)
		}
		p.cur.take() // consume {
		prop := ""
		for !p.cur.eof() && p.cur.peek(0) != "}" {
			prop += p.cur.take()
		}
		if p.cur.eof() {
			return nil, p.raiseError("Unterminated \\p{...}", startPos)
		}
		p.cur.take() // consume }
		escType := "p"
		if ch == "P" {
			escType = "P"
		}
		propStr := prop
		return CharClass{
			Negated: false,
			Items:   []ClassItem{ClassEscape{Type: escType, Property: &propStr}},
		}, nil
	}

	// Unknown escape for alphanumeric
	if (ch >= "a" && ch <= "z") || (ch >= "A" && ch <= "Z") {
		return nil, p.raiseError(fmt.Sprintf("Unknown escape sequence \\%s", ch), p.cur.i-2)
	}

	// Identity escape (punctuation)
	return Lit{Value: ch}, nil
}

// parseLiteral parses a literal character.
func (p *Parser) parseLiteral() (Node, error) {
	// Check for special chars that should not be treated as literals
	ch := p.cur.peek(0)
	quantifiers := "*+?{"
	if strings.ContainsRune(quantifiers, rune(ch[0])) {
		return nil, p.raiseError(fmt.Sprintf("Invalid quantifier '%s'", ch), p.cur.i)
	}
	special := "|()]"
	if strings.ContainsRune(special, rune(ch[0])) {
		return nil, p.raiseError(fmt.Sprintf("Unexpected token '%s'", ch), p.cur.i)
	}

	val := p.cur.take()
	return Lit{Value: val}, nil
}

// parseCharClass parses a character class [abc].
func (p *Parser) parseCharClass() (Node, error) {
	if !p.cur.match("[") {
		return nil, p.raiseError("Expected '['", p.cur.i)
	}

	p.cur.inClass++
	defer func() { p.cur.inClass-- }()

	negated := false
	if p.cur.peek(0) == "^" {
		negated = true
		p.cur.take()
	}

	// Empty character class
	if p.cur.peek(0) == "]" {
		return nil, p.raiseError("Unterminated character class", p.cur.i)
	}

	items := []ClassItem{}

	for !p.cur.eof() && p.cur.peek(0) != "]" {
		item, err := p.parseClassItem()
		if err != nil {
			return nil, err
		}
		items = append(items, item)
	}

	if p.cur.eof() {
		return nil, p.raiseError("Unterminated character class", p.cur.i)
	}

	p.cur.take() // consume ]

	return CharClass{Negated: negated, Items: items}, nil
}

// parseClassItem parses a single item within a character class.
func (p *Parser) parseClassItem() (ClassItem, error) {
	// Handle escape sequences
	if p.cur.peek(0) == "\\" {
		p.cur.take()
		if p.cur.eof() {
			return nil, p.raiseError("Unexpected end in character class", p.cur.i-1)
		}

		ch := p.cur.take()

		// Shorthand classes
		if ch == "d" || ch == "D" || ch == "w" || ch == "W" || ch == "s" || ch == "S" {
			return ClassEscape{Type: ch, Property: nil}, nil
		}

		// Control escapes
		if val, ok := p.controlEscapes[ch]; ok {
			return ClassLiteral{Ch: val}, nil
		}

		// Backspace in class
		if ch == "b" {
			return ClassLiteral{Ch: "\x08"}, nil
		}

		// Null byte
		if ch == "0" {
			return ClassLiteral{Ch: "\x00"}, nil
		}

		// Unicode property in class
		if ch == "p" || ch == "P" {
			startPos := p.cur.i - 2
			if p.cur.peek(0) != "{" {
				return nil, p.raiseError("Expected { after \\p/\\P", startPos)
			}
			p.cur.take() // consume {
			prop := ""
			for !p.cur.eof() && p.cur.peek(0) != "}" {
				prop += p.cur.take()
			}
			if p.cur.eof() {
				return nil, p.raiseError("Unterminated \\p{...}", startPos)
			}
			p.cur.take() // consume }
			return ClassEscape{Type: ch, Property: &prop}, nil
		}

		// Unknown escape for alphanumeric
		if (ch >= "a" && ch <= "z") || (ch >= "A" && ch <= "Z") {
			return nil, p.raiseError(fmt.Sprintf("Unknown escape sequence \\%s", ch), p.cur.i-2)
		}

		// Identity escape (punctuation)
		return ClassLiteral{Ch: ch}, nil
	}

	// Check for range
	ch := p.cur.take()
	if p.cur.peek(0) == "-" && p.cur.peek(1) != "]" {
		p.cur.take() // consume -
		toCh := p.cur.take()
		if toCh < ch {
			return nil, p.raiseError("Invalid character range", p.cur.i)
		}
		return ClassRange{FromCh: ch, ToCh: toCh}, nil
	}

	return ClassLiteral{Ch: ch}, nil
}

// parseGroup parses groups and lookarounds.
func (p *Parser) parseGroup() (Node, error) {
	if !p.cur.match("(") {
		return nil, p.raiseError("Expected '('", p.cur.i)
	}

	// Check for special group types
	if p.cur.peek(0) == "?" {
		p.cur.take()

		// Non-capturing group
		if p.cur.match(":") {
			body, err := p.parseAlt()
			if err != nil {
				return nil, err
			}
			if !p.cur.match(")") {
				return nil, p.raiseError("Unterminated group", p.cur.i)
			}
			return Group{Capturing: false, Body: body, Name: nil, Atomic: nil}, nil
		}

		// Lookahead
		if p.cur.match("=") {
			body, err := p.parseAlt()
			if err != nil {
				return nil, err
			}
			if !p.cur.match(")") {
				return nil, p.raiseError("Unterminated lookahead", p.cur.i)
			}
			return Look{Dir: "Ahead", Neg: false, Body: body}, nil
		}

		// Negative lookahead
		if p.cur.match("!") {
			body, err := p.parseAlt()
			if err != nil {
				return nil, err
			}
			if !p.cur.match(")") {
				return nil, p.raiseError("Unterminated lookahead", p.cur.i)
			}
			return Look{Dir: "Ahead", Neg: true, Body: body}, nil
		}

		// Lookbehind and named groups (both start with <)
		if p.cur.match("<") {
			// Check for lookbehind assertions
			if p.cur.match("=") {
				body, err := p.parseAlt()
				if err != nil {
					return nil, err
				}
				if !p.cur.match(")") {
					return nil, p.raiseError("Unterminated lookbehind", p.cur.i)
				}
				return Look{Dir: "Behind", Neg: false, Body: body}, nil
			}
			if p.cur.match("!") {
				body, err := p.parseAlt()
				if err != nil {
					return nil, err
				}
				if !p.cur.match(")") {
					return nil, p.raiseError("Unterminated lookbehind", p.cur.i)
				}
				return Look{Dir: "Behind", Neg: true, Body: body}, nil
			}

			// Otherwise, it's a named group
			name := ""
			for !p.cur.eof() && p.cur.peek(0) != ">" {
				name += p.cur.take()
			}
			if p.cur.eof() {
				return nil, p.raiseError("Unterminated group name", p.cur.i)
			}
			p.cur.take() // consume >

			// Validate group name
			validName := regexp.MustCompile(`^[a-zA-Z_][a-zA-Z0-9_]*$`)
			if name == "" || !validName.MatchString(name) {
				return nil, p.raiseError("Invalid group name", p.cur.i)
			}
			if p.capNames[name] {
				return nil, p.raiseError(fmt.Sprintf("Duplicate group name <%s>", name), p.cur.i)
			}

			body, err := p.parseAlt()
			if err != nil {
				return nil, err
			}
			if !p.cur.match(")") {
				return nil, p.raiseError("Unterminated group", p.cur.i)
			}

			p.capCount++
			p.capNames[name] = true
			return Group{Capturing: true, Body: body, Name: &name, Atomic: nil}, nil
		}

		// Atomic group
		if p.cur.match(">") {
			body, err := p.parseAlt()
			if err != nil {
				return nil, err
			}
			if !p.cur.match(")") {
				return nil, p.raiseError("Unterminated atomic group", p.cur.i)
			}
			atomic := true
			return Group{Capturing: false, Body: body, Name: nil, Atomic: &atomic}, nil
		}

		// Inline modifier detection (e.g. (?i), (?ms))
		ch0 := p.cur.peek(0)
		if ch0 != "" && strings.ContainsRune("imsux", rune(ch0[0])) {
			// Check if this looks like an inline modifier
			j := 0
			for p.cur.i+j < len(p.cur.text) && strings.ContainsRune("imsux", rune(p.cur.text[p.cur.i+j])) {
				j++
			}
			if p.cur.i+j < len(p.cur.text) && p.cur.text[p.cur.i+j] == ')' {
				return nil, p.raiseError("Inline modifiers are not supported", p.cur.i-2)
			}
		}

		return nil, p.raiseError("Unknown group type", p.cur.i)
	}

	// Capturing group
	p.capCount++
	body, err := p.parseAlt()
	if err != nil {
		return nil, err
	}
	if !p.cur.match(")") {
		return nil, p.raiseError("Unterminated group", p.cur.i)
	}

	return Group{Capturing: true, Body: body, Name: nil, Atomic: nil}, nil
}

// parseQuantifier checks for and parses quantifiers.
func (p *Parser) parseQuantifier(child Node) (Node, error) {
	p.cur.skipWsAndComments()

	if p.cur.eof() {
		return child, nil
	}

	var min, max int
	var maxInf bool
	hasQuant := false

	// Check for quantifier symbols
	if p.cur.match("*") {
		min, max, maxInf = 0, 0, true
		hasQuant = true
	} else if p.cur.match("+") {
		min, max, maxInf = 1, 0, true
		hasQuant = true
	} else if p.cur.match("?") {
		min, max, maxInf = 0, 1, false
		hasQuant = true
	} else if p.cur.peek(0) == "{" {
		save := p.cur.i
		p.cur.take() // consume {
		hasQuant = true

		// Look ahead to check for invalid brace quantifier content
		lookAhead := ""
		j := p.cur.i
		for j < len(p.cur.text) && p.cur.text[j] != '}' {
			lookAhead += string(p.cur.text[j])
			j++
		}
		validContent := regexp.MustCompile(`^\d+(,\d*)?$`)
		if j < len(p.cur.text) && p.cur.text[j] == '}' && lookAhead != "" && !validContent.MatchString(lookAhead) {
			return nil, p.raiseError("Brace quantifier: Invalid brace quantifier content", save)
		}

		// Parse {n,m} quantifier
		numStr := ""
		for !p.cur.eof() && p.cur.peek(0) >= "0" && p.cur.peek(0) <= "9" {
			numStr += p.cur.take()
		}
		if numStr == "" {
			return nil, p.raiseError("Expected number in quantifier", p.cur.i)
		}
		fmt.Sscanf(numStr, "%d", &min)

		if p.cur.match(",") {
			numStr = ""
			for !p.cur.eof() && p.cur.peek(0) >= "0" && p.cur.peek(0) <= "9" {
				numStr += p.cur.take()
			}
			if numStr == "" {
				max = 0
				maxInf = true
			} else {
				fmt.Sscanf(numStr, "%d", &max)
				maxInf = false
			}
		} else {
			max = min
			maxInf = false
		}

		if !p.cur.match("}") {
			return nil, p.raiseError("Incomplete quantifier", p.cur.i)
		}

		// Validate range
		if !maxInf && min > max {
			return nil, p.raiseError("Invalid quantifier range", save)
		}
	}

	if !hasQuant {
		return child, nil
	}

	// Cannot quantify anchor
	if _, ok := child.(Anchor); ok {
		return nil, p.raiseError("Cannot quantify anchor", p.cur.i)
	}

	// Check for lazy/possessive mode
	mode := "Greedy"
	if p.cur.match("?") {
		mode = "Lazy"
	} else if p.cur.match("+") {
		mode = "Possessive"
	}

	var maxVal interface{}
	if maxInf {
		maxVal = "Inf"
	} else {
		maxVal = max
	}

	return Quant{Child: child, Min: min, Max: maxVal, Mode: mode}, nil
}

// parseHexEscape parses \x hex escapes.
func (p *Parser) parseHexEscape(startPos int) (Node, error) {
	if p.cur.peek(0) == "{" {
		p.cur.take() // consume {
		hex := ""
		for !p.cur.eof() && isHexDigit(p.cur.peek(0)) {
			hex += p.cur.take()
		}
		if !p.cur.match("}") {
			return nil, p.raiseError("Unterminated \\x{...}", startPos)
		}
		return Lit{Value: hexToChar(hex)}, nil
	}

	h1 := p.cur.take()
	h2 := p.cur.take()
	if !isHexDigit(h1) || !isHexDigit(h2) {
		return nil, p.raiseError("Invalid \\xHH escape", startPos)
	}
	return Lit{Value: hexToChar(h1 + h2)}, nil
}

// parseUnicodeEscape parses \u and \U unicode escapes.
func (p *Parser) parseUnicodeEscape(tp string, startPos int) (Node, error) {
	if tp == "u" && p.cur.peek(0) == "{" {
		p.cur.take() // consume {
		hex := ""
		for !p.cur.eof() && isHexDigit(p.cur.peek(0)) {
			hex += p.cur.take()
		}
		if !p.cur.match("}") {
			return nil, p.raiseError("Unterminated \\u{...}", startPos)
		}
		return Lit{Value: hexToChar(hex)}, nil
	}

	if tp == "u" {
		hex := ""
		for i := 0; i < 4; i++ {
			hex += p.cur.take()
		}
		if !regexp.MustCompile(`^[0-9A-Fa-f]{4}$`).MatchString(hex) {
			return nil, p.raiseError("Invalid \\uHHHH escape", startPos)
		}
		return Lit{Value: hexToChar(hex)}, nil
	}

	if tp == "U" {
		hex := ""
		for i := 0; i < 8; i++ {
			hex += p.cur.take()
		}
		if !regexp.MustCompile(`^[0-9A-Fa-f]{8}$`).MatchString(hex) {
			return nil, p.raiseError("Invalid \\UHHHHHHHH escape", startPos)
		}
		return Lit{Value: hexToChar(hex)}, nil
	}

	return nil, p.raiseError("Invalid unicode escape", startPos)
}

func isHexDigit(s string) bool {
	if s == "" {
		return false
	}
	c := s[0]
	return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F')
}

func hexToChar(hex string) string {
	if hex == "" {
		return "\x00"
	}
	var cp int64
	fmt.Sscanf(hex, "%x", &cp)
	return string(rune(cp))
}
