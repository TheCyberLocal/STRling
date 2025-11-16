namespace Strling.Core;

/// <summary>
/// STRling Parser - Recursive Descent Parser for STRling DSL
/// 
/// This module implements a hand-rolled recursive-descent parser that transforms
/// STRling pattern syntax into Abstract Syntax Tree (AST) nodes. The parser handles:
///   - Alternation and sequencing
///   - Character classes and ranges
///   - Quantifiers (greedy, lazy, possessive)
///   - Groups (capturing, non-capturing, named, atomic)
///   - Lookarounds (lookahead and lookbehind, positive and negative)
///   - Anchors and special escapes
///   - Extended/free-spacing mode with comments
/// 
/// The parser produces AST nodes (defined in Nodes.cs) that can be compiled
/// to IR and ultimately emitted as target-specific regex patterns. It includes
/// comprehensive error handling with position tracking for helpful diagnostics.
/// </summary>
public class Parser
{
    private readonly string _originalText;
    private readonly Cursor _cur;
    private readonly Flags _flags;
    private readonly string _src;
    private int _capCount;
    private readonly HashSet<string> _capNames;
    
    private static readonly Dictionary<char, string> ControlEscapes = new()
    {
        ['n'] = "\n",
        ['r'] = "\r",
        ['t'] = "\t",
        ['f'] = "\f",
        ['v'] = "\v"
    };

    /// <summary>
    /// Initialize a new Parser instance.
    /// </summary>
    /// <param name="text">The STRling pattern text to parse</param>
    public Parser(string text)
    {
        _originalText = text;
        var (flags, src) = ParseDirectives(text);
        _flags = flags;
        _src = src;
        _cur = new Cursor(src, 0, flags.Extended, 0);
        _capCount = 0;
        _capNames = new HashSet<string>();
    }

    /// <summary>
    /// Static entry point for parsing a STRling pattern.
    /// </summary>
    /// <param name="src">The STRling pattern text to parse</param>
    /// <returns>A tuple of (Flags, AST root node)</returns>
    public static (Flags, Node) Parse(string src)
    {
        var parser = new Parser(src);
        var ast = parser.ParsePattern();
        return (parser._flags, ast);
    }

    private void RaiseError(string message, int pos)
    {
        var hint = HintEngine.GetHint(message, _src, pos);
        throw new STRlingParseError(message, pos, _src, hint);
    }

    /// <summary>
    /// Parse directives (like %flags) from the input text.
    /// </summary>
    private (Flags, string) ParseDirectives(string text)
    {
        var flags = new Flags();
        var lines = text.Split('\n');
        var patternLines = new List<string>();
        var inPattern = false;
        var lineNum = 0;

        foreach (var rawLine in lines)
        {
            lineNum++;
            var line = rawLine.TrimEnd('\r');
            var stripped = line.Trim();
            
            // Skip leading blank lines or comments
            if (!inPattern && (stripped == "" || stripped.StartsWith("#")))
            {
                continue;
            }
            
            // Process directives only before pattern content
            if (!inPattern && stripped.StartsWith("%flags"))
            {
                var idx = line.IndexOf("%flags");
                var after = line.Substring(idx + "%flags".Length);
                
                // Extract flag letters
                var letters = System.Text.RegularExpressions.Regex.Replace(after, @"[,\[\]\s]+", " ").Trim().ToLower();
                var validFlags = new HashSet<char> { 'i', 'm', 's', 'u', 'x' };
                
                foreach (var ch in letters.Replace(" ", ""))
                {
                    if (ch != '\0' && !validFlags.Contains(ch))
                    {
                        var pos = lines.Take(lineNum - 1).Sum(l => l.Length + 1) + idx;
                        var hint = HintEngine.GetHint($"Invalid flag '{ch}'", _originalText, pos);
                        throw new STRlingParseError($"Invalid flag '{ch}'", pos, _originalText, hint);
                    }
                }
                
                flags = Flags.FromLetters(letters);
                
                // Check if there's pattern content on the same line
                var remainder = after.Trim();
                if (remainder.Length > 0 && !remainder.All(c => " ,\t[]imsuxIMSUX".Contains(c)))
                {
                    inPattern = true;
                    // Find where pattern actually starts
                    var patternStart = after.TakeWhile(c => " ,\t[]imsuxIMSUX".Contains(c)).Count();
                    if (patternStart < after.Length)
                    {
                        patternLines.Add(after.Substring(patternStart));
                    }
                }
                continue;
            }
            
            if (!inPattern && stripped.StartsWith("%"))
            {
                continue; // Skip other directives
            }
            
            // This is pattern content
            if (line.Contains("%flags"))
            {
                var pos = lines.Take(lineNum - 1).Sum(l => l.Length + 1) + line.IndexOf("%flags");
                var hint = HintEngine.GetHint("Directive after pattern content", _originalText, pos);
                throw new STRlingParseError("Directive after pattern content", pos, _originalText, hint);
            }
            
            inPattern = true;
            patternLines.Add(line);
        }

        var pattern = string.Join("\n", patternLines);
        return (flags, pattern);
    }

