// Package core contains the fundamental components of the STRling compiler.
package core

// STRling Compiler - AST to IR Transformation
//
// This module implements the compiler that transforms Abstract Syntax Tree (AST)
// nodes from the parser into an optimized Intermediate Representation (IR). The
// compilation process includes:
//   - Lowering AST nodes to IR operations
//   - Flattening nested sequences and alternations
//   - Coalescing adjacent literal nodes for efficiency
//   - Ensuring quantifier children are properly grouped
//   - Analyzing and tracking regex features used
//
// The IR is designed to be easily consumed by target emitters (e.g., PCRE2)
// while maintaining semantic accuracy and enabling optimizations.

// Compiler transforms AST nodes into optimized IR.
//
// The Compiler class handles the complete transformation pipeline from parsed
// AST to normalized IR, including feature detection for metadata generation.
//
// AST -> IR lowering with normalization:
//   - Flatten nested Seq/Alt
//   - Coalesce adjacent Lit nodes
//   - Ensure quantifier children are grouped appropriately
type Compiler struct {
	featuresUsed map[string]bool
}

// NewCompiler creates a new Compiler instance.
func NewCompiler() *Compiler {
	return &Compiler{
		featuresUsed: make(map[string]bool),
	}
}

// CompileWithMetadata compiles an AST node and returns IR with metadata.
//
// This is the main entry point for compilation with full metadata tracking.
// It performs lowering, normalization, and feature analysis.
func (c *Compiler) CompileWithMetadata(rootNode Node) map[string]interface{} {
	irRoot := c.lower(rootNode)
	irRoot = c.normalize(irRoot)
	
	// Analyze the final IR tree for special features
	c.analyzeFeatures(irRoot)
	
	features := make([]string, 0, len(c.featuresUsed))
	for f := range c.featuresUsed {
		features = append(features, f)
	}
	
	return map[string]interface{}{
		"ir": irRoot,
		"metadata": map[string]interface{}{
			"features_used": features,
		},
	}
}

// Compile compiles an AST node to IR without metadata.
func (c *Compiler) Compile(root Node) IROp {
	ir := c.lower(root)
	ir = c.normalize(ir)
	return ir
}

// analyzeFeatures recursively walks the IR tree and logs features used.
func (c *Compiler) analyzeFeatures(node IROp) {
	switch n := node.(type) {
	case IRGroup:
		if n.Atomic != nil && *n.Atomic {
			c.featuresUsed["atomic_group"] = true
		}
		if n.Name != nil {
			c.featuresUsed["named_group"] = true
		}
		c.analyzeFeatures(n.Body)
		
	case IRQuant:
		if n.Mode == "Possessive" {
			c.featuresUsed["possessive_quantifier"] = true
		}
		c.analyzeFeatures(n.Child)
		
	case IRLook:
		if n.Dir == "Behind" {
			c.featuresUsed["lookbehind"] = true
		} else if n.Dir == "Ahead" {
			c.featuresUsed["lookahead"] = true
		}
		c.analyzeFeatures(n.Body)
		
	case IRBackref:
		c.featuresUsed["backreference"] = true
		
	case IRCharClass:
		// Check for Unicode property escapes in character class items
		for _, item := range n.Items {
			if esc, ok := item.(IRClassEscape); ok && esc.Type == "UnicodeProperty" {
				c.featuresUsed["unicode_property"] = true
			}
		}
		
	case IRSeq:
		for _, part := range n.Parts {
			c.analyzeFeatures(part)
		}
		
	case IRAlt:
		for _, branch := range n.Branches {
			c.analyzeFeatures(branch)
		}
	}
}

