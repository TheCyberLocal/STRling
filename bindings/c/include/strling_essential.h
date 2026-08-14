/*
 * STRling Essential — compatibility lexical-shape patterns for common
 * string formats. These helpers do not establish semantic validity or
 * complete standards conformance.
 *
 * Each helper returns a heap-allocated JSON AST string compatible with
 * `strling_compile`. The caller owns the returned buffer and must
 * release it with `free()`.
 */

#ifndef STRLING_ESSENTIAL_H
#define STRLING_ESSENTIAL_H

#ifdef __cplusplus
extern "C" {
#endif

/* Email-like lexical shape; RFC 5322 conformance is not claimed. */
char *sl_email(void);

/* HTTP(S) URL-like lexical shape; RFC 3986 conformance is not claimed. */
char *sl_url(void);

/* RFC 9562 8-4-4-4-12 UUID text shape; field validity is not claimed. */
char *sl_uuid(void);

/* RFC 9562 UUIDv4 text shape with version and variant nibbles. */
char *sl_uuid_v4(void);

/* Four-component IPv4-like lexical shape; octet ranges are not checked. */
char *sl_ip_v4(void);

/* Eight-group IPv6 lexical shape from RFC 4291 section 2.2. */
char *sl_ip_v6(void);

/* IP address pattern accepting either IPv4 or IPv6. */
char *sl_ip_any(void);

/* Timestamp-like lexical shape; RFC 3339 / ISO 8601 validity is not claimed. */
char *sl_date_time(void);

#ifdef __cplusplus
}
#endif

#endif /* STRLING_ESSENTIAL_H */
