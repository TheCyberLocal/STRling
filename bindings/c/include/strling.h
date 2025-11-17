/*
 * Public API header for STRling C binding (scaffold)
 *
 * This header intentionally exposes minimal public symbols for now. Core
 * implementation details live under `src/core/` and are not exposed here.
 */
#ifndef STRLING_H
#define STRLING_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stddef.h>

/* Library version */
const char* strling_version(void);

#ifdef __cplusplus
}
#endif

#endif /* STRLING_H */