    /// <summary>
    /// Parse the entire STRling pattern into an AST.
    /// </summary>
    public Node ParsePattern()
    {
        _cur.SkipWsAndComments();
        if (_cur.Eof())
        {
            // Empty pattern
            return new Lit { Value = "" };
        }

        var node = ParseAlt();
        _cur.SkipWsAndComments();
        
        if (!_cur.Eof())
        {
            RaiseError("Unexpected trailing input", _cur.I);
        }

        return node;
    }

    /// <summary>
    /// Parse alternation (|).
    /// </summary>
    private Node ParseAlt()
    {
        var branches = new List<Node>();
        branches.Add(ParseSeq());

        while (_cur.Peek() == '|')
        {
            _cur.Take(); // consume |
            _cur.SkipWsAndComments();
            branches.Add(ParseSeq());
        }

        return branches.Count == 1 ? branches[0] : new Alt { Branches = branches };
    }

    /// <summary>
    /// Parse a sequence of atoms.
    /// </summary>
    private Node ParseSeq()
    {
        var parts = new List<Node>();
        var prevHadFailedQuant = false;
        
        while (!_cur.Eof())
        {
            _cur.SkipWsAndComments();
            var ch = _cur.Peek();
            
            // Invalid quantifier at start of sequence/group (no previous atom)
            if (ch != '\0' && "*+?{".Contains(ch) && parts.Count == 0)
            {
                RaiseError($"Invalid quantifier '{ch}'", _cur.I);
            }
            
            // Stop at sequence terminators
            if (ch == '|' || ch == ')' || ch == '\0')
            {
                break;
            }

            var atom = ParseAtom();
            var (quantified, hadFailedQuant) = ParseQuantIfAny(atom);
            
            // Coalesce adjacent Lit nodes
            bool shouldCoalesce = false;
            if (quantified is Lit currentLit
                && parts.Count > 0
                && parts[^1] is Lit lastLit
                && !_cur.ExtendedMode
                && !prevHadFailedQuant
                && !ContainsNewline(currentLit.Value)
                && !ContainsNewline(lastLit.Value)
                && !(parts[^1] is Backref))
            {
                shouldCoalesce = true;
                parts[^1] = new Lit { Value = lastLit.Value + currentLit.Value };
            }
            
            if (!shouldCoalesce)
            {
                parts.Add(quantified);
            }
            
            prevHadFailedQuant = hadFailedQuant;
        }

        if (parts.Count == 0)
        {
            return new Lit { Value = "" };
        }
        return parts.Count == 1 ? parts[0] : new Seq { Parts = parts };
    }
    
    private static bool ContainsNewline(string s) => s.Contains('\n');

