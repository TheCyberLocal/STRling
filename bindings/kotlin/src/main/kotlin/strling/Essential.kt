package strling

import kotlinx.serialization.json.JsonPrimitive
import strling.core.*

/**
 * Standard library: canonical, RFC-grounded patterns for the most commonly
 * validated string formats.
 *
 * Each helper composes existing Simply primitives so the compiled output
 * flows through the standard pipeline and no raw regex leaks into the
 * public API.
 */
object Essential {

    private val letterItems: List<ClassItem> = listOf(
        Range(from = "A", to = "Z"),
        Range(from = "a", to = "z")
    )
    private val digitItems: List<ClassItem> = listOf(Escape(kind = "d"))
    private val hexItems: List<ClassItem> = listOf(
        Range(from = "A", to = "F"),
        Range(from = "a", to = "f"),
        Range(from = "0", to = "9")
    )

    private fun chars(s: String): List<ClassItem> =
        s.map { Literal(value = it.toString()) }

    private fun classOf(items: List<ClassItem>, min: Int, max: Int?): Pattern {
        val p = Pattern(CharacterClass(negated = false, members = items))
        return if (min == 1 && max == 1) p else p.repeat(min, max)
    }

    private fun digN(min: Int, max: Int?) = classOf(digitItems, min, max)
    private fun hexN(min: Int, max: Int?) = classOf(hexItems, min, max)
    private fun lettersN(min: Int, max: Int?) = classOf(letterItems, min, max)

    /** Matches an email address (RFC 5322 addr-spec, basic structure). */
    fun email(): Pattern {
        val local = classOf(letterItems + digitItems + chars("._%+-"), 1, 0)
        val domain = classOf(letterItems + digitItems + chars(".-"), 1, 0)
        val tld = lettersN(2, 0)
        return Simply.merge(local, "@", domain, ".", tld)
    }

    /** Matches an HTTP or HTTPS URL (RFC 3986 generic syntax). */
    fun url(): Pattern {
        val base = letterItems + digitItems + chars("/_-.~%&=:@!\$'()*+,;")
        val withQ = base + chars("?")
        val withFrag = withQ + chars("#")

        val scheme = Simply.merge("http", Simply.may("s"))
        val host = classOf(letterItems + digitItems + chars(".-"), 1, 0)
        val port = Simply.may(Simply.merge(":", digN(1, 0)))
        val path = Simply.may(Simply.merge("/", classOf(base, 0, 0)))
        val query = Simply.may(Simply.merge("?", classOf(withQ, 0, 0)))
        val fragment = Simply.may(Simply.merge("#", classOf(withFrag, 0, 0)))
        return Simply.merge(scheme, "://", host, port, path, query, fragment)
    }

    /**
     * Matches a UUID (RFC 4122). Pass `4` for v4-specific validation, or `0`
     * for any UUID version.
     */
    fun uuid(version: Int = 0): Pattern {
        val dash = "-"
        if (version == 4) {
            val variant = classOf(chars("89ABab"), 1, 1)
            return Simply.merge(
                hexN(8, null), dash,
                hexN(4, null), dash,
                "4", hexN(3, null), dash,
                variant, hexN(3, null), dash,
                hexN(12, null)
            )
        }
        return Simply.merge(
            hexN(8, null), dash,
            hexN(4, null), dash,
            hexN(4, null), dash,
            hexN(4, null), dash,
            hexN(12, null)
        )
    }

    /**
     * Matches an IPv4 (RFC 791) or full-form IPv6 (RFC 4291) address.
     * Pass `4` or `6` for family-specific matching, or `0` for either family.
     */
    fun ip(version: Int = 0): Pattern {
        val ipv4 = Simply.merge(
            digN(1, 3), ".",
            digN(1, 3), ".",
            digN(1, 3), ".",
            digN(1, 3)
        )
        if (version == 4) return ipv4
        val ipv6 = Simply.merge(
            hexN(1, 4), ":",
            hexN(1, 4), ":",
            hexN(1, 4), ":",
            hexN(1, 4), ":",
            hexN(1, 4), ":",
            hexN(1, 4), ":",
            hexN(1, 4), ":",
            hexN(1, 4)
        )
        if (version == 6) return ipv6
        return Simply.anyOf(ipv4, ipv6)
    }

    /** Matches an ISO 8601 / RFC 3339 datetime. */
    fun dateTime(): Pattern {
        val sign = classOf(chars("+-"), 1, 1)
        val frac = Simply.merge(".", digN(1, 0))
        val offset = Simply.merge(sign, digN(2, null), ":", digN(2, null))
        return Simply.merge(
            digN(4, null), "-", digN(2, null), "-", digN(2, null),
            "T",
            digN(2, null), ":", digN(2, null), ":", digN(2, null),
            Simply.may(frac),
            Simply.may(Simply.anyOf(Pattern(Literal("Z")), offset))
        )
    }
}
