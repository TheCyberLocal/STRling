<?php

namespace STRling\Core;

/**
 * STRling AST Node Definitions
 * 
 * This module defines the complete set of Abstract Syntax Tree (AST) node classes
 * that represent the parsed structure of STRling patterns. The AST is the direct
 * output of the parser and represents the syntactic structure of the pattern before
 * optimization and lowering to IR.
 * 
 * AST nodes are designed to:
 *   - Closely mirror the source pattern syntax
 *   - Be easily serializable to the Base TargetArtifact schema
 *   - Provide a clean separation between parsing and compilation
 *   - Support multiple target regex flavors through the compilation pipeline
 * 
 * Each AST node type corresponds to a syntactic construct in the STRling DSL
 * (alternation, sequencing, character classes, anchors, etc.) and can be
 * serialized to a dictionary representation for debugging or storage.
 * 
 * @package STRling\Core
 */

// ---- Flags container ----

/**
 * Container for regex flags/modifiers.
 * 
 * Flags control the behavior of pattern matching (case sensitivity, multiline
 * mode, etc.). This class encapsulates all standard regex flags.
 */
class Flags
{
    public bool $ignoreCase = false;
    public bool $multiline = false;
    public bool $dotAll = false;
    public bool $unicode = false;
    public bool $extended = false;
    
    /**
     * Serialize the flags to an array representation.
     * 
     * @return array<string, bool> The flags as an associative array
     */
    public function toDict(): array
    {
        return [
            'ignoreCase' => $this->ignoreCase,
            'multiline' => $this->multiline,
            'dotAll' => $this->dotAll,
            'unicode' => $this->unicode,
            'extended' => $this->extended,
        ];
    }
    
    /**
     * Create Flags from a string of flag letters.
     * 
     * @param string $letters String containing flag letters (i, m, s, u, x)
     * @return self A new Flags instance with the specified flags enabled
     */
    public static function fromLetters(string $letters): self
    {
        $f = new self();
        $cleaned = str_replace([',', ' '], '', $letters);
        
        for ($i = 0; $i < strlen($cleaned); $i++) {
            $ch = $cleaned[$i];
            switch ($ch) {
                case 'i':
                    $f->ignoreCase = true;
                    break;
                case 'm':
                    $f->multiline = true;
                    break;
                case 's':
                    $f->dotAll = true;
                    break;
                case 'u':
                    $f->unicode = true;
                    break;
                case 'x':
                    $f->extended = true;
                    break;
                case '':
                    break;
                default:
                    // Unknown flags are ignored at parser stage; may be warned later
                    break;
            }
        }
        
        return $f;
    }
}

// ---- Base node interface ----

/**
 * Base interface for all AST nodes.
 * 
 * All AST node classes must implement this interface and provide
 * a toDict() method for serialization.
 */
interface ASTNode
{
    /**
     * Serialize the node to an array representation.
     * 
     * @return array<string, mixed> The node as an associative array
     */
    public function toDict(): array;
}

// ---- Concrete nodes matching Base Schema ----

/**
 * Alternation node - represents OR operations.
 * 
 * Matches any one of the provided branches.
 */
class Alt implements ASTNode
{
    /**
     * @param array<ASTNode> $branches The alternative branches
     */
    public function __construct(
        public array $branches
    ) {}
    
    public function toDict(): array
    {
        return [
            'kind' => 'Alt',
            'branches' => array_map(fn($b) => $b->toDict(), $this->branches)
        ];
    }
}

/**
 * Sequence node - represents sequential matching.
 * 
 * Matches all parts in order.
 */
class Seq implements ASTNode
{
    /**
     * @param array<ASTNode> $parts The sequential parts
     */
    public function __construct(
        public array $parts
    ) {}
    
    public function toDict(): array
    {
        return [
            'kind' => 'Seq',
            'parts' => array_map(fn($p) => $p->toDict(), $this->parts)
        ];
    }
}

/**
 * Literal node - represents a literal string match.
 */
class Lit implements ASTNode
{
    public function __construct(
        public string $value
    ) {}
    
    public function toDict(): array
    {
        return [
            'kind' => 'Lit',
            'value' => $this->value
        ];
    }
}

/**
 * Dot node - represents the wildcard (.) metacharacter.
 * 
 * Matches any character (except newline by default).
 */
class Dot implements ASTNode
{
    public function toDict(): array
    {
        return ['kind' => 'Dot'];
    }
}

/**
 * Anchor node - represents position assertions.
 * 
 * Anchors match at specific positions in the text (start, end, word boundaries).
 */
class Anchor implements ASTNode
{
    /**
     * @param string $at Position type: "Start"|"End"|"WordBoundary"|"NotWordBoundary"|Absolute* variants
     */
    public function __construct(
        public string $at
    ) {}
    