    /// <summary>
    /// Parse a single atom (literal, group, anchor, char class, etc.).
    /// </summary>
    private Node ParseAtom()
    {
        _cur.SkipWsAndComments();
        var ch = _cur.Peek();

        switch (ch)
        {
            case '^':
                _cur.Take();
                return new Anchor { At = "Start" };
            
            case '$':
                _cur.Take();
                return new Anchor { At = "End" };
            
            case '.':
                _cur.Take();
                return new Dot();
            
            case '\\':
                return ParseEscapeAtom();
            
            case '(':
                return ParseGroupOrLook();
            
            case '[':
                return ParseCharClass();
            
            case ')':
            case ']':
            case '|':
            case '*':
            case '+':
            case '?':
            case '{':
                RaiseError($"Unexpected token '{ch}'", _cur.I);
                return new Lit { Value = "" }; // unreachable
            
            default:
                return TakeLiteralChar();
        }
    }

    /// <summary>
    /// Parse an escape sequence (\d, \w, \b, etc.).
    /// </summary>
    private Node ParseEscapeAtom()
    {
        var startPos = _cur.I;
        _cur.Take(); // consume \
        
        if (_cur.Eof())
        {
            RaiseError("Unexpected end of pattern after '\\'", startPos);
        }

        var ch = _cur.Take();
        
        switch (ch)
        {
            // Anchors
            case 'b':
                return new Anchor { At = "WordBoundary" };
            case 'B':
                return new Anchor { At = "NotWordBoundary" };
            case 'A':
                return new Anchor { At = "AbsoluteStart" };
            case 'Z':
                return new Anchor { At = "EndBeforeFinalNewline" };
            
            // Character class escapes
            case 'd':
            case 'D':
            case 'w':
            case 'W':
            case 's':
            case 'S':
                return new CharClass
                {
                    Negated = false,
                    Items = new List<ClassItem>
                    {
                        new ClassEscape { Type = ch.ToString() }
                    }
                };
            
            // Control escapes
            case 'n':
            case 'r':
            case 't':
            case 'f':
            case 'v':
                return new Lit { Value = ControlEscapes[ch] };
            
            // Literal escape
            default:
                if ("^$.*+?()[]{}|\\".Contains(ch))
                {
                    return new Lit { Value = ch.ToString() };
                }
                RaiseError($"Unknown escape sequence \\{ch}", startPos);
                return new Lit { Value = "" }; // unreachable
        }
    }

    /// <summary>
    /// Parse a group or lookaround.
    /// </summary>
    private Node ParseGroupOrLook()
    {
        var startPos = _cur.I;
        _cur.Take(); // consume (
        _cur.SkipWsAndComments();

        if (_cur.Peek() == '?')
        {
            _cur.Take(); // consume ?
            var next = _cur.Peek();

            switch (next)
            {
                case ':': // Non-capturing group
                    _cur.Take();
                    var body = ParseAlt();
                    if (_cur.Peek() != ')')
                    {
                        RaiseError("Unterminated group", startPos);
                    }
                    _cur.Take();
                    return new Group { Capturing = false, Body = body };
                
                case '=': // Positive lookahead
                    _cur.Take();
                    body = ParseAlt();
                    if (_cur.Peek() != ')')
                    {
                        RaiseError("Unterminated lookahead", startPos);
                    }
                    _cur.Take();
                    return new Look { Dir = "Ahead", Neg = false, Body = body };
                
                case '!': // Negative lookahead
                    _cur.Take();
                    body = ParseAlt();
                    if (_cur.Peek() != ')')
                    {
                        RaiseError("Unterminated lookahead", startPos);
                    }
                    _cur.Take();
                    return new Look { Dir = "Ahead", Neg = true, Body = body };
                
                case '<': // Lookbehind or named group
                    _cur.Take();
                    var afterAngle = _cur.Peek();
                    if (afterAngle == '=') // Positive lookbehind
                    {
                        _cur.Take();
                        body = ParseAlt();
                        if (_cur.Peek() != ')')
                        {
                            RaiseError("Unterminated lookbehind", startPos);
                        }
                        _cur.Take();
                        return new Look { Dir = "Behind", Neg = false, Body = body };
                    }
                    else if (afterAngle == '!') // Negative lookbehind
                    {
                        _cur.Take();
                        body = ParseAlt();
                        if (_cur.Peek() != ')')
                        {
                            RaiseError("Unterminated lookbehind", startPos);
                        }
                        _cur.Take();
                        return new Look { Dir = "Behind", Neg = true, Body = body };
                    }
                    else // Named group (?<name>...)
                    {
                        var name = ReadIdentUntil('>');
                        if (_cur.Peek() != '>')
                        {
                            RaiseError("Unterminated group name", startPos);
                        }
                        _cur.Take();
                        _capCount++;
                        _capNames.Add(name);
                        body = ParseAlt();
                        if (_cur.Peek() != ')')
                        {
                            RaiseError("Unterminated group", startPos);
                        }
                        _cur.Take();
                        return new Group { Capturing = true, Name = name, Body = body };
                    }
                
                case '>': // Atomic group
                    _cur.Take();
                    body = ParseAlt();
                    if (_cur.Peek() != ')')
                    {
                        RaiseError("Unterminated atomic group", startPos);
                    }
                    _cur.Take();
                    return new Group { Capturing = false, Atomic = true, Body = body };
                
                default:
                    RaiseError($"Unknown group type '(?{next}'", startPos);
                    return new Lit { Value = "" }; // unreachable
            }
        }
        else
        {
            // Capturing group
            _capCount++;
            var body = ParseAlt();
            if (_cur.Peek() != ')')
            {
                RaiseError("Unterminated group", startPos);
            }
            _cur.Take();
            return new Group { Capturing = true, Body = body };
        }
    }

