#include "strling_essential.h"

/* Canonical lexical-shape helpers delegate by registry identity and do not
 * claim semantic validation. */

sl_pattern_t sl_email(void)
{
    return sl_stdlib_helper_v1("stdlib.email", SL_STDLIB_NO_VERSION);
}

sl_pattern_t sl_url(void)
{
    return sl_stdlib_helper_v1("stdlib.url", SL_STDLIB_NO_VERSION);
}

sl_pattern_t sl_uuid(void)
{
    return sl_stdlib_helper_v1("stdlib.uuid", SL_STDLIB_NULL_VERSION);
}

sl_pattern_t sl_uuid_v4(void)
{
    return sl_stdlib_helper_v1("stdlib.uuid", 4);
}

sl_pattern_t sl_ip_v4(void)
{
    return sl_stdlib_helper_v1("stdlib.ip", 4);
}

sl_pattern_t sl_ip_v6(void)
{
    return sl_stdlib_helper_v1("stdlib.ip", 6);
}

sl_pattern_t sl_ip_any(void)
{
    return sl_stdlib_helper_v1("stdlib.ip", SL_STDLIB_NULL_VERSION);
}

sl_pattern_t sl_date_time(void)
{
    return sl_stdlib_helper_v1("stdlib.date_time", SL_STDLIB_NO_VERSION);
}
