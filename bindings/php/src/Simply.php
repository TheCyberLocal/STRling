<?php

namespace STRling;

use STRling\Core\Nodes;
use STRling\Compiler;

/**
 * STRling Simply API - Static Pattern Constructor
 * 
 * Provides a composable API for building regex patterns using static methods.
 * This API uses static methods to wrap patterns, mimicking the Python/TypeScript nesting approach.
 * 
 * Example usage:
 * ```php
 * use STRling\Simply;
 * 
 * $phone = Simply::merge(
 *     Simply::start(),
 *     Simply::capture(Simply::digit(3)),
 *     Simply::may(Simply::inChars("-. ")),
 *     Simply::capture(Simply::digit(3)),
 *     Simply::may(Simply::inChars("-. ")),
 *     Simply::capture(Simply::digit(4)),
 *     Simply::end()
 * );
 * 
 * $regex = $phone->compile();
 * ```
 * 
 * @package STRling
 */
class Simply
{
    /**
     * Create a pattern matching digits with optional repetition.
     * 
     * @param int|null $minRep Minimum number of digits (null = match exactly once)
     * @param int|null $maxRep Maximum number of digits (null = match exactly $minRep times, 0 = unlimited)
     * @return Pattern A Pattern object representing digit pattern
     */
    public static function digit(?int $minRep = null, ?int $maxRep = null): Pattern
    {
        // Create a character class containing the digit escape (\d)
        $escapeNode = new Nodes\Escape('digit');
        $charClassNode = new Nodes\CharacterClass(
            negated: false,
            members: [$escapeNode]
        );
        
        $pattern = new Pattern($charClassNode);
        return $minRep !== null ? $pattern->rep($minRep, $maxRep) : $pattern;
    }
    
    /**
     * Create a pattern matching any one character from the provided string.
     * 
     * @param string $chars The characters to match (e.g., "-. ")
     * @return Pattern A Pattern object representing a character class
     */
    public static function anyOf(string $chars): Pattern
    {
        $members = [];
        for ($i = 0; $i < strlen($chars); $i++) {
            $members[] = new Nodes\Literal($chars[$i]);
        }
        
        $charClassNode = new Nodes\CharacterClass(
            negated: false,
            members: $members
        );
        
        return new Pattern($charClassNode);
    }
    
    /**
     * Concatenate multiple patterns into a single sequential pattern.
     * 
     * @param Pattern ...$patterns One or more patterns to concatenate
     * @return Pattern A Pattern object representing the sequence
     */
    public static function merge(Pattern ...$patterns): Pattern
    {
        $nodes = array_map(fn($p) => $p->getNode(), $patterns);
        $sequenceNode = new Nodes\Sequence(parts: $nodes);
        
        return new Pattern($sequenceNode);
    }
    
    /**
     * Create a capturing group around the provided pattern.
     * 
     * @param Pattern $pattern The pattern to capture
     * @return Pattern A Pattern object representing the capture group
     */
    public static function capture(Pattern $pattern): Pattern
    {
        $groupNode = new Nodes\Group(
            capturing: true,
            body: $pattern->getNode()
        );
        
        return new Pattern($groupNode);
    }
    
    /**
     * Make the provided pattern optional (matches 0 or 1 times).
     * 
     * @param Pattern $pattern The pattern to make optional
     * @return Pattern A Pattern object representing the optional pattern
     */
    public static function may(Pattern $pattern): Pattern
    {
        $quantifierNode = new Nodes\Quantifier(
            target: $pattern->getNode(),
            min: 0,
            max: 1,
            greedy: true,
            lazy: false,
            possessive: false
        );
        
        return new Pattern($quantifierNode);
    }
    
    /**
     * Match the start of a line.
     * 
     * @return Pattern A Pattern object representing the start anchor
     */
    public static function start(): Pattern
    {
        $anchorNode = new Nodes\Anchor(at: 'Start');
        return new Pattern($anchorNode);
    }
    
    /**
     * Match the end of a line.
     * 
     * @return Pattern A Pattern object representing the end anchor
     */
    public static function end(): Pattern
    {
        $anchorNode = new Nodes\Anchor(at: 'End');
        return new Pattern($anchorNode);
    }
}

/**
 * Pattern - Wrapper class for AST nodes
 * 
 * Represents a regex pattern that can be compiled to a regex string.
 * Wraps an internal AST node and provides compilation interface.
 */
class Pattern
{
    private Nodes\Node $node;
    
    /**
     * Create a new Pattern wrapping the given AST node.
     * 
     * @param Nodes\Node $node The AST node to wrap
     */
    public function __construct(Nodes\Node $node)
    {
        $this->node = $node;
    }
    
    /**
     * Get the underlying AST node.
     * 
     * @return Nodes\Node The wrapped AST node
     */
    public function getNode(): Nodes\Node
    {
        return $this->node;
    }
    
    /**
     * Apply repetition quantifier to this pattern.
     * 
     * This method matches the Python/TypeScript API convention where 0 represents
     * unlimited repetition. For example, rep(1, 0) means "one or more".
     * 
     * @param int $minRep Minimum number of repetitions
     * @param int|null $maxRep Maximum repetitions (null = exactly $minRep, 0 = unlimited)
     * @return Pattern A new Pattern with quantifier applied
     */
    public function rep(int $minRep, ?int $maxRep = null): Pattern
    {
        // Handle unlimited repetition (0 means unlimited, matching Python/TS convention)
        if ($maxRep === 0) {
            $max = 'inf';
        } else {
            // If maxRep is null, match exactly minRep times
            $max = $maxRep ?? $minRep;
        }
        
        $quantifierNode = new Nodes\Quantifier(
            target: $this->node,
            min: $minRep,
            max: $max,
            greedy: true,
            lazy: false,
            possessive: false
        );
        
        return new Pattern($quantifierNode);
    }
    
    /**
     * Compile this pattern to an intermediate representation (IR).
     * 
     * This compiles the pattern's AST node through the compiler pipeline
     * and returns the JSON-encoded IR for demonstration purposes.
     * In production, an emitter would convert the IR to a final regex string.
     * 
     * @return string JSON-encoded IR representation
     */
    public function compile(): string
    {
        $compiler = new Compiler();
        $ir = $compiler->compile($this->node);
        return json_encode($ir, JSON_PRETTY_PRINT);
    }
}
