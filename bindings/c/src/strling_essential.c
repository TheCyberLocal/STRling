/*
 * STRling Essential — RFC-grounded patterns for the most commonly
 * validated string formats (email, URL, UUID, IP, dateTime).
 *
 * Each helper composes JSON AST nodes via jansson and returns a heap
 * allocated JSON string compatible with `strling_compile`. The caller
 * owns the returned buffer and must release it with `free()`.
 */

#include "strling_essential.h"

#include <jansson.h>
#include <stdlib.h>
#include <string.h>

static json_t *literal(const char *s) {
    return json_pack("{s:s, s:s}", "type", "Literal", "value", s);
}

static json_t *escape_digit(void) {
    return json_pack("{s:s, s:s}", "type", "Escape", "kind", "digit");
}

static json_t *range(const char *from, const char *to) {
    return json_pack("{s:s, s:s, s:s}", "type", "Range", "from", from, "to", to);
}

static json_t *class_lit(char c) {
    char buf[2] = {c, '\0'};
    return json_pack("{s:s, s:s}", "type", "Literal", "value", buf);
}

static json_t *char_class(json_t *members) {
    return json_pack("{s:s, s:b, s:o}", "type", "CharacterClass", "negated", 0, "members", members);
}

static json_t *quant(json_t *target, int min, int max_or_neg1) {
    json_t *node = json_object();
    json_object_set_new(node, "type", json_string("Quantifier"));
    json_object_set_new(node, "target", target);
    json_object_set_new(node, "min", json_integer(min));
    if (max_or_neg1 < 0) {
        json_object_set_new(node, "max", json_null());
    } else {
        json_object_set_new(node, "max", json_integer(max_or_neg1));
    }
    json_object_set_new(node, "greedy", json_true());
    json_object_set_new(node, "lazy", json_false());
    json_object_set_new(node, "possessive", json_false());
    return node;
}

static json_t *non_capturing_group(json_t *body) {
    return json_pack("{s:s, s:b, s:o}", "type", "Group", "capturing", 0, "body", body);
}

static json_t *opt(json_t *body) {
    return quant(non_capturing_group(body), 0, 1);
}

static json_t *sequence(json_t *parts) {
    return json_pack("{s:s, s:o}", "type", "Sequence", "parts", parts);
}

static json_t *alternation(json_t *alternatives) {
    return json_pack("{s:s, s:o}", "type", "Alternation", "alternatives", alternatives);
}

/* Build the standard letter range items: A-Z and a-z. */
static void add_letters(json_t *arr) {
    json_array_append_new(arr, range("A", "Z"));
    json_array_append_new(arr, range("a", "z"));
}

static void add_digits(json_t *arr) {
    json_array_append_new(arr, escape_digit());
}

static void add_hex(json_t *arr) {
    json_array_append_new(arr, range("A", "F"));
    json_array_append_new(arr, range("a", "f"));
    json_array_append_new(arr, range("0", "9"));
}

static void add_chars(json_t *arr, const char *s) {
    for (const char *p = s; *p; p++) {
        json_array_append_new(arr, class_lit(*p));
    }
}

static json_t *class_letters(void) { json_t *a = json_array(); add_letters(a); return char_class(a); }
static json_t *class_hex(void)     { json_t *a = json_array(); add_hex(a);     return char_class(a); }
static json_t *class_digits(void)  { json_t *a = json_array(); add_digits(a);  return char_class(a); }

static json_t *dig_n(int min, int max)  { return quant(class_digits(),  min, max); }
static json_t *hex_n(int min, int max)  { return quant(class_hex(),     min, max); }
static json_t *lett_n(int min, int max) { return quant(class_letters(), min, max); }

static char *dump(json_t *node) {
    char *s = json_dumps(node, JSON_COMPACT);
    json_decref(node);
    return s;
}

char *sl_email(void) {
    json_t *local_items = json_array();
    add_letters(local_items); add_digits(local_items); add_chars(local_items, "._%+-");
    json_t *domain_items = json_array();
    add_letters(domain_items); add_digits(domain_items); add_chars(domain_items, ".-");

    json_t *parts = json_array();
    json_array_append_new(parts, quant(char_class(local_items), 1, -1));
    json_array_append_new(parts, literal("@"));
    json_array_append_new(parts, quant(char_class(domain_items), 1, -1));
    json_array_append_new(parts, literal("."));
    json_array_append_new(parts, lett_n(2, -1));
    return dump(sequence(parts));
}

