<?php

declare(strict_types=1);

namespace STRling\Emitters;

use STRling\Core\Nodes\{
    Node, Alternation, Sequence, Literal, Dot, Anchor, CharacterClass, Quantifier, Group, Backreference,
    Lookahead, NegativeLookahead, Lookbehind, NegativeLookbehind,
    ClassItem, Escape, Range, Flags
};
use STRling\Core\CompileResult;
use STRling\Core\STRlingCompilationError;
use STRling\Core\STRlingWarning;

/**
 * STRling PCRE2 Emitter - IR to PCRE2 Pattern String
 *
 * Transforms STRling AST nodes into PCRE2-compatible regex pattern strings.
 */
class Pcre2Emitter
{
    /**
     * Default upper bound on AST/IR nesting depth before the emitter
     * aborts. Mirrors the SSOT in the TypeScript reference and the
     * matching constants in every other binding.
     */
    public const DEFAULT_MAX_DEPTH = 250;

    private const REDOS_MESSAGE =
        'The pattern contains overlapping alternations or nested unbounded '
      . 'quantifiers (e.g., (a+)+). This can lead to catastrophic backtracking '
      . 'and exponential CPU spikes. Consider using possessive quantifiers '
      . '(++ or *+) or atomic groups to guarantee execution safety.';

    /**
     * Emit a PCRE2 pattern string from an AST node.
     */
    public static function emit(Node $node, ?Flags $flags = null): string
    {
        return self::emitWithDiagnostics($node, $flags, 0)->pattern;
    }

    /**
     * Emit a PCRE2 pattern string from an AST node and surface any
     * non-fatal diagnostics collected during emission. Pass
     * `$maxDepth <= 0` to use {@see self::DEFAULT_MAX_DEPTH}.
     */
    public static function emitWithDiagnostics(Node $node, ?Flags $flags = null, int $maxDepth = 0): CompileResult
    {
        $prefix = $flags ? self::emitFlagsPrefix($flags) : '';
        $ctx = self::newContext($maxDepth);
        $body = self::emitNode($node, '', $ctx);
        return new CompileResult($prefix . $body, $ctx['warnings']);
    }

    /**
     * @return array{depth:int, maxDepth:int, inLookbehind:bool, warnings:list<STRlingWarning>}
     */
    private static function newContext(int $maxDepth): array
    {
        return [
            'depth' => 0,
            'maxDepth' => $maxDepth > 0 ? $maxDepth : self::DEFAULT_MAX_DEPTH,
            'inLookbehind' => false,
            'warnings' => [],
        ];
    }

    /** True iff a quantifier has an unbounded upper bound. */
    private static function isUnboundedQuant(Quantifier $q): bool
    {
        // null in the user-facing AST means unbounded; 'inf' is also accepted.
        return $q->max === null || (is_string($q->max) && strtolower($q->max) === 'inf');
    }

    /** True iff a quantifier matches a variable number of characters. */
    private static function isVariableLengthQuant(Quantifier $q): bool
    {
        if (self::isUnboundedQuant($q)) {
            return true;
        }
        return $q->max !== $q->min;
    }

    /**
     * Mirror of `_isFixedLengthBody` in the TS SSOT. Returns true when
     * the node consumes a fixed number of characters and is therefore
     * safe inside a PCRE2 lookbehind.
     */
    private static function isFixedLengthBody(Node $node): bool
    {
        if ($node instanceof Quantifier) {
            return !self::isVariableLengthQuant($node) && self::isFixedLengthBody($node->target);
        }
        if ($node instanceof Sequence) {
            foreach ($node->parts as $p) {
                if (!self::isFixedLengthBody($p)) return false;
            }
            return true;
        }
        if ($node instanceof Alternation) {
            foreach ($node->alternatives as $b) {
                if (!self::isFixedLengthBody($b)) return false;
            }
            return true;
        }
        if ($node instanceof Group) {
            return self::isFixedLengthBody($node->body);
        }
        if ($node instanceof Lookahead || $node instanceof NegativeLookahead
            || $node instanceof Lookbehind || $node instanceof NegativeLookbehind) {
            return true; // zero-width
        }
        return true;
    }

    /**
     * Mirror of `_hasNestedUnboundedQuant` in the TS SSOT. Detects an
     * unbounded quantifier reachable via single-child wrappers or any
     * branch of an Alternation.
     */
    private static function hasNestedUnboundedQuant(Node $child): bool
    {
        if ($child instanceof Quantifier) {
            return self::isUnboundedQuant($child);
        }
        if ($child instanceof Group) {
            return self::hasNestedUnboundedQuant($child->body);
        }
        if ($child instanceof Sequence) {
            return count($child->parts) === 1 && self::hasNestedUnboundedQuant($child->parts[0]);
        }
        if ($child instanceof Alternation) {
            foreach ($child->alternatives as $b) {
                if (self::hasNestedUnboundedQuant($b)) return true;
            }
            return false;
        }
        return false;
    }