    public function toDict(): array
    {
        return [
            'kind' => 'Anchor',
            'at' => $this->at
        ];
    }
}

// ---- CharClass ----

/**
 * Base interface for character class items.
 */
interface ClassItem
{
    /**
     * Serialize the class item to an array representation.
     * 
     * @return array<string, mixed> The class item as an associative array
     */
    public function toDict(): array;
}

/**
 * Character range in a character class.
 * 
 * Represents a range like [a-z].
 */
class ClassRange implements ClassItem
{
    public function __construct(
        public string $from_ch,
        public string $to_ch
    ) {}
    
    public function toDict(): array
    {
        return [
            'kind' => 'Range',
            'from' => $this->from_ch,
            'to' => $this->to_ch
        ];
    }
}

/**
 * Literal character in a character class.
 */
class ClassLiteral implements ClassItem
{
    public function __construct(
        public string $ch
    ) {}
    
    public function toDict(): array
    {
        return [
            'kind' => 'Char',
            'char' => $this->ch
        ];
    }
}

/**
 * Escape sequence in a character class.
 * 
 * Represents escapes like \d, \w, \s, \p{...}, etc.
 */
class ClassEscape implements ClassItem
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
        $data = [
            'kind' => 'Esc',
            'type' => $this->type
        ];
        
        if (in_array($this->type, ['p', 'P']) && $this->property !== null) {
            $data['property'] = $this->property;
        }
        
        return $data;
    }
}

/**
 * Character class node - represents [...] constructs.
 * 
 * Matches any character from the specified set.
 */
class CharClass implements ASTNode
{
    /**
     * @param bool $negated Whether this is a negated class [^...]
     * @param array<ClassItem> $items The items in the character class
     */
    public function __construct(
        public bool $negated,
        public array $items
    ) {}
    
    public function toDict(): array
    {
        return [
            'kind' => 'CharClass',
            'negated' => $this->negated,
            'items' => array_map(fn($it) => $it->toDict(), $this->items)
        ];
    }
}

/**
 * Quantifier node - represents repetition.
 * 
 * Quantifies how many times the child pattern should match.
 */
class Quant implements ASTNode
{
    /**
     * @param ASTNode $child The pattern to quantify
     * @param int $min Minimum repetitions
     * @param int|string $max Maximum repetitions (int or "Inf" for unbounded)
     * @param string $mode Quantifier mode: "Greedy"|"Lazy"|"Possessive"
     */
    public function __construct(
        public ASTNode $child,
        public int $min,
        public int|string $max,
        public string $mode
    ) {}
    
    public function toDict(): array
    {
        return [
            'kind' => 'Quant',
            'child' => $this->child->toDict(),
            'min' => $this->min,
            'max' => $this->max,
            'mode' => $this->mode
        ];
    }
}

/**
 * Group node - represents capturing and non-capturing groups.
 * 
 * Groups patterns together and optionally captures matched text.
 */
class Group implements ASTNode
{
    /**
     * @param bool $capturing Whether this is a capturing group
     * @param ASTNode $body The grouped pattern
     * @param string|null $name Named capture group name
     * @param bool|null $atomic Whether this is an atomic group (extension)
     */
    public function __construct(
        public bool $capturing,
        public ASTNode $body,
        public ?string $name = null,
        public ?bool $atomic = null
    ) {}
    
    public function toDict(): array
    {
        $data = [
            'kind' => 'Group',
            'capturing' => $this->capturing,
            'body' => $this->body->toDict()
        ];
        
        if ($this->name !== null) {
            $data['name'] = $this->name;
        }
        
        if ($this->atomic !== null) {
            $data['atomic'] = $this->atomic;
        }
        
        return $data;
    }
}

/**
 * Backreference node - references a previously captured group.
 */
class Backref implements ASTNode
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
        $data = ['kind' => 'Backref'];
        
        if ($this->byIndex !== null) {
            $data['byIndex'] = $this->byIndex;
        }
        
        if ($this->byName !== null) {
            $data['byName'] = $this->byName;
        }
        
        return $data;
    }
}

/**
 * Lookaround node - represents lookahead and lookbehind assertions.
 * 
 * Asserts that a pattern does (or doesn't) match at the current position
 * without consuming characters.
 */
class Look implements ASTNode
{
    /**
     * @param string $dir Direction: "Ahead"|"Behind"
     * @param bool $neg Whether this is a negative lookaround
     * @param ASTNode $body The pattern to assert
     */
    public function __construct(
        public string $dir,
        public bool $neg,
        public ASTNode $body
    ) {}
    
    public function toDict(): array
    {
        return [
            'kind' => 'Look',
            'dir' => $this->dir,
            'neg' => $this->neg,
            'body' => $this->body->toDict()
        ];
    }
}
