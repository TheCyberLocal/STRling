using System.Collections.Generic;
using Strling.Core;

namespace Strling.Simply
{
    // ============================================================================
    // Standard Library — Essential Patterns
    //
    // Compatibility lexical-shape patterns for common string formats. These
    // helpers do not establish semantic validity or complete standards
    // conformance. Each helper composes core AST nodes so output flows
    // through the standard Parse → Compile → Emit pipeline and no raw regex
    // leaks into the public API.
    // ============================================================================
    public static class Essential
    {
        private static ClassRange UpperRange => new ClassRange("A", "Z");
        private static ClassRange LowerRange => new ClassRange("a", "z");
        private static ClassRange DigitRange => new ClassRange("0", "9");

        private static Pattern WrapClass(IEnumerable<ClassItem> items, int min, int? max)
        {
            var cc = new CharClass(false, new List<ClassItem>(items));
            if (min == 1 && max == 1) return new Pattern(cc);
            return new Pattern(new Quant(cc, min, max, true, false, false));
        }

        private static Pattern Letters(int min, int? max)
            => WrapClass(new ClassItem[] { UpperRange, LowerRange }, min, max);

        private static Pattern Digits(int min, int? max)
            => WrapClass(new ClassItem[] { DigitRange }, min, max);

        private static Pattern HexDigits(int min, int? max)
            => WrapClass(new ClassItem[] {
                new ClassRange("A", "F"), new ClassRange("a", "f"), DigitRange
            }, min, max);

        private static Pattern AltOf(params Pattern[] branches)
        {
            var list = new List<Node>();
            foreach (var b in branches) list.Add(b.Node);
            return new Pattern(new Alt(list));
        }

        private static Pattern Optional(Pattern inner)
            => new Pattern(new Quant(inner.Node, 0, 1, true, false, false));

        private static Pattern LitP(string text) => new Pattern(new Lit(text));

        /// <summary>
        /// Matches the legacy email-like lexical shape; RFC 5322 conformance is not claimed.
        /// </summary>
        public static Pattern Email()
        {
            var local = WrapClass(new ClassItem[] {
                UpperRange, LowerRange, DigitRange,
                new ClassLiteral("."), new ClassLiteral("_"),
                new ClassLiteral("%"), new ClassLiteral("+"),
                new ClassLiteral("-")
            }, 1, null);
            var domain = WrapClass(new ClassItem[] {
                UpperRange, LowerRange, DigitRange,
                new ClassLiteral("."), new ClassLiteral("-")
            }, 1, null);
            var tld = Letters(2, null);
            return S.Merge(local, LitP("@"), domain, LitP("."), tld);
        }

        /// <summary>
        /// Matches the legacy HTTP(S) URL-like lexical shape; RFC 3986
        /// conformance, host validity, and percent-encoding validity are not claimed.
        /// </summary>
        public static Pattern Url()
        {
            ClassItem[] urlChars(params string[] extras)
            {
                var baseItems = new List<ClassItem> {
                    UpperRange, LowerRange, DigitRange,
                    new ClassLiteral("/"), new ClassLiteral("_"),
                    new ClassLiteral("-"), new ClassLiteral("."),
                    new ClassLiteral("~"), new ClassLiteral("%"),
                    new ClassLiteral("&"), new ClassLiteral("="),
                    new ClassLiteral(":"), new ClassLiteral("@"),
                    new ClassLiteral("!"), new ClassLiteral("$"),
                    new ClassLiteral("'"), new ClassLiteral("("),
                    new ClassLiteral(")"), new ClassLiteral("*"),
                    new ClassLiteral("+"), new ClassLiteral(","),
                    new ClassLiteral(";"),
                };
                foreach (var e in extras) baseItems.Add(new ClassLiteral(e));
                return baseItems.ToArray();
            }
            var scheme = S.Merge(LitP("http"), Optional(LitP("s")));
            var host = WrapClass(new ClassItem[] {
                UpperRange, LowerRange, DigitRange,
                new ClassLiteral("."), new ClassLiteral("-")
            }, 1, null);
            var port = Optional(S.Merge(LitP(":"), Digits(1, null)));
            var path = Optional(S.Merge(LitP("/"), WrapClass(urlChars(), 0, null)));
            var query = Optional(S.Merge(LitP("?"), WrapClass(urlChars("?"), 0, null)));
            var fragment = Optional(S.Merge(LitP("#"), WrapClass(urlChars("?", "#"), 0, null)));
            return S.Merge(scheme, LitP("://"), host, port, path, query, fragment);
        }

        /// <summary>
        /// Matches the RFC 9562 8-4-4-4-12 text shape. When
        /// <paramref name="version"/> is 4, constrains the version and variant nibbles.
        /// </summary>
        public static Pattern Uuid(int version = 0)
        {
            var dash = LitP("-");
            if (version == 4)
            {
                var variant = WrapClass(new ClassItem[] {
                    new ClassLiteral("8"), new ClassLiteral("9"),
                    new ClassLiteral("A"), new ClassLiteral("B"),
                    new ClassLiteral("a"), new ClassLiteral("b"),
                }, 1, 1);
                return S.Merge(
                    HexDigits(8, 8), dash,
                    HexDigits(4, 4), dash,
                    LitP("4"), HexDigits(3, 3), dash,
                    variant, HexDigits(3, 3), dash,
                    HexDigits(12, 12)
                );
            }
            return S.Merge(
                HexDigits(8, 8), dash,
                HexDigits(4, 4), dash,
                HexDigits(4, 4), dash,
                HexDigits(4, 4), dash,
                HexDigits(12, 12)
            );
        }

        /// <summary>
        /// Matches an IPv4-like or full-form IPv6 lexical shape. IPv4 octet
        /// ranges and complete RFC 4291 text-form coverage are not claimed.
        /// </summary>
        public static Pattern Ip(int version = 0)
        {
            var ipv4 = S.Merge(
                Digits(1, 3), LitP("."),
                Digits(1, 3), LitP("."),
                Digits(1, 3), LitP("."),
                Digits(1, 3)
            );
            var ipv6 = S.Merge(
                HexDigits(1, 4), LitP(":"),
                HexDigits(1, 4), LitP(":"),
                HexDigits(1, 4), LitP(":"),
                HexDigits(1, 4), LitP(":"),
                HexDigits(1, 4), LitP(":"),
                HexDigits(1, 4), LitP(":"),
                HexDigits(1, 4), LitP(":"),
                HexDigits(1, 4)
            );
            if (version == 4) return ipv4;
            if (version == 6) return ipv6;
            return AltOf(ipv4, ipv6);
        }

        /// <summary>
        /// Matches a timestamp-like lexical shape with optional fraction and
        /// offset; calendar, clock, RFC 3339, and ISO 8601 validity are not claimed.
        /// </summary>
        public static Pattern DateTime()
        {
            var sign = WrapClass(new ClassItem[] {
                new ClassLiteral("+"), new ClassLiteral("-")
            }, 1, 1);
            return S.Merge(
                Digits(4, 4), LitP("-"), Digits(2, 2), LitP("-"), Digits(2, 2),
                LitP("T"),
                Digits(2, 2), LitP(":"), Digits(2, 2), LitP(":"), Digits(2, 2),
                Optional(S.Merge(LitP("."), Digits(1, null))),
                Optional(AltOf(LitP("Z"), S.Merge(sign, Digits(2, 2), LitP(":"), Digits(2, 2))))
            );
        }
    }
}
