package core

import "strings"

// STRling AST Node Definitions
//
// This file defines the complete set of Abstract Syntax Tree (AST) node classes
// that represent the parsed structure of STRling patterns. The AST is the direct
// output of the parser and represents the syntactic structure of the pattern before
// optimization and lowering to IR.
//
// AST nodes are designed to:
//   - Closely mirror the source pattern syntax
//   - Be easily serializable to the Base TargetArtifact schema
//   - Provide a clean separation between parsing and compilation
//   - Support multiple target regex flavors through the compilation pipeline
//
// Each AST node type corresponds to a syntactic construct in the STRling DSL
// (alternation, sequencing, character classes, anchors, etc.) and can be
// serialized to a dictionary representation for debugging or storage.

// Node is the base interface for all AST nodes.
// All AST node types must implement the ToDict method for serialization.
type Node interface {
	// ToDict serializes the node to a map representation
	ToDict() map[string]interface{}
}

// Flags is a container for regex flags/modifiers.
//
// Flags control the behavior of pattern matching (case sensitivity, multiline
// mode, etc.). This struct encapsulates all standard regex flags.
type Flags struct {
	IgnoreCase bool
	Multiline  bool
	DotAll     bool
	Unicode    bool
	Extended   bool
}

// ToDict serializes the Flags to a map representation.
func (f Flags) ToDict() map[string]bool {
	return map[string]bool{
		"ignoreCase": f.IgnoreCase,
		"multiline":  f.Multiline,
		"dotAll":     f.DotAll,
		"unicode":    f.Unicode,
		"extended":   f.Extended,
	}
}

// FromLetters creates a Flags instance from a flag string.
// Recognizes flag characters: i (ignoreCase), m (multiline), s (dotAll),
// u (unicode), x (extended). Commas and spaces are ignored.
func FromLetters(letters string) Flags {
	f := Flags{}
	// Remove commas and spaces
	letters = strings.ReplaceAll(letters, ",", "")
	letters = strings.ReplaceAll(letters, " ", "")

	for _, ch := range letters {
		switch ch {
		case 'i':
			f.IgnoreCase = true
		case 'm':
			f.Multiline = true
		case 's':
			f.DotAll = true
		case 'u':
			f.Unicode = true
		case 'x':
			f.Extended = true
		default:
			// Unknown flags are ignored at parser stage; may be warned later
		}
	}
	return f
}

// Alt represents an alternation node (OR operation).
// Matches any one of the provided branches.
type Alt struct {
	Branches []Node
}

// ToDict serializes Alt to a map representation.
func (a Alt) ToDict() map[string]interface{} {
	branches := make([]interface{}, len(a.Branches))
	for i, b := range a.Branches {
		branches[i] = b.ToDict()
	}
	return map[string]interface{}{
		"kind":     "Alt",
		"branches": branches,
	}
}

// Seq represents a sequence node.
// Matches parts in sequential order.
type Seq struct {
	Parts []Node
}

// ToDict serializes Seq to a map representation.
func (s Seq) ToDict() map[string]interface{} {
	parts := make([]interface{}, len(s.Parts))
	for i, p := range s.Parts {
		parts[i] = p.ToDict()
	}
	return map[string]interface{}{
		"kind":  "Seq",
		"parts": parts,
	}
}

// Lit represents a literal string node.
type Lit struct {
	Value string
}

// ToDict serializes Lit to a map representation.
func (l Lit) ToDict() map[string]interface{} {
	return map[string]interface{}{
		"kind":  "Lit",
		"value": l.Value,
	}
}

// Dot represents the wildcard dot (.) node.
// Matches any character.
type Dot struct{}

// ToDict serializes Dot to a map representation.
func (d Dot) ToDict() map[string]interface{} {
	return map[string]interface{}{
		"kind": "Dot",
	}
}

// Anchor represents an anchor node.
// Anchors match positions rather than characters.
type Anchor struct {
	// At specifies the anchor type:
	// "Start", "End", "WordBoundary", "NotWordBoundary", or Absolute* variants
	At string
}

