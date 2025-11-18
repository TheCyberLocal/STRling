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
	hint := GetHint(message, p.src, pos)
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
		
		// Process directives only before pattern content
		if !inPattern && strings.HasPrefix(stripped, "%flags") {
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
			patternLines = append(patternLines, line)
			inPattern = true
		}
	}
	
	src := strings.Join(patternLines, "\n")
	return flags, src
}

// Parse parses the STRling pattern and returns flags and AST.
func Parse(text string) (Flags, Node, error) {
	defer func() {
		if r := recover(); r != nil {
			if err, ok := r.(*STRlingParseError); ok {
				panic(err)
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
		return Flags{}, nil, p.raiseError("Unexpected character", p.cur.i)
	}
	
	return p.flags, ast, nil
}

// parseAlt parses alternation (a|b|c).
func (p *Parser) parseAlt() (Node, error) {
	p.cur.skipWsAndComments()
	
	branches := []Node{}
	first, err := p.parseSeq()
	if err != nil {
		return nil, err
	}
	branches = append(branches, first)
	
	for {
		p.cur.skipWsAndComments()
		if !p.cur.match("|") {
			break
		}
		p.cur.skipWsAndComments()
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
	if ch == "z" {
		return Anchor{At: "AbsoluteEnd"}, nil
	}
	
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
		num := int(ch[0] - '0')
		// Continue reading digits
		for !p.cur.eof() && p.cur.peek(0) >= "0" && p.cur.peek(0) <= "9" {
			ch = p.cur.take()
			num = num*10 + int(ch[0]-'0')
		}
		return Backref{ByIndex: &num, ByName: nil}, nil
	}
	
	// Named backreference
	if ch == "k" {
		if p.cur.peek(0) != "<" {
			return nil, p.raiseError("Expected '<' after \\k", p.cur.i)
		}
		p.cur.take() // consume <
		
		name := ""
		for !p.cur.eof() && p.cur.peek(0) != ">" {
			name += p.cur.take()
		}
		
		if p.cur.eof() {
			return nil, p.raiseError("Unclosed named backreference", p.cur.i)
		}
		p.cur.take() // consume >
		
		return Backref{ByIndex: nil, ByName: &name}, nil
	}
	
	// Control escapes
	if val, ok := p.controlEscapes[ch]; ok {
		return Lit{Value: val}, nil
	}
	
	// Literal escape
	return Lit{Value: ch}, nil
}

// parseLiteral parses a literal character.
func (p *Parser) parseLiteral() (Node, error) {
	// Check for special chars that should not be treated as literals
	ch := p.cur.peek(0)
	special := "*+?{|()[]"
	if strings.ContainsRune(special, rune(ch[0])) {
		return nil, p.raiseError(fmt.Sprintf("Unexpected special character '%s'", ch), p.cur.i)
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
	
	items := []ClassItem{}
	
	for !p.cur.eof() && p.cur.peek(0) != "]" {
		item, err := p.parseClassItem()
		if err != nil {
			return nil, err
		}
		items = append(items, item)
	}
	
	if p.cur.eof() {
		return nil, p.raiseError("Unclosed character class", p.cur.i)
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
		
		// Literal escape
		return ClassLiteral{Ch: ch}, nil
	}
	
	// Check for range
	ch := p.cur.take()
	if p.cur.peek(0) == "-" && p.cur.peek(1) != "]" {
		p.cur.take() // consume -
		toCh := p.cur.take()
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
				return nil, p.raiseError("Unclosed non-capturing group", p.cur.i)
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
				return nil, p.raiseError("Unclosed lookahead", p.cur.i)
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
				return nil, p.raiseError("Unclosed negative lookahead", p.cur.i)
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
					return nil, p.raiseError("Unclosed lookbehind", p.cur.i)
				}
				return Look{Dir: "Behind", Neg: false, Body: body}, nil
			}
			if p.cur.match("!") {
				body, err := p.parseAlt()
				if err != nil {
					return nil, err
				}
				if !p.cur.match(")") {
					return nil, p.raiseError("Unclosed negative lookbehind", p.cur.i)
				}
				return Look{Dir: "Behind", Neg: true, Body: body}, nil
			}
			
			// Otherwise, it's a named group
			name := ""
			for !p.cur.eof() && p.cur.peek(0) != ">" {
				name += p.cur.take()
			}
			if p.cur.eof() {
				return nil, p.raiseError("Unclosed named group", p.cur.i)
			}
			p.cur.take() // consume >
			
			body, err := p.parseAlt()
			if err != nil {
				return nil, err
			}
			if !p.cur.match(")") {
				return nil, p.raiseError("Unclosed named group", p.cur.i)
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
				return nil, p.raiseError("Unclosed atomic group", p.cur.i)
			}
			atomic := true
			return Group{Capturing: false, Body: body, Name: nil, Atomic: &atomic}, nil
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
		return nil, p.raiseError("Unclosed capturing group", p.cur.i)
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
	} else if p.cur.match("{") {
		hasQuant = true
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
			return nil, p.raiseError("Unclosed quantifier", p.cur.i)
		}
	}
	
	if !hasQuant {
		return child, nil
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
