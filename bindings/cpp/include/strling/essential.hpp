/**
 * @file essential.hpp
 * @brief STRling Essential — RFC-grounded patterns for the most commonly
 *        validated string formats.
 *
 * Each helper returns a portable regex string (PCRE2-compatible, also valid
 * under ECMAScript and std::regex's default grammar). The patterns are
 * unanchored; callers that require full-string matching should wrap them in
 * `^(?: ... )$`.
 *
 * References:
 *   - email     : RFC 5322 addr-spec (commonly accepted subset)
 *   - url       : RFC 3986 generic URI syntax (HTTP / HTTPS)
 *   - uuid      : RFC 4122 (default any version, optional v4 strict form)
 *   - ip        : RFC 791 (IPv4) and RFC 4291 §2.2 full form (IPv6)
 *   - date_time : RFC 3339 / ISO 8601 calendar dates with optional offset
 */

#ifndef STRLING_ESSENTIAL_HPP
#define STRLING_ESSENTIAL_HPP

#include <string>

namespace strling::essential {

/// RFC 5322 email address pattern (commonly accepted subset).
std::string email();

/// RFC 3986 HTTP / HTTPS URL pattern.
std::string url();

/// RFC 4122 UUID pattern. `version == 4` enforces the v4 strict form;
/// any other value accepts every UUID version.
std::string uuid(int version = 0);

/// IP address pattern. `version == 4` and `version == 6` return the
/// strict family; any other value accepts either.
std::string ip(int version = 0);

/// RFC 3339 / ISO 8601 datetime pattern with optional fractional seconds
/// and timezone offset.
std::string date_time();

} // namespace strling::essential

#endif // STRLING_ESSENTIAL_HPP