    /// <summary>
    /// Parse a character class [a-z].
    /// </summary>
    private CharClass ParseCharClass()
    {
        var startPos = _cur.I;
        _cur.Take(); // consume [
        _cur.InClass++;
        
        var negated = false;
        if (_cur.Peek() == '^')
        {
            negated = true;
            _cur.Take();
        }

        var items = new List<ClassItem>();
        
        while (!_cur.Eof() && _cur.Peek() != ']')
        {
            items.Add(ReadClassItem());
        }

        if (_cur.Peek() != ']')
        {
            RaiseError("Unterminated character class", startPos);
        }
        
        _cur.InClass--;
        _cur.Take(); // consume ]

        return new CharClass { Negated = negated, Items = items };
    }

    /// <summary>
    /// Read a single character class item (literal, range, or escape).
    /// </summary>
    private ClassItem ReadClassItem()
    {
        var ch = _cur.Peek();
        
        if (ch == '\\')
        {
            _cur.Take();
            var escCh = _cur.Take();
            
            switch (escCh)
            {
                case 'd':
                case 'D':
                case 'w':
                case 'W':
                case 's':
                case 'S':
                    return new ClassEscape { Type = escCh.ToString() };
                
                case 'n':
                    return new ClassLiteral { Ch = "\n" };
                case 'r':
                    return new ClassLiteral { Ch = "\r" };
                case 't':
                    return new ClassLiteral { Ch = "\t" };
                
                default:
                    return new ClassLiteral { Ch = escCh.ToString() };
            }
        }
        else
        {
            var literal = _cur.Take().ToString();
            
            // Check for range
            if (_cur.Peek() == '-' && _cur.Peek(1) != ']')
            {
                _cur.Take(); // consume -
                var endCh = _cur.Take().ToString();
                return new ClassRange { FromCh = literal, ToCh = endCh };
            }
            
            return new ClassLiteral { Ch = literal };
        }
    }