// lower converts AST nodes to IR operations.
func (c *Compiler) lower(node Node) IROp {
	switch n := node.(type) {
	case Alt:
		branches := make([]IROp, len(n.Branches))
		for i, b := range n.Branches {
			branches[i] = c.lower(b)
		}
		return IRAlt{Branches: branches}
		
	case Seq:
		parts := make([]IROp, len(n.Parts))
		for i, p := range n.Parts {
			parts[i] = c.lower(p)
		}
		return IRSeq{Parts: parts}
		
	case Lit:
		return IRLit{Value: n.Value}
		
	case Dot:
		return IRDot{}
		
	case Anchor:
		return IRAnchor{At: n.At}
		
	case CharClass:
		items := make([]IRClassItem, len(n.Items))
		for i, item := range n.Items {
			items[i] = c.lowerClassItem(item)
		}
		return IRCharClass{Negated: n.Negated, Items: items}
		
	case Quant:
		child := c.lower(n.Child)
		return IRQuant{Child: child, Min: n.Min, Max: n.Max, Mode: n.Mode}
		
	case Group:
		body := c.lower(n.Body)
		return IRGroup{Capturing: n.Capturing, Body: body, Name: n.Name, Atomic: n.Atomic}
		
	case Backref:
		return IRBackref{ByIndex: n.ByIndex, ByName: n.ByName}
		
	case Look:
		body := c.lower(n.Body)
		return IRLook{Dir: n.Dir, Neg: n.Neg, Body: body}
		
	default:
		// Unknown node type
		return IRLit{Value: ""}
	}
}

// lowerClassItem converts AST class items to IR class items.
func (c *Compiler) lowerClassItem(item ClassItem) IRClassItem {
	switch i := item.(type) {
	case ClassLiteral:
		return IRClassLiteral{Ch: i.Ch}
	case ClassRange:
		return IRClassRange{FromCh: i.FromCh, ToCh: i.ToCh}
	case ClassEscape:
		return IRClassEscape{Type: i.Type, Property: i.Property}
	default:
		return IRClassLiteral{Ch: ""}
	}
}

// normalize optimizes the IR tree.
func (c *Compiler) normalize(node IROp) IROp {
	switch n := node.(type) {
	case IRSeq:
		// Normalize children first
		parts := make([]IROp, len(n.Parts))
		for i, p := range n.Parts {
			parts[i] = c.normalize(p)
		}
		
		// Flatten nested sequences
		flattened := []IROp{}
		for _, part := range parts {
			if seq, ok := part.(IRSeq); ok {
				flattened = append(flattened, seq.Parts...)
			} else {
				flattened = append(flattened, part)
			}
		}
		
		// Coalesce adjacent literals
		coalesced := []IROp{}
		for i := 0; i < len(flattened); i++ {
			if lit, ok := flattened[i].(IRLit); ok {
				// Collect consecutive literals
				value := lit.Value
				j := i + 1
				for j < len(flattened) {
					if nextLit, ok := flattened[j].(IRLit); ok {
						value += nextLit.Value
						j++
					} else {
						break
					}
				}
				coalesced = append(coalesced, IRLit{Value: value})
				i = j - 1
			} else {
				coalesced = append(coalesced, flattened[i])
			}
		}
		
		if len(coalesced) == 1 {
			return coalesced[0]
		}
		return IRSeq{Parts: coalesced}
		
	case IRAlt:
		// Normalize children first
		branches := make([]IROp, len(n.Branches))
		for i, b := range n.Branches {
			branches[i] = c.normalize(b)
		}
		
		// Flatten nested alternations
		flattened := []IROp{}
		for _, branch := range branches {
			if alt, ok := branch.(IRAlt); ok {
				flattened = append(flattened, alt.Branches...)
			} else {
				flattened = append(flattened, branch)
			}
		}
		
		if len(flattened) == 1 {
			return flattened[0]
		}
		return IRAlt{Branches: flattened}
		
	case IRQuant:
		child := c.normalize(n.Child)
		return IRQuant{Child: child, Min: n.Min, Max: n.Max, Mode: n.Mode}
		
	case IRGroup:
		body := c.normalize(n.Body)
		return IRGroup{Capturing: n.Capturing, Body: body, Name: n.Name, Atomic: n.Atomic}
		
	case IRLook:
		body := c.normalize(n.Body)
		return IRLook{Dir: n.Dir, Neg: n.Neg, Body: body}
		
	default:
		return node
	}
}
