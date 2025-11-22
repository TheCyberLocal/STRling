using System;
using System.Collections.Generic;
using System.Linq;

namespace Strling.Core;

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

            if (!inPattern && (stripped == "" || stripped.StartsWith("#")))
            {
                continue;
            }

            if (!inPattern && stripped.StartsWith("%flags"))
            {
                var idx = line.IndexOf("%flags");
                var after = line.Substring(idx + "%flags".Length);

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

                var remainder = after.Trim();
                if (remainder.Length > 0 && !remainder.All(c => " ,\t[]imsuxIMSUX".Contains(c)))
                {
                    inPattern = true;
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
                continue;
            }

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

    public Node ParsePattern()
    {
        _cur.SkipWsAndComments();
        if (_cur.Eof())
        {
            return new Lit("");
        }

        var node = ParseAlt();
        _cur.SkipWsAndComments();

        if (!_cur.Eof())
        {
            RaiseError("Unexpected trailing input", _cur.I);
        }

        return node;
    }

    private Node ParseAlt()
    {
        var branches = new List<Node>();
        branches.Add(ParseSeq());

        while (_cur.Peek() == '|')
        {
            _cur.Take();
            _cur.SkipWsAndComments();
            branches.Add(ParseSeq());
        }

        return branches.Count == 1 ? branches[0] : new Alt(branches);
    }

    private Node ParseSeq()
    {
        var parts = new List<Node>();
        var prevHadFailedQuant = false;

        while (!_cur.Eof())
        {
            _cur.SkipWsAndComments();
            var ch = _cur.Peek();

            if (ch != '\0' && "*+?{".Contains(ch) && parts.Count == 0)
            {
                RaiseError($"Invalid quantifier '{ch}'", _cur.I);
            }

            if (ch == '|' || ch == ')' || ch == '\0')
            {
                break;
            }

            var atom = ParseAtom();
            var (quantified, hadFailedQuant) = ParseQuantIfAny(atom);

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
                parts[^1] = new Lit(lastLit.Value + currentLit.Value);
            }

            if (!shouldCoalesce)
            {
                parts.Add(quantified);
            }

            prevHadFailedQuant = hadFailedQuant;
        }

        if (parts.Count == 0)
        {
            return new Lit("");
        }
        return parts.Count == 1 ? parts[0] : new Seq(parts);
    }

    private static bool ContainsNewline(string s) => s.Contains('\n');

    private Node ParseAtom()
    {
        _cur.SkipWsAndComments();
        var ch = _cur.Peek();

        switch (ch)
        {
            case '^':
                _cur.Take();
                return new Anchor("Start");

            case '$':
                _cur.Take();
                return new Anchor("End");

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
                return new Lit("");

            default:
                return TakeLiteralChar();
        }
    }

    private Node ParseEscapeAtom()
    {
        var startPos = _cur.I;
        _cur.Take();

        if (_cur.Eof())
        {
            RaiseError("Unexpected end of pattern after '\\'", startPos);
        }

        var ch = _cur.Take();

        switch (ch)
        {
            case 'b': return new Anchor("WordBoundary");
            case 'B': return new Anchor("NotWordBoundary");
            case 'A': return new Anchor("AbsoluteStart");
            case 'Z': return new Anchor("EndBeforeFinalNewline");

            case 'd': return new CharClass(false, new List<ClassItem> { new ClassEscape("digit") });
            case 'D': return new CharClass(false, new List<ClassItem> { new ClassEscape("not-digit") });
            case 'w': return new CharClass(false, new List<ClassItem> { new ClassEscape("word") });
            case 'W': return new CharClass(false, new List<ClassItem> { new ClassEscape("not-word") });
            case 's': return new CharClass(false, new List<ClassItem> { new ClassEscape("whitespace") });
            case 'S': return new CharClass(false, new List<ClassItem> { new ClassEscape("not-whitespace") });

            case 'n': return new Lit(ControlEscapes['n']);
            case 'r': return new Lit(ControlEscapes['r']);
            case 't': return new Lit(ControlEscapes['t']);
            case 'f': return new Lit(ControlEscapes['f']);
            case 'v': return new Lit(ControlEscapes['v']);

            default:
                if ("^$.*+?()[]{}|\\".Contains(ch))
                {
                    return new Lit(ch.ToString());
                }
                RaiseError($"Unknown escape sequence \\{ch}", startPos);
                return new Lit("");
        }
    }

    private Node ParseGroupOrLook()
    {
        var startPos = _cur.I;
        _cur.Take();
        _cur.SkipWsAndComments();

        if (_cur.Peek() == '?')
        {
            _cur.Take();
            var next = _cur.Peek();

            switch (next)
            {
                case ':':
                    _cur.Take();
                    var body = ParseAlt();
                    if (_cur.Peek() != ')') RaiseError("Unterminated group", startPos);
                    _cur.Take();
                    return new Group(false, body, null, false);

                case '=':
                    _cur.Take();
                    body = ParseAlt();
                    if (_cur.Peek() != ')') RaiseError("Unterminated lookahead", startPos);
                    _cur.Take();
                    return new Lookahead(body);

                case '!':
                    _cur.Take();
                    body = ParseAlt();
                    if (_cur.Peek() != ')') RaiseError("Unterminated lookahead", startPos);
                    _cur.Take();
                    return new NegativeLookahead(body);

                case '<':
                    _cur.Take();
                    var afterAngle = _cur.Peek();
                    if (afterAngle == '=')
                    {
                        _cur.Take();
                        body = ParseAlt();
                        if (_cur.Peek() != ')') RaiseError("Unterminated lookbehind", startPos);
                        _cur.Take();
                        return new Lookbehind(body);
                    }
                    else if (afterAngle == '!')
                    {
                        _cur.Take();
                        body = ParseAlt();
                        if (_cur.Peek() != ')') RaiseError("Unterminated lookbehind", startPos);
                        _cur.Take();
                        return new NegativeLookbehind(body);
                    }
                    else
                    {
                        var name = ReadIdentUntil('>');
                        if (_cur.Peek() != '>') RaiseError("Unterminated group name", startPos);
                        _cur.Take();
                        _capCount++;
                        _capNames.Add(name);
                        body = ParseAlt();
                        if (_cur.Peek() != ')') RaiseError("Unterminated group", startPos);
                        _cur.Take();
                        return new Group(true, body, name, false);
                    }

                case '>':
                    _cur.Take();
                    body = ParseAlt();
                    if (_cur.Peek() != ')') RaiseError("Unterminated atomic group", startPos);
                    _cur.Take();
                    return new Group(false, body, null, true);

                default:
                    RaiseError($"Unknown group type '(?{next}'", startPos);
                    return new Lit("");
            }
        }
        else
        {
            _capCount++;
            var body = ParseAlt();
            if (_cur.Peek() != ')') RaiseError("Unterminated group", startPos);
            _cur.Take();
            return new Group(true, body, null, false);
        }
    }

    private CharClass ParseCharClass()
    {
        var startPos = _cur.I;
        _cur.Take();
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
        _cur.Take();

        return new CharClass(negated, items);
    }

    private ClassItem ReadClassItem()
    {
        var ch = _cur.Peek();

        if (ch == '\\')
        {
            _cur.Take();
            var escCh = _cur.Take();

            switch (escCh)
            {
                case 'd': return new ClassEscape("digit");
                case 'D': return new ClassEscape("not-digit");
                case 'w': return new ClassEscape("word");
                case 'W': return new ClassEscape("not-word");
                case 's': return new ClassEscape("whitespace");
                case 'S': return new ClassEscape("not-whitespace");

                case 'n': return new ClassLiteral("\n");
                case 'r': return new ClassLiteral("\r");
                case 't': return new ClassLiteral("\t");

                default:
                    return new ClassLiteral(escCh.ToString());
            }
        }
        else
        {
            var literal = _cur.Take().ToString();

            if (_cur.Peek() == '-' && _cur.Peek(1) != ']')
            {
                _cur.Take();
                var endCh = _cur.Take().ToString();
                return new ClassRange(literal, endCh);
            }

            return new ClassLiteral(literal);
        }
    }

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
        int? max = null;
        var greedy = true;
        var lazy = false;
        var possessive = false;

        switch (ch)
        {
            case '*':
                _cur.Take();
                min = 0;
                max = null;
                break;

            case '+':
                _cur.Take();
                min = 1;
                max = null;
                break;

            case '?':
                _cur.Take();
                min = 0;
                max = 1;
                break;

            case '{':
                var (minVal, maxVal) = ParseBraceQuant();
                if (minVal == null) return (child, false);
                min = minVal.Value;
                max = maxVal;
                break;

            default:
                return (child, false);
        }

        if (_cur.Peek() == '?')
        {
            _cur.Take();
            greedy = false;
            lazy = true;
        }
        else if (_cur.Peek() == '+')
        {
            _cur.Take();
            greedy = false;
            possessive = true;
        }

        return (new Quant(child, min, max, greedy, lazy, possessive), true);
    }

    private (int?, int?) ParseBraceQuant()
    {
        var startPos = _cur.I;
        _cur.Take();
        _cur.SkipWsAndComments();

        var minStr = "";
        while (char.IsDigit(_cur.Peek()))
        {
            minStr += _cur.Take();
        }

        if (minStr == "")
        {
            RaiseError("Invalid brace quantifier content", startPos);
            return (null, null);
        }

        var min = int.Parse(minStr);
        int? max = min;

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

            max = maxStr == "" ? null : int.Parse(maxStr);
        }

        _cur.SkipWsAndComments();
        if (_cur.Peek() != '}')
        {
            RaiseError("Unterminated {m,n}", startPos);
        }
        _cur.Take();

        return (min, max);
    }

    private Lit TakeLiteralChar()
    {
        var ch = _cur.Take();
        return new Lit(ch.ToString());
    }

    private string ReadIdentUntil(char end)
    {
        var ident = "";
        while (!_cur.Eof() && _cur.Peek() != end)
        {
            ident += _cur.Take();
        }
        return ident;
    }

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