// ToDict serializes Anchor to a map representation.
func (a Anchor) ToDict() map[string]interface{} {
	return map[string]interface{}{
		"kind": "Anchor",
		"at":   a.At,
	}
}

// ClassItem is the base interface for character class items.
type ClassItem interface {
	// ToDict serializes the class item to a map representation
	ToDict() map[string]interface{}
}

// ClassRange represents a character range in a character class.
type ClassRange struct {
	FromCh string
	ToCh   string
}

// ToDict serializes ClassRange to a map representation.
func (cr ClassRange) ToDict() map[string]interface{} {
	return map[string]interface{}{
		"kind": "Range",
		"from": cr.FromCh,
		"to":   cr.ToCh,
	}
}

// ClassLiteral represents a literal character in a character class.
type ClassLiteral struct {
	Ch string
}

// ToDict serializes ClassLiteral to a map representation.
func (cl ClassLiteral) ToDict() map[string]interface{} {
	return map[string]interface{}{
		"kind": "Char",
		"char": cl.Ch,
	}
}

// ClassEscape represents an escape sequence in a character class.
type ClassEscape struct {
	// Type is the escape type: d, D, w, W, s, S, p, P
	Type string
	// Property is the Unicode property name (for p and P types)
	Property *string
}

// ToDict serializes ClassEscape to a map representation.
func (ce ClassEscape) ToDict() map[string]interface{} {
	data := map[string]interface{}{
		"kind": "Esc",
		"type": ce.Type,
	}
	if (ce.Type == "p" || ce.Type == "P") && ce.Property != nil {
		data["property"] = *ce.Property
	}
	return data
}

// CharClass represents a character class node.
type CharClass struct {
	Negated bool
	Items   []ClassItem
}

// ToDict serializes CharClass to a map representation.
func (cc CharClass) ToDict() map[string]interface{} {
	items := make([]interface{}, len(cc.Items))
	for i, item := range cc.Items {
		items[i] = item.ToDict()
	}
	return map[string]interface{}{
		"kind":    "CharClass",
		"negated": cc.Negated,
		"items":   items,
	}
}

// Quant represents a quantifier node.
type Quant struct {
	Child Node
	Min   int
	// Max can be an integer or "Inf" for unbounded
	Max interface{}
	// Mode is "Greedy", "Lazy", or "Possessive"
	Mode string
}

// ToDict serializes Quant to a map representation.
func (q Quant) ToDict() map[string]interface{} {
	return map[string]interface{}{
		"kind":  "Quant",
		"child": q.Child.ToDict(),
		"min":   q.Min,
		"max":   q.Max,
		"mode":  q.Mode,
	}
}

// Group represents a grouping node.
type Group struct {
	Capturing bool
	Body      Node
	Name      *string
	Atomic    *bool
}

// ToDict serializes Group to a map representation.
func (g Group) ToDict() map[string]interface{} {
	data := map[string]interface{}{
		"kind":      "Group",
		"capturing": g.Capturing,
		"body":      g.Body.ToDict(),
	}
	if g.Name != nil {
		data["name"] = *g.Name
	}
	if g.Atomic != nil {
		data["atomic"] = *g.Atomic
	}
	return data
}

// Backref represents a backreference node.
type Backref struct {
	ByIndex *int
	ByName  *string
}

// ToDict serializes Backref to a map representation.
func (b Backref) ToDict() map[string]interface{} {
	data := map[string]interface{}{
		"kind": "Backref",
	}
	if b.ByIndex != nil {
		data["byIndex"] = *b.ByIndex
	}
	if b.ByName != nil {
		data["byName"] = *b.ByName
	}
	return data
}

// Look represents a lookaround assertion node.
type Look struct {
	// Dir is "Ahead" or "Behind"
	Dir string
	// Neg indicates whether this is a negative lookaround
	Neg  bool
	Body Node
}

// ToDict serializes Look to a map representation.
func (l Look) ToDict() map[string]interface{} {
	return map[string]interface{}{
		"kind": "Look",
		"dir":  l.Dir,
		"neg":  l.Neg,
		"body": l.Body.ToDict(),
	}
}
