<?php

namespace STRling\Core;

/**
 * STRling Intermediate Representation (IR) Node Definitions
 * 
 * This module defines the complete set of IR node classes that represent
 * language-agnostic regex constructs. The IR serves as an intermediate layer
 * between the parsed AST and the target-specific emitters (e.g., PCRE2).
 * 
 * IR nodes are designed to be:
 *   - Simple and composable
 *   - Easy to serialize (via toDict methods)
 *   - Independent of any specific regex flavor
 *   - Optimized for transformation and analysis
 * 
 * Each IR node corresponds to a fundamental regex operation (alternation,
 * sequencing, character classes, quantification, etc.) and can be serialized
 * to a dictionary representation for further processing or debugging.
 * 
 * @package STRling\Core
 */

/**
 * Base interface for all IR operations.
 * 
 * All IR nodes extend this interface and must implement the toDict() method
 * for serialization to an array representation.
 */
interface IROp
{
    /**
     * Serialize the IR node to an array representation.
     * 
     * @return array<string, mixed> The array representation of this IR node
     */
    public function toDict(): array;
}

/**
 * Represents an alternation (OR) operation in the IR.
 * 
 * Matches any one of the provided branches. Equivalent to the | operator
 * in traditional regex syntax.
 */
class IRAlt implements IROp
{
    /**
     * @param array<IROp> $branches The alternative branches
     */
    public function __construct(
        public array $branches
    ) {}
    
    public function toDict(): array
    {
        return [
            'ir' => 'Alt',
            'branches' => array_map(fn($b) => $b->toDict(), $this->branches)
        ];
    }
}

/**
 * Represents a sequence operation in the IR.
 * 
 * Matches all parts in sequential order.
 */
class IRSeq implements IROp
{
    /**
     * @param array<IROp> $parts The sequential parts
     */
    public function __construct(
        public array $parts
    ) {}
    
    public function toDict(): array
    {
        return [
            'ir' => 'Seq',
            'parts' => array_map(fn($p) => $p->toDict(), $this->parts)
        ];
    }
}

/**
 * Represents a literal string match in the IR.
 */
class IRLit implements IROp
{
    public function __construct(
        public string $value
    ) {}
    
    public function toDict(): array
    {
        return [
            'ir' => 'Lit',
            'value' => $this->value
        ];
    }
}

/**
 * Represents the wildcard (.) metacharacter in the IR.
 * 
 * Matches any character (except newline by default).
 */
class IRDot implements IROp
{
    public function toDict(): array
    {
        return ['ir' => 'Dot'];
    }
}

/**
 * Represents a position anchor in the IR.
 * 
 * Anchors match at specific positions in the text.
 */
class IRAnchor implements IROp
{
    /**
     * @param string $at Position type: "Start"|"End"|"WordBoundary"|etc.
     */
    public function __construct(
        public string $at
    ) {}
    
    public function toDict(): array
    {
        return [
            'ir' => 'Anchor',
            'at' => $this->at
        ];
    }
}

// ---- Character Class Items ----

/**
 * Base interface for IR character class items.
 */
interface IRClassItem
{
    /**
     * Serialize the class item to an array representation.
     * 
     * @return array<string, mixed> The class item as an associative array
     */
    public function toDict(): array;
}

/**
 * Represents a character range in an IR character class.
 */
class IRClassRange implements IRClassItem
{
    public function __construct(
        public string $from_ch,
        public string $to_ch
    ) {}
    
    public function toDict(): array
    {
        return [
            'ir' => 'Range',
            'from' => $this->from_ch,
            'to' => $this->to_ch
        ];
    }
}

/**
 * Represents a literal character in an IR character class.
 */
class IRClassLiteral implements IRClassItem
{
    public function __construct(
        public string $ch
    ) {}
    
    public function toDict(): array
    {
        return [
            'ir' => 'Char',
            'char' => $this->ch
        ];
    }
}

/**
 * Represents an escape sequence in an IR character class.
 */
