package strling

import (
	"encoding/json"
	"fmt"

	"github.com/thecyberlocal/strling/bindings/go/core"
)

// SpecNode is the interface for all AST nodes from the JSON spec.
type SpecNode interface {
	ToCore() (core.Node, error)
}

// NodeWrapper handles polymorphic JSON unmarshalling.
type NodeWrapper struct {
	Node SpecNode
}

func (w *NodeWrapper) UnmarshalJSON(data []byte) error {
	var base struct {
		Type string `json:"type"`
	}
	if err := json.Unmarshal(data, &base); err != nil {
		return err
	}

	switch base.Type {
	case "Literal":
		var n Literal
		if err := json.Unmarshal(data, &n); err != nil {
			return err
		}
		w.Node = &n
	case "Sequence":
		var n Sequence
		if err := json.Unmarshal(data, &n); err != nil {
			return err
		}
		w.Node = &n
	case "Alternation":
		var n Alternation
		if err := json.Unmarshal(data, &n); err != nil {
			return err
		}
		w.Node = &n
	case "Group":
		var n Group
		if err := json.Unmarshal(data, &n); err != nil {
			return err
		}
		w.Node = &n
	case "Quantifier":
		var n Quantifier
		if err := json.Unmarshal(data, &n); err != nil {
			return err
		}
		w.Node = &n
	case "CharacterClass":
		var n CharacterClass
		if err := json.Unmarshal(data, &n); err != nil {
			return err
		}
		w.Node = &n
	case "Anchor":
		var n Anchor
		if err := json.Unmarshal(data, &n); err != nil {
			return err
		}
		w.Node = &n
	case "Dot":
		var n Dot
		if err := json.Unmarshal(data, &n); err != nil {
			return err
		}
		w.Node = &n
	case "Range":
		var n Range
		if err := json.Unmarshal(data, &n); err != nil {
			return err
		}
		w.Node = &n
	case "Backreference":
		var n Backreference
		if err := json.Unmarshal(data, &n); err != nil {
			return err
		}
		w.Node = &n
	case "Lookaround":
		var n Lookaround
		if err := json.Unmarshal(data, &n); err != nil {
			return err
		}
		w.Node = &n
	case "Escape": // For CharacterClass escapes
		var n Escape
		if err := json.Unmarshal(data, &n); err != nil {
			return err
		}
		w.Node = &n
	default:
		return fmt.Errorf("unknown node type: %s", base.Type)
	}
	return nil
}

// Literal
type Literal struct {
	Value string `json:"value"`
}

func (n *Literal) ToCore() (core.Node, error) {
	return core.Lit{Value: n.Value}, nil
}

func (n *Literal) ToClassItem() (core.ClassItem, error) {
	if len(n.Value) != 1 {
		return nil, fmt.Errorf("literal in character class must be single char, got '%s'", n.Value)
	}
	return core.ClassLiteral{Ch: n.Value}, nil
}

// Sequence
type Sequence struct {
	Elements []NodeWrapper `json:"elements"`
}

func (n *Sequence) ToCore() (core.Node, error) {
	parts := make([]core.Node, len(n.Elements))
	for i, el := range n.Elements {
		c, err := el.Node.ToCore()
		if err != nil {
			return nil, err
		}
		parts[i] = c
	}
	return core.Seq{Parts: parts}, nil
}

// Alternation
type Alternation struct {
	Options []NodeWrapper `json:"options"`
}

func (n *Alternation) ToCore() (core.Node, error) {
	branches := make([]core.Node, len(n.Options))
	for i, opt := range n.Options {
		c, err := opt.Node.ToCore()
		if err != nil {
			return nil, err
		}
		branches[i] = c
	}
	return core.Alt{Branches: branches}, nil
}

// Group
type Group struct {
	Capturing bool        `json:"capturing"`
	Body      NodeWrapper `json:"body"`
	Name      *string     `json:"name"`
	Atomic    bool        `json:"atomic"`
}

func (n *Group) ToCore() (core.Node, error) {
	body, err := n.Body.Node.ToCore()
	if err != nil {
		return nil, err
	}
	atomic := n.Atomic
	return core.Group{
		Capturing: n.Capturing,
		Body:      body,
		Name:      n.Name,
		Atomic:    &atomic,
	}, nil
}

