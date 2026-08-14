package com.strling.simply;

import com.strling.core.Nodes.*;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * Standard library compatibility lexical-shape patterns for common string
 * formats. They do not establish semantic validity or standards conformance.
 *
 * <p>Each helper composes existing Simply primitives so the compiled output
 * flows through the standard pipeline and no raw regex leaks into the public
 * API.</p>
 */
public class Essential {

    private Essential() {}

    private static List<ClassItem> letterItems() {
        List<ClassItem> items = new ArrayList<>();
        items.add(new ClassRange("A", "Z"));
        items.add(new ClassRange("a", "z"));
        return items;
    }

    private static List<ClassItem> digitItems() {
        List<ClassItem> items = new ArrayList<>();
        items.add(new ClassEscape("d"));
        return items;
    }

    private static List<ClassItem> hexItems() {
        List<ClassItem> items = new ArrayList<>();
        items.add(new ClassRange("A", "F"));
        items.add(new ClassRange("a", "f"));
        items.add(new ClassRange("0", "9"));
        return items;
    }

    private static Pattern classOf(List<ClassItem> items, Integer min, Object max) {
        Node body = new CharClass(false, items);
        if (min == null) {
            return new Pattern(body);
        }
        Object maxValue = (max == null) ? "Inf" : max;
        Node q = new Quant(body, min, maxValue, "Greedy");
        return new Pattern(q);
    }

    private static Pattern digN(int min, Object max) {
        return classOf(digitItems(), min, max);
    }

    private static Pattern hexN(int min, Object max) {
        return classOf(hexItems(), min, max);
    }

    private static Pattern lettersN(int min, Object max) {
        return classOf(letterItems(), min, max);
    }

    @SafeVarargs
    private static List<ClassItem> mix(List<ClassItem>... groups) {
        List<ClassItem> out = new ArrayList<>();
        for (List<ClassItem> g : groups) {
            out.addAll(g);
        }
        return out;
    }

    private static List<ClassItem> chars(String chars) {
        List<ClassItem> items = new ArrayList<>();
        for (int i = 0; i < chars.length(); i++) {
            items.add(new ClassLiteral(String.valueOf(chars.charAt(i))));
        }
        return items;
    }

    /**
     * Matches the legacy email-like lexical shape; RFC 5322 conformance is not claimed.
     */
    public static Pattern email() {
        Pattern local = classOf(mix(letterItems(), digitItems(), chars("._%+-")), 1, null);
        Pattern domain = classOf(mix(letterItems(), digitItems(), chars(".-")), 1, null);
        Pattern tld = lettersN(2, null);
        return Constructors.merge(local, Pattern.lit("@"), domain, Pattern.lit("."), tld);
    }

    /**
     * Matches the legacy HTTP(S) URL-like lexical shape; RFC 3986 conformance is not claimed.
     */
    public static Pattern url() {
        List<ClassItem> base = mix(letterItems(), digitItems(), chars("/_-.~%&=:@!$'()*+,;"));
        List<ClassItem> withQuestion = new ArrayList<>(base);
        withQuestion.addAll(chars("?"));
        List<ClassItem> withFragment = new ArrayList<>(withQuestion);
        withFragment.addAll(chars("#"));

        Pattern scheme = Constructors.merge(Pattern.lit("http"), Constructors.may(Pattern.lit("s")));
        Pattern host = classOf(mix(letterItems(), digitItems(), chars(".-")), 1, null);
        Pattern port = Constructors.may(Constructors.merge(Pattern.lit(":"), digN(1, null)));
        Pattern path = Constructors.may(Constructors.merge(Pattern.lit("/"), classOf(base, 0, null)));
        Pattern query = Constructors.may(Constructors.merge(Pattern.lit("?"), classOf(withQuestion, 0, null)));
        Pattern fragment = Constructors.may(Constructors.merge(Pattern.lit("#"), classOf(withFragment, 0, null)));
        return Constructors.merge(scheme, Pattern.lit("://"), host, port, path, query, fragment);
    }

    /**
     * Matches the RFC 9562 UUID text shape. Pass {@code 4} to constrain the
     * version/variant nibbles, or {@code 0} for uninterpreted fields.
     */
    public static Pattern uuid(int version) {
        Pattern dash = Pattern.lit("-");
        if (version == 4) {
            Pattern variant = classOf(chars("89ABab"), 1, 1);
            return Constructors.merge(
                hexN(8, 8), dash,
                hexN(4, 4), dash,
                Pattern.lit("4"), hexN(3, 3), dash,
                variant, hexN(3, 3), dash,
                hexN(12, 12)
            );
        }
        return Constructors.merge(
            hexN(8, 8), dash,
            hexN(4, 4), dash,
            hexN(4, 4), dash,
            hexN(4, 4), dash,
            hexN(12, 12)
        );
    }

    /** Convenience: matches any UUID version. */
    public static Pattern uuid() {
        return uuid(0);
    }

    /**
     * Matches an IPv4-like or full-form IPv6 lexical shape; address validity is not claimed.
     * Pass {@code 4} or {@code 6} for family-specific matching, or {@code 0}
     * for either family.
     */
    public static Pattern ip(int version) {
        Pattern ipv4 = Constructors.merge(
            digN(1, 3), Pattern.lit("."),
            digN(1, 3), Pattern.lit("."),
            digN(1, 3), Pattern.lit("."),
            digN(1, 3)
        );
        if (version == 4) return ipv4;
        Pattern ipv6 = Constructors.merge(
            hexN(1, 4), Pattern.lit(":"),
            hexN(1, 4), Pattern.lit(":"),
            hexN(1, 4), Pattern.lit(":"),
            hexN(1, 4), Pattern.lit(":"),
            hexN(1, 4), Pattern.lit(":"),
            hexN(1, 4), Pattern.lit(":"),
            hexN(1, 4), Pattern.lit(":"),
            hexN(1, 4)
        );
        if (version == 6) return ipv6;
        return Constructors.anyOf(ipv4, ipv6);
    }

    /** Convenience: accepts both IPv4 and IPv6. */
    public static Pattern ip() {
        return ip(0);
    }

    /**
     * Matches a timestamp-like lexical shape; RFC 3339 / ISO 8601 validity is not claimed.
     */
    public static Pattern dateTime() {
        Pattern sign = classOf(chars("+-"), 1, 1);
        Pattern frac = Constructors.merge(Pattern.lit("."), digN(1, null));
        Pattern offset = Constructors.merge(sign, digN(2, 2), Pattern.lit(":"), digN(2, 2));
        return Constructors.merge(
            digN(4, 4), Pattern.lit("-"), digN(2, 2), Pattern.lit("-"), digN(2, 2),
            Pattern.lit("T"),
            digN(2, 2), Pattern.lit(":"), digN(2, 2), Pattern.lit(":"), digN(2, 2),
            Constructors.may(frac),
            Constructors.may(Constructors.anyOf(Pattern.lit("Z"), offset))
        );
    }
}