char *sl_url(void) {
    /* Build the four character-class buckets: base, with_q, with_frag, host. */
    json_t *parts = json_array();

    /* scheme = "http" + opt("s") */
    json_t *scheme_parts = json_array();
    json_array_append_new(scheme_parts, literal("http"));
    json_array_append_new(scheme_parts, opt(literal("s")));
    json_array_append_new(parts, sequence(scheme_parts));

    json_array_append_new(parts, literal("://"));

    /* host = [letters,digits,.,-]+ */
    json_t *host_items = json_array();
    add_letters(host_items); add_digits(host_items); add_chars(host_items, ".-");
    json_array_append_new(parts, quant(char_class(host_items), 1, -1));

    /* port = (?: ":" \d+ )? */
    json_t *port_seq = json_array();
    json_array_append_new(port_seq, literal(":"));
    json_array_append_new(port_seq, dig_n(1, -1));
    json_array_append_new(parts, opt(sequence(port_seq)));

    /* path = (?: "/" base* )? */
    json_t *base_items = json_array();
    add_letters(base_items); add_digits(base_items); add_chars(base_items, "/_-.~%&=:@!$'()*+,;");
    json_t *path_seq = json_array();
    json_array_append_new(path_seq, literal("/"));
    json_array_append_new(path_seq, quant(char_class(base_items), 0, -1));
    json_array_append_new(parts, opt(sequence(path_seq)));

    /* query = (?: "?" with_q* )? */
    json_t *with_q_items = json_array();
    add_letters(with_q_items); add_digits(with_q_items); add_chars(with_q_items, "/_-.~%&=:@!$'()*+,;?");
    json_t *query_seq = json_array();
    json_array_append_new(query_seq, literal("?"));
    json_array_append_new(query_seq, quant(char_class(with_q_items), 0, -1));
    json_array_append_new(parts, opt(sequence(query_seq)));

    /* fragment = (?: "#" with_frag* )? */
    json_t *with_frag_items = json_array();
    add_letters(with_frag_items); add_digits(with_frag_items); add_chars(with_frag_items, "/_-.~%&=:@!$'()*+,;?#");
    json_t *frag_seq = json_array();
    json_array_append_new(frag_seq, literal("#"));
    json_array_append_new(frag_seq, quant(char_class(with_frag_items), 0, -1));
    json_array_append_new(parts, opt(sequence(frag_seq)));

    return dump(sequence(parts));
}

char *sl_uuid(void) {
    json_t *parts = json_array();
    json_array_append_new(parts, hex_n(8, 8));
    json_array_append_new(parts, literal("-"));
    json_array_append_new(parts, hex_n(4, 4));
    json_array_append_new(parts, literal("-"));
    json_array_append_new(parts, hex_n(4, 4));
    json_array_append_new(parts, literal("-"));
    json_array_append_new(parts, hex_n(4, 4));
    json_array_append_new(parts, literal("-"));
    json_array_append_new(parts, hex_n(12, 12));
    return dump(sequence(parts));
}

char *sl_uuid_v4(void) {
    json_t *variant_items = json_array();
    add_chars(variant_items, "89ABab");

    json_t *parts = json_array();
    json_array_append_new(parts, hex_n(8, 8));
    json_array_append_new(parts, literal("-"));
    json_array_append_new(parts, hex_n(4, 4));
    json_array_append_new(parts, literal("-"));
    json_array_append_new(parts, literal("4"));
    json_array_append_new(parts, hex_n(3, 3));
    json_array_append_new(parts, literal("-"));
    json_array_append_new(parts, char_class(variant_items));
    json_array_append_new(parts, hex_n(3, 3));
    json_array_append_new(parts, literal("-"));
    json_array_append_new(parts, hex_n(12, 12));
    return dump(sequence(parts));
}

static json_t *build_ipv4(void) {
    json_t *parts = json_array();
    json_array_append_new(parts, dig_n(1, 3)); json_array_append_new(parts, literal("."));
    json_array_append_new(parts, dig_n(1, 3)); json_array_append_new(parts, literal("."));
    json_array_append_new(parts, dig_n(1, 3)); json_array_append_new(parts, literal("."));
    json_array_append_new(parts, dig_n(1, 3));
    return sequence(parts);
}

static json_t *build_ipv6(void) {
    json_t *parts = json_array();
    for (int i = 0; i < 7; i++) {
        json_array_append_new(parts, hex_n(1, 4));
        json_array_append_new(parts, literal(":"));
    }
    json_array_append_new(parts, hex_n(1, 4));
    return sequence(parts);
}

char *sl_ip_v4(void) { return dump(build_ipv4()); }
char *sl_ip_v6(void) { return dump(build_ipv6()); }

char *sl_ip_any(void) {
    json_t *alts = json_array();
    json_array_append_new(alts, build_ipv4());
    json_array_append_new(alts, build_ipv6());
    return dump(alternation(alts));
}

char *sl_date_time(void) {
    json_t *sign_items = json_array();
    add_chars(sign_items, "+-");

    json_t *frac_seq = json_array();
    json_array_append_new(frac_seq, literal("."));
    json_array_append_new(frac_seq, dig_n(1, -1));

    json_t *offset_seq = json_array();
    json_array_append_new(offset_seq, char_class(sign_items));
    json_array_append_new(offset_seq, dig_n(2, 2));
    json_array_append_new(offset_seq, literal(":"));
    json_array_append_new(offset_seq, dig_n(2, 2));

    json_t *tz_alts = json_array();
    json_array_append_new(tz_alts, literal("Z"));
    json_array_append_new(tz_alts, sequence(offset_seq));

    json_t *parts = json_array();
    json_array_append_new(parts, dig_n(4, 4)); json_array_append_new(parts, literal("-"));
    json_array_append_new(parts, dig_n(2, 2)); json_array_append_new(parts, literal("-"));
    json_array_append_new(parts, dig_n(2, 2));
    json_array_append_new(parts, literal("T"));
    json_array_append_new(parts, dig_n(2, 2)); json_array_append_new(parts, literal(":"));
    json_array_append_new(parts, dig_n(2, 2)); json_array_append_new(parts, literal(":"));
    json_array_append_new(parts, dig_n(2, 2));
    json_array_append_new(parts, opt(sequence(frac_seq)));
    json_array_append_new(parts, opt(alternation(tz_alts)));
    return dump(sequence(parts));
}