    /** Append a single REDOS_RISK warning, deduplicated per pass. */
    private static function pushReDoSWarning(array &$ctx): void
    {
        foreach ($ctx['warnings'] as $w) {
            if ($w->code === 'REDOS_RISK') return;
        }
        $ctx['warnings'][] = new STRlingWarning('REDOS_RISK', self::REDOS_MESSAGE);
    }

    /**
     * Build the inline prefix form from flags, e.g. "(?imx)"
     */
    private static function emitFlagsPrefix(Flags $flags): string
    {
        $letters = '';
        if ($flags->ignoreCase) $letters .= 'i';
        if ($flags->multiline) $letters .= 'm';
        if ($flags->dotAll) $letters .= 's';
        if ($flags->unicode) $letters .= 'u';
        if ($flags->extended) $letters .= 'x';
        return $letters ? "(?{$letters})" : '';
    }

    private static function emitNode(Node $node, string $parentKind, array &$ctx): string
    {
        $ctx['depth'] += 1;
        try {
            if ($ctx['depth'] > $ctx['maxDepth']) {
                throw new STRlingCompilationError(
                    "Maximum AST depth exceeded (limit: {$ctx['maxDepth']}). "
                  . 'This pattern is too deeply nested and risks host stack '
                  . 'exhaustion during emission. Refactor the pattern to '
                  . 'reduce nesting, or flatten capturing groups where possible.',
                    'MAX_DEPTH'
                );
            }

            if ($node instanceof Literal) {
                return self::escapeLiteral($node->value);
            }

            if ($node instanceof Dot) {
                return '.';
            }

            if ($node instanceof Anchor) {
                return match ($node->at) {
                    'Start' => '^',
                    'End' => '$',
                    'WordBoundary' => '\\b',
                    'NotWordBoundary' => '\\B',
                    'AbsoluteStart' => '\\A',
                    'EndBeforeFinalNewline' => '\\Z',
                    'AbsoluteEnd' => '\\z',
                    default => '',
                };
            }

            if ($node instanceof Backreference) {
                if ($node->name !== null) {
                    return "\\k<{$node->name}>";
                }
                if ($node->index !== null) {
                    return "\\{$node->index}";
                }
                return '';
            }

            if ($node instanceof CharacterClass) {
                return self::emitClass($node);
            }

            if ($node instanceof Sequence) {
                $parts = array_map(fn($p) => self::emitNode($p, 'Seq', $ctx), $node->parts);
                return implode('', $parts);
            }

            if ($node instanceof Alternation) {
                $branches = array_map(fn($b) => self::emitNode($b, 'Alt', $ctx), $node->alternatives);
                $body = implode('|', $branches);
                return in_array($parentKind, ['Seq', 'Quant'], true) ? "(?:{$body})" : $body;
            }

            if ($node instanceof Quantifier) {
                // ReDoS guard: only flag when the *outer* quantifier is
                // itself unbounded (e.g. `(a+)+`). A bounded outer like
                // `(a+){0,3}` cannot produce exponential backtracking on
                // its own.
                if (self::isUnboundedQuant($node) && self::hasNestedUnboundedQuant($node->target)) {
                    self::pushReDoSWarning($ctx);
                }
                $childStr = self::emitNode($node->target, 'Quant', $ctx);
                if (self::needsGroupForQuant($node->target)) {
                    $childStr = "(?:{$childStr})";
                }
                return $childStr . self::emitQuantSuffix($node);
            }

            if ($node instanceof Group) {
                $open = self::emitGroupOpen($node);
                return $open . self::emitNode($node->body, 'Group', $ctx) . ')';
            }

            if ($node instanceof Lookahead) {
                return '(?=' . self::emitNode($node->body, 'Look', $ctx) . ')';
            }

            if ($node instanceof NegativeLookahead) {
                return '(?!' . self::emitNode($node->body, 'Look', $ctx) . ')';
            }

            if ($node instanceof Lookbehind || $node instanceof NegativeLookbehind) {
                // Variable-length lookbehind guard: PCRE2 mandates a
                // fixed-width lookbehind body. Detect the violation here
                // so the user sees a Signpost-pattern error rather than
                // an opaque PCRE2 compile failure leaking from the runtime.
                if (!self::isFixedLengthBody($node->body)) {
                    throw new STRlingCompilationError(
                        'PCRE2 does not support variable-length lookbehinds. '
                      . 'The lookbehind body contains a quantifier that makes '
                      . 'its length unpredictable. Rewrite the assertion using '
                      . 'a fixed-length range (e.g. `{1,8}` instead of `+`), '
                      . 'or restructure the pattern using a Lookahead, or '
                      . 'extract the quantified portion outside the assertion.',
                        'VLB_NOT_SUPPORTED'
                    );
                }
                $wasInLb = $ctx['inLookbehind'];
                $ctx['inLookbehind'] = true;
                try {
                    $op = $node instanceof NegativeLookbehind ? '(?<!' : '(?<=';
                    return $op . self::emitNode($node->body, 'Look', $ctx) . ')';
                } finally {
                    $ctx['inLookbehind'] = $wasInLb;
                }
            }

            throw new \RuntimeException('Emitter missing for ' . get_class($node));
        } finally {
            $ctx['depth'] -= 1;
        }
    }