    /// <summary>
    /// Parse quantifiers (* + ? {n,m}).
    /// </summary>
    private (Node, bool) ParseQuantIfAny(Node child)
    {
        _cur.SkipWsAndComments();
        var ch = _cur.Peek();
        
        if (child is Anchor)
        {
            if ("*+?{".Contains(ch))
            {
                RaiseError("Cannot quantify anchor", _cur.I);
            }
            return (child, false);
        }

        var min = 0;
        object max = "Inf";
        var mode = "Greedy";

        switch (ch)
        {
            case '*':
                _cur.Take();
                min = 0;
                max = "Inf";
                break;
            
            case '+':
                _cur.Take();
                min = 1;
                max = "Inf";
                break;
            
            case '?':
                _cur.Take();
                min = 0;
                max = 1;
                break;
            
            case '{':
                // Parse {n,m}
                var (minVal, maxVal, modeVal) = ParseBraceQuant();
                if (minVal == null) return (child, false);
                min = minVal.Value;
                max = maxVal ?? (object)"Inf";
                mode = modeVal;
                break;
            
            default:
                return (child, false);
        }

        // Check for mode modifiers (?, +)
        if (_cur.Peek() == '?')
        {
            _cur.Take();
            mode = "Lazy";
        }
        else if (_cur.Peek() == '+')
        {
            _cur.Take();
            mode = "Possessive";
        }

        return (new Quant { Child = child, Min = min, Max = max, Mode = mode }, true);
    }

    /// <summary>
    /// Parse a brace quantifier {n,m}.
    /// </summary>
    private (int?, object?, string) ParseBraceQuant()
    {
        var startPos = _cur.I;
        _cur.Take(); // consume {
        _cur.SkipWsAndComments();

        var minStr = "";
        while (char.IsDigit(_cur.Peek()))
        {
            minStr += _cur.Take();
        }

        if (minStr == "")
        {
            RaiseError("Invalid brace quantifier content", startPos);
            return (null, null, "Greedy");
        }

        var min = int.Parse(minStr);
        object? max = min;

        _cur.SkipWsAndComments();
        if (_cur.Peek() == ',')
        {
            _cur.Take();
            _cur.SkipWsAndComments();
            
            var maxStr = "";
            while (char.IsDigit(_cur.Peek()))
            {
                maxStr += _cur.Take();
            }
            
            max = maxStr == "" ? (object)"Inf" : int.Parse(maxStr);
        }

        _cur.SkipWsAndComments();
        if (_cur.Peek() != '}')
        {
            RaiseError("Unterminated {m,n}", startPos);
        }
        _cur.Take();

        return (min, max, "Greedy");
    }

    /// <summary>
    /// Take a literal character.
    /// </summary>
    private Lit TakeLiteralChar()
    {
        var ch = _cur.Take();
        return new Lit { Value = ch.ToString() };
    }

    /// <summary>
    /// Read an identifier until the specified end character.
    /// </summary>
    private string ReadIdentUntil(char end)
    {
        var ident = "";
        while (!_cur.Eof() && _cur.Peek() != end)
        {
            ident += _cur.Take();
        }
        return ident;
    }

    /// <summary>
    /// Cursor class for tracking position in the input.
    /// </summary>
    private class Cursor
    {
        public string Text { get; }
        public int I { get; set; }
        public bool ExtendedMode { get; }
        public int InClass { get; set; }

        public Cursor(string text, int i, bool extendedMode, int inClass)
        {
            Text = text;
            I = i;
            ExtendedMode = extendedMode;
            InClass = inClass;
        }

        public bool Eof() => I >= Text.Length;

        public char Peek(int n = 0)
        {
            var j = I + n;
            return j >= Text.Length ? '\0' : Text[j];
        }

        public char Take()
        {
            if (Eof()) return '\0';
            var ch = Text[I];
            I++;
            return ch;
        }

        public bool Match(string s)
        {
            if (Text.Substring(I).StartsWith(s))
            {
                I += s.Length;
                return true;
            }
            return false;
        }

        public void SkipWsAndComments()
        {
            if (!ExtendedMode || InClass > 0) return;
            
            while (!Eof())
            {
                var ch = Peek();
                if (" \t\r\n".Contains(ch))
                {
                    I++;
                    continue;
                }
                if (ch == '#')
                {
                    // skip comment to end of line
                    while (!Eof() && !"\r\n".Contains(Peek()))
                    {
                        I++;
                    }
                    continue;
                }
                break;
            }
        }
    }
}
