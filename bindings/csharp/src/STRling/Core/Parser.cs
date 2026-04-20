using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;

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

        for (int lineNum = 0; lineNum < lines.Length; lineNum++)
        {
            var line = lines[lineNum].TrimEnd('\r');
            var stripped = line.Trim();

            if (!inPattern && (stripped == "" || stripped.StartsWith("#")))
            {
                continue;
            }

            if (stripped.StartsWith("%"))
            {
                if (inPattern)
                {
                    var pos = lines.Take(lineNum).Sum(l => l.Length + 1) + line.IndexOf("%");
                    var hint = HintEngine.GetHint("Directive after pattern", text, pos);
                    throw new STRlingParseError("Directive after pattern", pos, text, hint);
                }

                if (!stripped.StartsWith("%flags"))
                {
                    var pos = lines.Take(lineNum).Sum(l => l.Length + 1) + line.IndexOf("%");
                    var hint = HintEngine.GetHint("Malformed directive", text, pos);
                    throw new STRlingParseError("Malformed directive", pos, text, hint);
                }

                var idx = line.IndexOf("%flags");
                var after = line.Substring(idx + "%flags".Length);
                var allowed = " ,\t[]imsuxIMSUX";

                int j = 0;
                while (j < after.Length && allowed.Contains(after[j]))
                {
                    j++;
                }

                var flagsToken = after.Substring(0, j);
                var remainder = j < after.Length ? after.Substring(j) : "";

                var letters = "";
                foreach (var ch in flagsToken)
                {
                    if (char.IsLetter(ch))
                    {
                        letters += char.ToLower(ch);
                    }
                }

                var validFlags = "imsux";
                foreach (var ch in letters)
                {
                    if (!validFlags.Contains(ch))
                    {
                        var flagPos = lines.Take(lineNum).Sum(l => l.Length + 1) + idx;
                        var hint = HintEngine.GetHint($"Invalid flag '{ch}'", text, flagPos);
                        throw new STRlingParseError($"Invalid flag '{ch}'", flagPos, text, hint);
                    }
                }

                if (!string.IsNullOrEmpty(letters))
                {
                    flags = Flags.FromLetters(letters);
                }
                else
                {
                    // Check remainder for invalid flag
                    var trimmed = remainder.TrimStart();
                    if (trimmed.Length > 0)
                    {
                        var ch = trimmed[0];
                        var flagPos = lines.Take(lineNum).Sum(l => l.Length + 1) + idx;
                        var hint = HintEngine.GetHint($"Invalid flag '{ch}'", text, flagPos);
                        throw new STRlingParseError($"Invalid flag '{ch}'", flagPos, text, hint);
                    }
                }

                // Check if there's pattern content in remainder
                var remTrimmed = remainder.TrimStart();
                if (remTrimmed.Length > 0)
                {
                    patternLines.Add(remainder);
                    inPattern = true;
                }
                continue;
            }

            // Check for directive after pattern
            if (line.Contains("%flags"))
            {
                var pos = lines.Take(lineNum).Sum(l => l.Length + 1) + line.IndexOf("%flags");
                var hint = HintEngine.GetHint("Directive after pattern", text, pos);
                throw new STRlingParseError("Directive after pattern", pos, text, hint);
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
            return new Seq(new List<Node>());
        }

        var node = ParseAlt();
        _cur.SkipWsAndComments();

        if (!_cur.Eof())
        {
            if (_cur.Peek() == ')')
            {
                RaiseError("Unmatched ')'", _cur.I);
            }
            RaiseError("Unexpected trailing input", _cur.I);
        }

        return node;
    }

    private Node ParseAlt()
    {
        _cur.SkipWsAndComments();

        // Check for stray pipe at start
        if (_cur.Peek() == '|')
        {
            RaiseError("Alternation lacks left-hand side", _cur.I);
        }

        var branches = new List<Node>();
        branches.Add(ParseSeq());

        while (_cur.Peek() == '|')
        {
            _cur.Take();
            _cur.SkipWsAndComments();

            // Check for empty alternation (|| or trailing |)
            if (_cur.Peek() == '|' || _cur.Eof() || _cur.Peek() == ')')
            {
                RaiseError("Empty alternation", _cur.I);
            }

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
                if (ch == '{')
                {
                    // Check if it's a valid quantifier pattern
                    int j = _cur.I + 1;
                    var look = "";
                    while (j < _cur.Text.Length && _cur.Text[j] != '}')
                    {
                        look += _cur.Text[j];
                        j++;
                    }
                    if (j < _cur.Text.Length && look.Length > 0)
                    {
                        if (Regex.IsMatch(look, @"^\d+(,\d*)?$"))
                        {
                            RaiseError($"Invalid quantifier '{ch}'", _cur.I);
                        }
                        else
                        {
                            RaiseError("Brace quantifier: Invalid brace quantifier content", _cur.I);
                        }
                    }
                    else if (j >= _cur.Text.Length)
                    {
                        RaiseError("Incomplete quantifier", _cur.I);
                    }
                    else
                    {
                        RaiseError($"Invalid quantifier '{ch}'", _cur.I);
                    }
                }
                else
                {
                    RaiseError($"Invalid quantifier '{ch}'", _cur.I);
                }
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
        _cur.Take(); // consume backslash

        if (_cur.Eof())
        {
            RaiseError("Unexpected end of pattern after '\\'", startPos);
        }

        var ch = _cur.Peek();

        // Anchors
        if (ch == 'b') { _cur.Take(); return new Anchor("WordBoundary"); }
        if (ch == 'B') { _cur.Take(); return new Anchor("NotWordBoundary"); }
        if (ch == 'A') { _cur.Take(); return new Anchor("AbsoluteStart"); }
        if (ch == 'Z') { _cur.Take(); return new Anchor("EndBeforeFinalNewline"); }

        // Shorthand classes
        if (ch == 'd') { _cur.Take(); return new CharClass(false, new List<ClassItem> { new ClassEscape("digit") }); }
        if (ch == 'D') { _cur.Take(); return new CharClass(false, new List<ClassItem> { new ClassEscape("not-digit") }); }
        if (ch == 'w') { _cur.Take(); return new CharClass(false, new List<ClassItem> { new ClassEscape("word") }); }
        if (ch == 'W') { _cur.Take(); return new CharClass(false, new List<ClassItem> { new ClassEscape("not-word") }); }
        if (ch == 's') { _cur.Take(); return new CharClass(false, new List<ClassItem> { new ClassEscape("whitespace") }); }
        if (ch == 'S') { _cur.Take(); return new CharClass(false, new List<ClassItem> { new ClassEscape("not-whitespace") }); }

        // Control escapes
        if (ControlEscapes.ContainsKey(ch)) { _cur.Take(); return new Lit(ControlEscapes[ch]); }

        // Unicode property: \p{...} and \P{...}
        if (ch == 'p' || ch == 'P')
        {
            bool neg = ch == 'P';
            _cur.Take();
            if (_cur.Peek() != '{')
            {
                RaiseError("Expected { after \\p/\\P", startPos);
            }
            _cur.Take(); // consume {
            var prop = "";
            while (!_cur.Eof() && _cur.Peek() != '}')
            {
                prop += _cur.Take();
            }
            if (_cur.Eof())
            {
                RaiseError("Unterminated \\p{...}", startPos);
            }
            _cur.Take(); // consume }
            // Parse property name=value or just name
            string? propName = null;
            string propValue = prop;
            if (prop.Contains("="))
            {
                var parts = prop.Split('=', 2);
                propName = parts[0];
                propValue = parts[1];
            }
            return new CharClass(false, new List<ClassItem> {
                new ClassUnicodeProperty(propName, propValue, neg)
            });
        }

        // Hex escape: \x{...} or \xHH
        if (ch == 'x')
        {
            _cur.Take();
            if (_cur.Peek() == '{')
            {
                _cur.Take();
                var hex = "";
                while (!_cur.Eof() && _cur.Peek() != '}')
                {
                    hex += _cur.Take();
                }
                if (_cur.Eof())
                {
                    RaiseError("Unterminated \\x{...}", startPos);
                }
                _cur.Take(); // consume }
                int cp = Convert.ToInt32(hex.Length > 0 ? hex : "0", 16);
                return new Lit(char.ConvertFromUtf32(cp));
            }
            else
            {
                // \xHH - exactly 2 hex digits
                var hex = "";
                for (int i = 0; i < 2; i++)
                {
                    var h = _cur.Peek();
                    if (h == '\0' || !"0123456789ABCDEFabcdef".Contains(h))
                    {
                        RaiseError("Invalid \\xHH escape", startPos);
                    }
                    hex += _cur.Take();
                }
                int cp = Convert.ToInt32(hex, 16);
                return new Lit(((char)cp).ToString());
            }
        }

        // Unicode escape: \u{...} or \uHHHH
        if (ch == 'u')
        {
            _cur.Take();
            if (_cur.Peek() == '{')
            {
                _cur.Take();
                var hex = "";
                while (!_cur.Eof() && _cur.Peek() != '}')
                {
                    hex += _cur.Take();
                }
                if (_cur.Eof())
                {
                    RaiseError("Unterminated \\u{...}", startPos);
                }
                _cur.Take(); // consume }
                int cp = Convert.ToInt32(hex.Length > 0 ? hex : "0", 16);
                return new Lit(char.ConvertFromUtf32(cp));
            }
            else
            {
                // \uHHHH - exactly 4 hex digits
                var hex = "";
                for (int i = 0; i < 4; i++)
                {
                    var h = _cur.Peek();
                    if (h == '\0' || !"0123456789ABCDEFabcdef".Contains(h))
                    {
                        RaiseError("Invalid \\uHHHH escape", startPos);
                    }
                    hex += _cur.Take();
                }
                int cp = Convert.ToInt32(hex, 16);
                return new Lit(char.ConvertFromUtf32(cp));
            }
        }

        // \UHHHHHHHH - 8 hex digits
        if (ch == 'U')
        {
            _cur.Take();
            var hex = "";
            for (int i = 0; i < 8; i++)
            {
                var h = _cur.Peek();
                if (h == '\0' || !"0123456789ABCDEFabcdef".Contains(h))
                {
                    RaiseError("Invalid \\UHHHHHHHH escape", startPos);
                }
                hex += _cur.Take();
            }
            int cp = Convert.ToInt32(hex, 16);
            return new Lit(char.ConvertFromUtf32(cp));
        }

        // Backreference: \1-\9
        if (ch >= '1' && ch <= '9')
        {
            var numStr = "";
            while (_cur.Peek() >= '0' && _cur.Peek() <= '9')
            {
                numStr += _cur.Take();
            }
            int num = int.Parse(numStr);
            if (num > _capCount)
            {
                RaiseError($"Backreference to undefined group \\{num}", startPos);
            }
            return new Backref(num, null);
        }

        // Forbidden octal: \0
        if (ch == '0')
        {
            RaiseError("Forbidden octal escape", startPos);
        }

        // Named backreference: \k<name>
        if (ch == 'k')
        {
            _cur.Take();
            if (_cur.Peek() != '<')
            {
                RaiseError("Expected '<' after \\k", startPos);
            }
            _cur.Take(); // consume <
            var name = "";
            while (!_cur.Eof() && _cur.Peek() != '>')
            {
                name += _cur.Take();
            }
            if (_cur.Eof())
            {
                RaiseError("Unterminated named backref", startPos);
            }
            _cur.Take(); // consume >
            if (!_capNames.Contains(name))
            {
                RaiseError($"Backreference to undefined group <{name}>", startPos);
            }
            return new Backref(null, name);
        }

        // Meta escapes
        if ("^$.*+?()[]{}|\\/".Contains(ch))
        {
            _cur.Take();
            return new Lit(ch.ToString());
        }

        // Unknown escape - if alphanumeric, error
        if (char.IsLetterOrDigit(ch))
        {
            RaiseError($"Unknown escape sequence \\{ch}", startPos);
        }

        _cur.Take();
        return new Lit(ch.ToString());
    }

    private Node ParseGroupOrLook()
    {
        var startPos = _cur.I;
        _cur.Take(); // consume (
        _cur.SkipWsAndComments();

        if (_cur.Peek() == '?')
        {
            _cur.Take();
            var next = _cur.Peek();

            if (next == ':')
            {
                _cur.Take();
                var body = ParseAlt();
                if (_cur.Peek() != ')') RaiseError("Unterminated group", _cur.I);
                _cur.Take();
                return new Group(false, body, null, false);
            }

            if (next == '=')
            {
                _cur.Take();
                var body = ParseAlt();
                if (_cur.Peek() != ')') RaiseError("Unterminated lookahead", _cur.I);
                _cur.Take();
                return new Lookahead(body);
            }

            if (next == '!')
            {
                _cur.Take();
                var body = ParseAlt();
                if (_cur.Peek() != ')') RaiseError("Unterminated lookahead", _cur.I);
                _cur.Take();
                return new NegativeLookahead(body);
            }

            if (next == '<')
            {
                _cur.Take();
                var afterAngle = _cur.Peek();
                if (afterAngle == '=')
                {
                    _cur.Take();
                    var body = ParseAlt();
                    if (_cur.Peek() != ')') RaiseError("Unterminated lookbehind", _cur.I);
                    _cur.Take();
                    return new Lookbehind(body);
                }
                else if (afterAngle == '!')
                {
                    _cur.Take();
                    var body = ParseAlt();
                    if (_cur.Peek() != ')') RaiseError("Unterminated lookbehind", _cur.I);
                    _cur.Take();
                    return new NegativeLookbehind(body);
                }
                else
                {
                    // Named group
                    var name = "";
                    while (!_cur.Eof() && _cur.Peek() != '>')
                    {
                        name += _cur.Take();
                    }
                    if (_cur.Eof())
                    {
                        RaiseError("Unterminated group name", _cur.I);
                    }
                    _cur.Take(); // consume >

                    // Validate group name
                    if (name.Length == 0 || (!char.IsLetter(name[0]) && name[0] != '_'))
                    {
                        RaiseError($"Invalid group name '{name}'", startPos);
                    }
                    for (int k = 1; k < name.Length; k++)
                    {
                        if (!char.IsLetterOrDigit(name[k]) && name[k] != '_')
                        {
                            RaiseError($"Invalid group name '{name}'", startPos);
                        }
                    }

                    if (_capNames.Contains(name))
                    {
                        RaiseError($"Duplicate group name '{name}'", startPos);
                    }
                    _capNames.Add(name);
                    _capCount++;

                    var body = ParseAlt();
                    if (_cur.Peek() != ')') RaiseError("Unterminated group", _cur.I);
                    _cur.Take();
                    return new Group(true, body, name, false);
                }
            }

            if (next == '>')
            {
                _cur.Take();
                var body = ParseAlt();
                if (_cur.Peek() != ')') RaiseError("Unterminated atomic group", _cur.I);
                _cur.Take();
                return new Group(false, body, null, true);
            }

            // Check for inline modifiers
            var save = _cur.I;
            var scan = "";
            int sj = save;
            while (sj < _cur.Text.Length && "imsux".Contains(_cur.Text[sj]))
            {
                scan += _cur.Text[sj];
                sj++;
            }
            if (scan.Length > 0 && sj < _cur.Text.Length && _cur.Text[sj] == ')')
            {
                RaiseError($"Inline modifiers like (?{scan}...) are not supported", startPos);
            }

            RaiseError($"Unknown group modifier: ?{next}", _cur.I - 1);
            return new Lit("");
        }
        else
        {
            // Capturing group
            _capCount++;
            var body = ParseAlt();
            if (_cur.Peek() != ')') RaiseError("Unterminated group", _cur.I);
            _cur.Take();
            return new Group(true, body, null, false);
        }
    }

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

        // Empty class: [] or [^]
        if (_cur.Peek() == ']')
        {
            _cur.InClass--;
            RaiseError("Unterminated character class", _cur.I);
        }

        var items = new List<ClassItem>();

        while (!_cur.Eof() && _cur.Peek() != ']')
        {
            var item = ParseClassItem();

            // Check for range
            if (_cur.Peek() == '-' && PeekAt(1) != ']' && !_cur.Eof())
            {
                if (item is ClassLiteral fromLit)
                {
                    _cur.Take(); // consume -
                    if (_cur.Eof() || _cur.Peek() == ']')
                    {
                        items.Add(item);
                        items.Add(new ClassLiteral("-"));
                        continue;
                    }
                    var toItem = ParseClassItem();
                    if (toItem is ClassLiteral toLit)
                    {
                        if (string.Compare(toLit.Value, fromLit.Value, StringComparison.Ordinal) < 0)
                        {
                            _cur.InClass--;
                            RaiseError("Invalid character range", startPos);
                        }
                        items.Add(new ClassRange(fromLit.Value, toLit.Value));
                        continue;
                    }
                    else
                    {
                        items.Add(item);
                        items.Add(new ClassLiteral("-"));
                        items.Add(toItem);
                        continue;
                    }
                }
            }

            items.Add(item);
        }

        if (_cur.Eof())
        {
            _cur.InClass--;
            RaiseError("Unterminated character class", _cur.I);
        }

        _cur.Take(); // consume ]
        _cur.InClass--;
        return new CharClass(negated, items);
    }

    private ClassItem ParseClassItem()
    {
        var ch = _cur.Peek();

        if (ch == '\\')
        {
            var startPos = _cur.I;
            _cur.Take(); // consume backslash

            if (_cur.Eof())
            {
                RaiseError("Unexpected end of pattern after '\\'", startPos);
            }

            var escCh = _cur.Peek();

            // Shorthand classes
            if (escCh == 'd') { _cur.Take(); return new ClassEscape("digit"); }
            if (escCh == 'D') { _cur.Take(); return new ClassEscape("not-digit"); }
            if (escCh == 'w') { _cur.Take(); return new ClassEscape("word"); }
            if (escCh == 'W') { _cur.Take(); return new ClassEscape("not-word"); }
            if (escCh == 's') { _cur.Take(); return new ClassEscape("whitespace"); }
            if (escCh == 'S') { _cur.Take(); return new ClassEscape("not-whitespace"); }

            // Control escapes
            if (ControlEscapes.ContainsKey(escCh))
            {
                _cur.Take();
                return new ClassLiteral(ControlEscapes[escCh]);
            }

            // Unicode property: \p{...} and \P{...}
            if (escCh == 'p' || escCh == 'P')
            {
                bool neg = escCh == 'P';
                _cur.Take();
                if (_cur.Peek() != '{')
                {
                    RaiseError("Expected { after \\p/\\P", startPos);
                }
                _cur.Take();
                var prop = "";
                while (!_cur.Eof() && _cur.Peek() != '}')
                {
                    prop += _cur.Take();
                }
                if (_cur.Eof())
                {
                    _cur.InClass--;
                    RaiseError("Unterminated \\p{...}", startPos);
                }
                _cur.Take();
                string? propName = null;
                string propValue = prop;
                if (prop.Contains("="))
                {
                    var parts = prop.Split('=', 2);
                    propName = parts[0];
                    propValue = parts[1];
                }
                return new ClassUnicodeProperty(propName, propValue, neg);
            }

            // Hex escape: \x{...} or \xHH
            if (escCh == 'x')
            {
                _cur.Take();
                if (_cur.Peek() == '{')
                {
                    _cur.Take();
                    var hex = "";
                    while (!_cur.Eof() && _cur.Peek() != '}')
                    {
                        hex += _cur.Take();
                    }
                    if (_cur.Eof())
                    {
                        _cur.InClass--;
                        RaiseError("Unterminated \\x{...}", startPos);
                    }
                    _cur.Take();
                    int cp = Convert.ToInt32(hex.Length > 0 ? hex : "0", 16);
                    return new ClassLiteral(char.ConvertFromUtf32(cp));
                }
                else
                {
                    var hex = "";
                    for (int i = 0; i < 2; i++)
                    {
                        var h = _cur.Peek();
                        if (h == '\0' || !"0123456789ABCDEFabcdef".Contains(h))
                        {
                            _cur.InClass--;
                            RaiseError("Invalid \\xHH escape", startPos);
                        }
                        hex += _cur.Take();
                    }
                    int cp = Convert.ToInt32(hex, 16);
                    return new ClassLiteral(((char)cp).ToString());
                }
            }

            // Unicode escape: \u{...} or \uHHHH
            if (escCh == 'u')
            {
                _cur.Take();
                if (_cur.Peek() == '{')
                {
                    _cur.Take();
                    var hex = "";
                    while (!_cur.Eof() && _cur.Peek() != '}')
                    {
                        hex += _cur.Take();
                    }
                    if (_cur.Eof())
                    {
                        _cur.InClass--;
                        RaiseError("Unterminated \\u{...}", startPos);
                    }
                    _cur.Take();
                    int cp = Convert.ToInt32(hex.Length > 0 ? hex : "0", 16);
                    return new ClassLiteral(char.ConvertFromUtf32(cp));
                }
                else
                {
                    var hex = "";
                    for (int i = 0; i < 4; i++)
                    {
                        var h = _cur.Peek();
                        if (h == '\0' || !"0123456789ABCDEFabcdef".Contains(h))
                        {
                            _cur.InClass--;
                            RaiseError("Invalid \\uHHHH escape", startPos);
                        }
                        hex += _cur.Take();
                    }
                    int cp = Convert.ToInt32(hex, 16);
                    return new ClassLiteral(char.ConvertFromUtf32(cp));
                }
            }

            // Forbidden octal: \0
            if (escCh == '0')
            {
                _cur.InClass--;
                RaiseError("Forbidden octal escape", startPos);
            }

            // Meta escapes in class
            if ("^$.*+?()[]{}|\\/\\-".Contains(escCh))
            {
                _cur.Take();
                return new ClassLiteral(escCh.ToString());
            }

            // Unknown escape - alphanumeric is error
            if (char.IsLetterOrDigit(escCh))
            {
                _cur.InClass--;
                RaiseError($"Unknown escape sequence \\{escCh}", startPos);
            }

            _cur.Take();
            return new ClassLiteral(escCh.ToString());
        }
        else
        {
            _cur.Take();
            return new ClassLiteral(ch.ToString());
        }
    }

    private char PeekAt(int offset)
    {
        var j = _cur.I + offset;
        return j < _cur.Text.Length ? _cur.Text[j] : '\0';
    }

    private (Node, bool) ParseQuantIfAny(Node child)
    {
        _cur.SkipWsAndComments();
        var ch = _cur.Peek();

        if (child is Anchor)
        {
            if (ch != '\0' && "*+?{".Contains(ch))
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
                var (minVal, maxVal, ok) = ParseBraceQuant();
                if (!ok) return (child, true);
                min = minVal;
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

    private (int, int?, bool) ParseBraceQuant()
    {
        var startPos = _cur.I;
        _cur.Take(); // consume {

        // Look at the content to determine if it's a valid quantifier
        var contentStart = _cur.I;
        var content = "";
        while (!_cur.Eof() && _cur.Peek() != '}')
        {
            content += _cur.Take();
        }

        if (_cur.Eof())
        {
            RaiseError("Incomplete quantifier", startPos);
        }

        _cur.Take(); // consume }

        // Validate content
        if (content.Length == 0)
        {
            RaiseError("Brace quantifier: Invalid brace quantifier content", startPos);
        }

        // Check if it matches valid quantifier format: digits, optionally comma and optional digits
        if (!Regex.IsMatch(content, @"^\d+(,\d*)?$"))
        {
            RaiseError("Brace quantifier: Invalid brace quantifier content", startPos);
        }

        // Parse min,max
        var commaIdx = content.IndexOf(',');
        if (commaIdx == -1)
        {
            int val = int.Parse(content);
            return (val, val, true);
        }
        else
        {
            int minVal = int.Parse(content.Substring(0, commaIdx));
            int? maxVal = null;
            if (commaIdx + 1 < content.Length)
            {
                maxVal = int.Parse(content.Substring(commaIdx + 1));
            }

            if (maxVal.HasValue && maxVal.Value < minVal)
            {
                RaiseError("Invalid quantifier range", startPos);
            }

            return (minVal, maxVal, true);
        }
    }

    private Lit TakeLiteralChar()
    {
        var ch = _cur.Take();
        return new Lit(ch.ToString());
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
            if (I + s.Length <= Text.Length && Text.Substring(I, s.Length) == s)
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