    private static function escapeLiteral(string $s): string
    {
        $toEscape = [' ', '#', '$', '&', '(', ')', '*', '+', '-', '.', '?', '[', '\\', ']', '^', '{', '|', '}', '~'];
        $result = '';

        for ($i = 0; $i < strlen($s); $i++) {
            $ch = $s[$i];
            if (in_array($ch, $toEscape, true) && $ch !== '-') {
                $result .= '\\' . $ch;
            } else {
                $result .= $ch;
            }
        }

        return $result;
    }

    private static function escapeClassChar(string $ch): string
    {
        if ($ch === '\\' || $ch === ']') {
            return '\\' . $ch;
        }
        if ($ch === '-') {
            return '\\-';
        }
        if ($ch === '^') {
            return '\\^';
        }
        if ($ch === "\n") return '\\n';
        if ($ch === "\r") return '\\r';
        if ($ch === "\t") return '\\t';
        if ($ch === "\f") return '\\f';
        if ($ch === "\v") return '\\v';

        $code = ord($ch);
        if ($code < 32 || ($code >= 127 && $code <= 159)) {
            return sprintf('\\x%02x', $code);
        }

        return $ch;
    }

    private static function emitClass(CharacterClass $cc): string
    {
        $items = $cc->members;

        // Single-item shorthand optimization
        if (count($items) === 1 && $items[0] instanceof Escape) {
            $esc = $items[0];
            $k = match ($esc->kind) {
                'digit' => 'd',
                'not-digit' => 'D',
                'word' => 'w',
                'not-word' => 'W',
                'space' => 's',
                'not-space' => 'S',
                default => null,
            };

            if ($k !== null) {
                if (in_array($k, ['d', 'w', 's'], true)) {
                    if ($cc->negated) {
                        return '\\' . strtoupper($k);
                    }
                    return '\\' . $k;
                }
                if (in_array($k, ['D', 'W', 'S'], true)) {
                    $base = strtolower($k);
                    return $cc->negated ? '\\' . $base : '\\' . $k;
                }
            }
        }

        // General case: build bracket class
        $parts = [];
        foreach ($items as $item) {
            if ($item instanceof Literal) {
                $parts[] = self::escapeClassChar($item->value);
            } elseif ($item instanceof Range) {
                $parts[] = self::escapeClassChar($item->from) . '-' . self::escapeClassChar($item->to);
            } elseif ($item instanceof Escape) {
                $k = match ($item->kind) {
                    'digit' => 'd',
                    'not-digit' => 'D',
                    'word' => 'w',
                    'not-word' => 'W',
                    'space' => 's',
                    'not-space' => 'S',
                    'property' => 'p',
                    'not-property' => 'P',
                    default => null,
                };
                if ($k !== null) {
                    $parts[] = '\\' . $k;
                }
            }
        }

        $inner = implode('', $parts);
        return '[' . ($cc->negated ? '^' : '') . $inner . ']';
    }

    private static function emitQuantSuffix(Quantifier $q): string
    {
        $min = $q->min;
        $max = $q->max;

        if ($min === 0 && $max === null) {
            $suffix = '*';
        } elseif ($min === 1 && $max === null) {
            $suffix = '+';
        } elseif ($min === 0 && $max === 1) {
            $suffix = '?';
        } elseif ($min === $max) {
            $suffix = "{{$min}}";
        } elseif ($max === null) {
            $suffix = "{{$min},}";
        } else {
            $suffix = "{{$min},{$max}}";
        }

        if ($q->lazy) {
            $suffix .= '?';
        } elseif ($q->possessive) {
            $suffix .= '+';
        }

        return $suffix;
    }

    private static function needsGroupForQuant(Node $child): bool
    {
        if ($child instanceof CharacterClass || $child instanceof Dot ||
            $child instanceof Group || $child instanceof Backreference ||
            $child instanceof Anchor) {
            return false;
        }
        if ($child instanceof Literal) {
            return strlen($child->value) > 1;
        }
        if ($child instanceof Alternation) {
            return true;
        }
        if ($child instanceof Sequence) {
            return count($child->parts) > 1;
        }
        return false;
    }

    private static function emitGroupOpen(Group $group): string
    {
        if ($group->atomic === true) {
            return '(?>';
        }
        if ($group->capturing) {
            if ($group->name !== null) {
                return "(?<{$group->name}>";
            }
            return '(';
        }
        return '(?:';
    }
}
