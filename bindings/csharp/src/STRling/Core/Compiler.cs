using System;
using System.Collections.Generic;
using System.Linq;

namespace Strling.Core;

public class Compiler
{
    public static IROp Compile(Node node)
    {
        return node switch
        {
            Alt alt => new IRAlt((alt.Alternatives ?? new List<Node>()).Select(Compile).ToList()),
            Seq seq => CreateSeq((seq.Parts ?? new List<Node>()).Select(Compile)),
            Lit lit => new IRLit(lit.Value),
            Dot dot => new IRDot(),
            Anchor anchor => new IRAnchor(MapAnchor(anchor.At)),
            CharClass cc => new IRCharClass(cc.Negated, (cc.Members ?? new List<ClassItem>()).Select(CompileClassItem).ToList()),
            Quant quant => CompileQuant(quant),
            Group group => new IRGroup(group.Capturing, Compile(group.Body), group.Name, group.Atomic),
            Backref backref => new IRBackref(backref.Index, backref.Name),
            Lookahead la => new IRLook("Ahead", false, Compile(la.Body)),
            NegativeLookahead nla => new IRLook("Ahead", true, Compile(nla.Body)),
            Lookbehind lb => new IRLook("Behind", false, Compile(lb.Body)),
            NegativeLookbehind nlb => new IRLook("Behind", true, Compile(nlb.Body)),
            _ => throw new NotImplementedException($"Unknown node type: {node.GetType().Name}")
        };
    }

    private static IROp CreateSeq(IEnumerable<IROp> parts)
    {
        var list = new List<IROp>();
        foreach (var part in parts)
        {
            if (part is IRSeq subSeq)
            {
                list.AddRange(subSeq.Parts);
            }
            else
            {
                list.Add(part);
            }
        }

        var merged = new List<IROp>();
        foreach (var op in list)
        {
            if (merged.Count > 0 && merged[^1] is IRLit lastLit && op is IRLit newLit)
            {
                merged[^1] = new IRLit(lastLit.Value + newLit.Value);
            }
            else
            {
                merged.Add(op);
            }
        }

        if (merged.Count == 1) return merged[0];
        return new IRSeq(merged);
    }

    private static string MapAnchor(string at)
    {
        return at == "NonWordBoundary" ? "NotWordBoundary" : at;
    }

    private static IRClassItem CompileClassItem(ClassItem item)
    {
        return item switch
        {
            ClassRange range => new IRClassRange(range.From, range.To),
            ClassLiteral lit => new IRClassLiteral(lit.Value),
            ClassEscape esc => new IRClassEscape(MapEscapeKind(esc.Kind), null),
            ClassUnicodeProperty prop => new IRClassEscape(prop.Negated ? "P" : "p", prop.Value),
            _ => throw new NotImplementedException($"Unknown class item type: {item.GetType().Name}")
        };
    }

    private static string MapEscapeKind(string kind)
    {
        return kind switch
        {
            "digit" => "d",
            "not-digit" => "D",
            "word" => "w",
            "not-word" => "W",
            "whitespace" => "s",
            "not-whitespace" => "S",
            "space" => "s",
            "not-space" => "S",
            _ => kind
        };
    }

    private static IROp CompileQuant(Quant quant)
    {
        string mode = "Greedy";
        if (quant.Lazy) mode = "Lazy";
        else if (quant.Possessive) mode = "Possessive";

        object max = quant.Max.HasValue ? quant.Max.Value : "Inf";

        return new IRQuant(Compile(quant.Target), quant.Min, max, mode);
    }
}
