#ifndef STRLING_CPP_ESSENTIAL_HPP
#define STRLING_CPP_ESSENTIAL_HPP

#include "strling/simply.hpp"

namespace strling::essential {

// Canonical lexical-shape builders; these helpers do not claim semantic
// validation.

[[nodiscard]] simply::pattern email();
[[nodiscard]] simply::pattern url();
[[nodiscard]] simply::pattern uuid();
[[nodiscard]] simply::pattern uuid_v4();
[[nodiscard]] simply::pattern ip_v4();
[[nodiscard]] simply::pattern ip_v6();
[[nodiscard]] simply::pattern ip_any();
[[nodiscard]] simply::pattern date_time();

} // namespace strling::essential

#endif // STRLING_CPP_ESSENTIAL_HPP