class IRClassEscape implements IRClassItem
{
    /**
     * @param string $type Escape type: d, D, w, W, s, S, p, P
     * @param string|null $property Unicode property name (for \p and \P)
     */
    public function __construct(
        public string $type,
        public ?string $property = null
    ) {}
    
    public function toDict(): array
    {
        $d = [
            'ir' => 'Esc',
            'type' => $this->type
        ];
        
        if ($this->property !== null) {
            $d['property'] = $this->property;
        }
        
        return $d;
    }
}

/**
 * Represents a character class in the IR.
 * 
 * Matches any character from the specified set.
 */
class IRCharClass implements IROp
{
    /**
     * @param bool $negated Whether this is a negated class
     * @param array<IRClassItem> $items The items in the character class
     */
    public function __construct(
        public bool $negated,
        public array $items
    ) {}
    
    public function toDict(): array
    {
        return [
            'ir' => 'CharClass',
            'negated' => $this->negated,
            'items' => array_map(fn($i) => $i->toDict(), $this->items)
        ];
    }
}

/**
 * Represents a quantifier in the IR.
 * 
 * Specifies how many times the child pattern should match.
 */
class IRQuant implements IROp
{
    /**
     * @param IROp $child The pattern to quantify
     * @param int $min Minimum repetitions
     * @param int|string $max Maximum repetitions (int or "Inf" for unbounded)
     * @param string $mode Quantifier mode: "Greedy"|"Lazy"|"Possessive"
     */
    public function __construct(
        public IROp $child,
        public int $min,
        public int|string $max,
        public string $mode
    ) {}
    
    public function toDict(): array
    {
        return [
            'ir' => 'Quant',
            'child' => $this->child->toDict(),
            'min' => $this->min,
            'max' => $this->max,
            'mode' => $this->mode
        ];
    }
}

/**
 * Represents a group in the IR.
 * 
 * Groups patterns together and optionally captures matched text.
 */
class IRGroup implements IROp
{
    /**
     * @param bool $capturing Whether this is a capturing group
     * @param IROp $body The grouped pattern
     * @param string|null $name Named capture group name
     * @param bool|null $atomic Whether this is an atomic group
     */
    public function __construct(
        public bool $capturing,
        public IROp $body,
        public ?string $name = null,
        public ?bool $atomic = null
    ) {}
    
    public function toDict(): array
    {
        $d = [
            'ir' => 'Group',
            'capturing' => $this->capturing,
            'body' => $this->body->toDict()
        ];
        
        if ($this->name !== null) {
            $d['name'] = $this->name;
        }
        
        if ($this->atomic !== null) {
            $d['atomic'] = $this->atomic;
        }
        
        return $d;
    }
}

/**
 * Represents a backreference in the IR.
 * 
 * References a previously captured group.
 */
class IRBackref implements IROp
{
    /**
     * @param int|null $byIndex Reference by numeric index
     * @param string|null $byName Reference by named group
     */
    public function __construct(
        public ?int $byIndex = null,
        public ?string $byName = null
    ) {}
    
    public function toDict(): array
    {
        $d = ['ir' => 'Backref'];
        
        if ($this->byIndex !== null) {
            $d['byIndex'] = $this->byIndex;
        }
        
        if ($this->byName !== null) {
            $d['byName'] = $this->byName;
        }
        
        return $d;
    }
}

/**
 * Represents a lookaround assertion in the IR.
 * 
 * Asserts that a pattern does (or doesn't) match at the current position
 * without consuming characters.
 */
class IRLook implements IROp
{
    /**
     * @param string $dir Direction: "Ahead"|"Behind"
     * @param bool $neg Whether this is a negative lookaround
     * @param IROp $body The pattern to assert
     */
    public function __construct(
        public string $dir,
        public bool $neg,
        public IROp $body
    ) {}
    
    public function toDict(): array
    {
        return [
            'ir' => 'Look',
            'dir' => $this->dir,
            'neg' => $this->neg,
            'body' => $this->body->toDict()
        ];
    }
}
