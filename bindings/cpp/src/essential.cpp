/**
 * @file essential.cpp
 * @brief Implementation of the Essential compatibility lexical-shape helpers.
 */

#include "strling/essential.hpp"

namespace strling::essential {

std::string email() {
    return "[A-Za-z\\d._%+\\-]+@[A-Za-z\\d.\\-]+\\.[A-Za-z]{2,}";
}

std::string url() {
    // scheme :// host (:port)? (/path)? (?query)? (#fragment)?
    const std::string base    = "[A-Za-z\\d/_\\-.~%&=:@!$'()*+,;]";
    const std::string with_q  = "[A-Za-z\\d/_\\-.~%&=:@!$'()*+,;?]";
    const std::string with_h  = "[A-Za-z\\d/_\\-.~%&=:@!$'()*+,;?#]";
    return std::string("https?://[A-Za-z\\d.\\-]+(?::\\d+)?")
         + "(?:/" + base + "*)?"
         + "(?:\\?" + with_q + "*)?"
         + "(?:#" + with_h + "*)?";
}

std::string uuid(int version) {
    if (version == 4) {
        return "[A-Fa-f0-9]{8}-[A-Fa-f0-9]{4}-4[A-Fa-f0-9]{3}-[89ABab][A-Fa-f0-9]{3}-[A-Fa-f0-9]{12}";
    }
    return "[A-Fa-f0-9]{8}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{12}";
}

static std::string ipv4() { return "\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}"; }
static std::string ipv6() {
    // Eight 1-4 hex groups separated by ':'.
    std::string g = "[A-Fa-f0-9]{1,4}";
    std::string out;
    for (int i = 0; i < 7; ++i) { out += g; out += ':'; }
    out += g;
    return out;
}

std::string ip(int version) {
    if (version == 4) return ipv4();
    if (version == 6) return ipv6();
    return std::string("(?:") + ipv4() + "|" + ipv6() + ")";
}

std::string date_time() {
    return "\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(?:\\.\\d+)?(?:Z|[+\\-]\\d{2}:\\d{2})?";
}

} // namespace strling::essential