// Quantifier
type Quantifier struct {
	Target     NodeWrapper `json:"target"`
	Min        int         `json:"min"`
	Max        *int        `json:"max"` // Nullable
	Greedy     bool        `json:"greedy"`
	Lazy       bool        `json:"lazy"`
	Possessive bool        `json:"possessive"`
}

func (n *Quantifier) ToCore() (core.Node, error) {
	child, err := n.Target.Node.ToCore()
	if err != nil {
		return nil, err
	}

	var max interface{}
	if n.Max == nil {
		max = "Inf"
	} else {
		max = *n.Max
	}

	mode := "Greedy"
	if n.Lazy {
		mode = "Lazy"
	} else if n.Possessive {
		mode = "Possessive"
	}

	return core.Quant{
		Child: child,
		Min:   n.Min,
		Max:   max,
		Mode:  mode,
	}, nil
}

// CharacterClass
type CharacterClass struct {
	Negated bool          `json:"negated"`
	Members []NodeWrapper `json:"members"`
}

func (n *CharacterClass) ToCore() (core.Node, error) {
	items := make([]core.ClassItem, len(n.Members))
	for i, m := range n.Members {
		// Try to convert to ClassItem
		if lit, ok := m.Node.(*Literal); ok {
			item, err := lit.ToClassItem()
			if err != nil {
				return nil, err
			}
			items[i] = item
		} else if rng, ok := m.Node.(*Range); ok {
			item, err := rng.ToClassItem()
			if err != nil {
				return nil, err
			}
			items[i] = item
		} else if esc, ok := m.Node.(*Escape); ok {
			item, err := esc.ToClassItem()
			if err != nil {
				return nil, err
			}
			items[i] = item
		} else {
			return nil, fmt.Errorf("unsupported node type in character class: %T", m.Node)
		}
	}
	return core.CharClass{
		Negated: n.Negated,
		Items:   items,
	}, nil
}

// Range
type Range struct {
	Start string `json:"start"`
	End   string `json:"end"`
}

func (n *Range) ToCore() (core.Node, error) {
	return nil, fmt.Errorf("Range cannot be used as a standalone core.Node")
}

func (n *Range) ToClassItem() (core.ClassItem, error) {
	return core.ClassRange{
		FromCh: n.Start,
		ToCh:   n.End,
	}, nil
}

// Anchor
type Anchor struct {
	At string `json:"at"`
}

func (n *Anchor) ToCore() (core.Node, error) {
	return core.Anchor{At: n.At}, nil
}

// Dot
type Dot struct{}

func (n *Dot) ToCore() (core.Node, error) {
	return core.Dot{}, nil
}

// Backreference
type Backreference struct {
	Index *int    `json:"index"`
	Name  *string `json:"name"`
}

func (n *Backreference) ToCore() (core.Node, error) {
	return core.Backref{
		ByIndex: n.Index,
		ByName:  n.Name,
	}, nil
}

// Lookaround
type Lookaround struct {
	Direction string      `json:"direction"` // "ahead" or "behind"
	Negative  bool        `json:"negative"`
	Body      NodeWrapper `json:"body"`
}

func (n *Lookaround) ToCore() (core.Node, error) {
	body, err := n.Body.Node.ToCore()
	if err != nil {
		return nil, err
	}
	dir := "Ahead"
	if n.Direction == "behind" {
		dir = "Behind"
	}
	return core.Look{
		Dir:  dir,
		Neg:  n.Negative,
		Body: body,
	}, nil
}

// Escape (for CharacterClass)
type Escape struct {
	Type     string  `json:"escape_type"` // d, D, w, W, s, S, p, P
	Property *string `json:"property"`
}

func (n *Escape) ToCore() (core.Node, error) {
	return nil, fmt.Errorf("Escape cannot be used as a standalone core.Node")
}

func (n *Escape) ToClassItem() (core.ClassItem, error) {
	return core.ClassEscape{
		Type:     n.Type,
		Property: n.Property,
	}, nil
}
