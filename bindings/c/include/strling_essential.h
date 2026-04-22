/*
 * STRling Essential — RFC-grounded patterns for the most commonly
 * validated string formats (email, URL, UUID, IP, dateTime).
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

/* Email address pattern (RFC 5322 addr-spec). */
char *sl_email(void);

/* HTTP / HTTPS URL pattern (RFC 3986 generic syntax). */
char *sl_url(void);

/* UUID pattern (RFC 4122). */
char *sl_uuid(void);

/* UUID v4 pattern (RFC 4122 §4.4). */
char *sl_uuid_v4(void);

/* IPv4 address pattern (RFC 791). */
char *sl_ip_v4(void);

/* IPv6 address pattern (RFC 4291, full form). */
char *sl_ip_v6(void);

/* IP address pattern accepting either IPv4 or IPv6. */
char *sl_ip_any(void);

/* ISO 8601 / RFC 3339 datetime pattern. */
char *sl_date_time(void);

#ifdef __cplusplus
}
#endif

#endif /* STRLING_ESSENTIAL_H */
