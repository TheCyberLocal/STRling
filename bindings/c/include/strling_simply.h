/* STRling Simply 1.1 construction adapter for C. */
#ifndef STRLING_SIMPLY_H
#define STRLING_SIMPLY_H

#include <stddef.h>
#include <stdint.h>

#include "strling.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct sl_value_v1 sl_value_v1;
typedef sl_value_v1 *sl_pattern_t;

typedef struct sl_options_v1 {
    uint32_t case_insensitive;
    uint32_t ascii_character_domain;
    uint32_t include_line_terminators;
} sl_options_v1;

enum {
    SL_STDLIB_NO_VERSION = -1,
    SL_STDLIB_NULL_VERSION = 0,
};

sl_options_v1 sl_options_default_v1(void);

sl_pattern_t sl_literal(const char *text);
sl_pattern_t sl_digit(int count);
sl_pattern_t sl_any_of(const char *characters);
sl_pattern_t sl_dot(void);
sl_pattern_t sl_start(void);
sl_pattern_t sl_end(void);
sl_pattern_t sl_capture(sl_pattern_t value);
sl_pattern_t sl_may(sl_pattern_t value);
sl_pattern_t sl_merge(int count, ...);

/* On success, transfer ownership of every element into one sequence. */
sl_pattern_t sl_merge_array_v1(size_t count, sl_pattern_t const *values);

/* Generic registry selection; unknown helpers are rejected by Simply replay. */
sl_pattern_t sl_stdlib_helper_v1(const char *helper_id, int version);

/* Serialize one immutable construction graph as a Simply 1.1 BuilderRequest. */
char *sl_builder_request_json_v1(const sl_pattern_t value,
                                 const sl_options_v1 *options);

/* Execute the generated BuilderRequest through strling.c-abi v1. */
strling_c_result_v1 sl_compile_v1(const sl_pattern_t value,
                                  const sl_options_v1 *options);

void sl_string_free_v1(char *value);
void sl_free(sl_pattern_t value);

#ifdef __cplusplus
}
#endif

#endif /* STRLING_SIMPLY_H */
