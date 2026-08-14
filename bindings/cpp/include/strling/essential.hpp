/**
 * @file essential.hpp
 * @brief STRling Essential — compatibility lexical-shape patterns for common
 *        string formats, without semantic-validity or conformance claims.
 *
 * Each helper returns a portable regex string (PCRE2-compatible, also valid
 * under ECMAScript and std::regex's default grammar). The patterns are
 * unanchored; callers that require full-string matching should wrap them in
 * `^(?: ... )$`.
 *
 * Standards references identify lexical inspiration or a documented subset;
 * exact scope and non-claims live in spec/stdlib/stdlib-guarantee-audit.json.
 */

#ifndef STRLING_ESSENTIAL_HPP
#define STRLING_ESSENTIAL_HPP

#include <string>

namespace strling::essential {

/// Email-like lexical shape; RFC 5322 conformance is not claimed.
std::string email();

/// HTTP(S) URL-like lexical shape; RFC 3986 conformance is not claimed.
std::string url();

/// RFC 9562 8-4-4-4-12 text shape. `version == 4` constrains the
/// version/variant nibbles; any other value performs no field interpretation.
std::string uuid(int version = 0);

/// IP-like lexical shape. `version == 4` selects four 1-3 digit groups and
/// `version == 6` selects eight hex groups; no numeric address validity claim.
std::string ip(int version = 0);

/// Timestamp-like lexical shape with optional fraction and offset; calendar,
/// clock, RFC 3339, and ISO 8601 validity are not claimed.
std::string date_time();

} // namespace strling::essential

#endif // STRLING_ESSENTIAL_HPP
