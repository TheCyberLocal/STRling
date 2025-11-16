package core

// STRling Intermediate Representation (IR) Node Definitions
//
// This file defines the complete set of IR node classes that represent
// language-agnostic regex constructs. The IR serves as an intermediate layer
// between the parsed AST and the target-specific emitters (e.g., PCRE2).
//
// IR nodes are designed to be:
//   - Simple and composable
//   - Easy to serialize (via ToDict methods)
//   - Independent of any specific regex flavor
//   - Optimized for transformation and analysis
//
// Each IR node corresponds to a fundamental regex operation (alternation,
// sequencing, character classes, quantification, etc.) and can be serialized
// to a map representation for further processing or debugging.

// IROp is the base interface for all IR operations.
//
// All IR nodes extend this base interface and must implement the ToDict() method
// for serialization to a map representation.
type IROp interface {
	// ToDict serializes the IR node to a map representation.
	ToDict() map[string]interface{}
}

// IRAlt represents an alternation (OR) operation in the IR.
//
// Matches any one of the provided branches. Equivalent to the | operator
// in traditional regex syntax.
type IRAlt struct {
	Branches []IROp
}

// ToDict serializes IRAlt to a map representation.
func (a IRAlt) ToDict() map[string]interface{} {
	branches := make([]interface{}, len(a.Branches))
	for i, b := range a.Branches {
		branches[i] = b.ToDict()
	}
	return map[string]interface{}{
		"ir":       "Alt",
		"branches": branches,
	}
}

// IRSeq represents a sequence operation in the IR.
//
// Matches parts in sequential order.
type IRSeq struct {
	Parts []IROp
}

// ToDict serializes IRSeq to a map representation.
func (s IRSeq) ToDict() map[string]interface{} {
	parts := make([]interface{}, len(s.Parts))
	for i, p := range s.Parts {
		parts[i] = p.ToDict()
	}
	return map[string]interface{}{
		"ir":    "Seq",
		"parts": parts,
	}
}

// IRLit represents a literal string in the IR.
type IRLit struct {
	Value string
}

// ToDict serializes IRLit to a map representation.
func (l IRLit) ToDict() map[string]interface{} {
	return map[string]interface{}{
		"ir":    "Lit",
		"value": l.Value,
	}
}

// IRDot represents the wildcard dot (.) in the IR.
type IRDot struct{}

// ToDict serializes IRDot to a map representation.
func (d IRDot) ToDict() map[string]interface{} {
	return map[string]interface{}{
		"ir": "Dot",
	}
}

// IRAnchor represents an anchor in the IR.
type IRAnchor struct {
	At string
}

// ToDict serializes IRAnchor to a map representation.
func (a IRAnchor) ToDict() map[string]interface{} {
	return map[string]interface{}{
		"ir": "Anchor",
		"at": a.At,
	}
}

// IRClassItem is the base interface for character class items in the IR.
type IRClassItem interface {
	// ToDict serializes the class item to a map representation
	ToDict() map[string]interface{}
}

// IRClassRange represents a character range in the IR.
type IRClassRange struct {
	FromCh string
	ToCh   string
}

// ToDict serializes IRClassRange to a map representation.
func (cr IRClassRange) ToDict() map[string]interface{} {
	return map[string]interface{}{
		"ir":   "Range",
		"from": cr.FromCh,
		"to":   cr.ToCh,
	}
}

// IRClassLiteral represents a literal character in the IR.
type IRClassLiteral struct {
	Ch string
}

// ToDict serializes IRClassLiteral to a map representation.
func (cl IRClassLiteral) ToDict() map[string]interface{} {
	return map[string]interface{}{
		"ir":   "Char",
		"char": cl.Ch,
	}
}

// IRClassEscape represents an escape sequence in the IR.
type IRClassEscape struct {
	Type     string
	Property *string
}

// ToDict serializes IRClassEscape to a map representation.
func (ce IRClassEscape) ToDict() map[string]interface{} {
	d := map[string]interface{}{
		"ir":   "Esc",
		"type": ce.Type,
	}
	if ce.Property != nil {
		d["property"] = *ce.Property
	}
	return d
}

// IRCharClass represents a character class in the IR.
type IRCharClass struct {
	Negated bool
	Items   []IRClassItem
}

// ToDict serializes IRCharClass to a map representation.
func (cc IRCharClass) ToDict() map[string]interface{} {
	items := make([]interface{}, len(cc.Items))
	for i, item := range cc.Items {
		items[i] = item.ToDict()
	}
	return map[string]interface{}{
		"ir":      "CharClass",
		"negated": cc.Negated,
		"items":   items,
	}
}

// IRQuant represents a quantifier in the IR.
type IRQuant struct {
	Child IROp
	Min   int
	// Max can be an integer or "Inf" for unbounded
	Max interface{}
	// Mode is "Greedy", "Lazy", or "Possessive"
	Mode string
}

// ToDict serializes IRQuant to a map representation.
func (q IRQuant) ToDict() map[string]interface{} {
	return map[string]interface{}{
		"ir":    "Quant",
		"child": q.Child.ToDict(),
		"min":   q.Min,
		"max":   q.Max,
		"mode":  q.Mode,
	}
}

// IRGroup represents a grouping in the IR.
type IRGroup struct {
	Capturing bool
	Body      IROp
	Name      *string
	Atomic    *bool
}

// ToDict serializes IRGroup to a map representation.
func (g IRGroup) ToDict() map[string]interface{} {
	d := map[string]interface{}{
		"ir":        "Group",
		"capturing": g.Capturing,
		"body":      g.Body.ToDict(),
	}
	if g.Name != nil {
		d["name"] = *g.Name
	}
	if g.Atomic != nil {
		d["atomic"] = *g.Atomic
	}
	return d
}

// IRBackref represents a backreference in the IR.
type IRBackref struct {
	ByIndex *int
	ByName  *string
}

// ToDict serializes IRBackref to a map representation.
func (b IRBackref) ToDict() map[string]interface{} {
	d := map[string]interface{}{
		"ir": "Backref",
	}
	if b.ByIndex != nil {
		d["byIndex"] = *b.ByIndex
	}
	if b.ByName != nil {
		d["byName"] = *b.ByName
	}
	return d
}

// IRLook represents a lookaround assertion in the IR.
type IRLook struct {
	Dir  string
	Neg  bool
	Body IROp
}

// ToDict serializes IRLook to a map representation.
func (l IRLook) ToDict() map[string]interface{} {
	return map[string]interface{}{
		"ir":   "Look",
		"dir":  l.Dir,
		"neg":  l.Neg,
		"body": l.Body.ToDict(),
	}
}
