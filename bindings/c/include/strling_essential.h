/* Canonical lexical-shape helper selections for the C Simply adapter.
 * These builders do not claim semantic validation. */
#ifndef STRLING_ESSENTIAL_H
#define STRLING_ESSENTIAL_H

#include "strling_simply.h"

#ifdef __cplusplus
extern "C" {
#endif

sl_pattern_t sl_email(void);
sl_pattern_t sl_url(void);
sl_pattern_t sl_uuid(void);
sl_pattern_t sl_uuid_v4(void);
sl_pattern_t sl_ip_v4(void);
sl_pattern_t sl_ip_v6(void);
sl_pattern_t sl_ip_any(void);
sl_pattern_t sl_date_time(void);

#ifdef __cplusplus
}
#endif

#endif /* STRLING_ESSENTIAL_H */
