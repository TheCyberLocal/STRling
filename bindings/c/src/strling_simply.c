#include "strling_simply.h"

#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef enum sl_operation_v1 {
    SL_OPERATION_LITERAL,
    SL_OPERATION_DIGIT,
    SL_OPERATION_CHARACTER_SET,
    SL_OPERATION_WILDCARD,
    SL_OPERATION_POSITION,
    SL_OPERATION_CAPTURE,
    SL_OPERATION_REPEAT,
    SL_OPERATION_SEQUENCE,
    SL_OPERATION_STDLIB_HELPER,
} sl_operation_v1;

struct sl_value_v1 {
    sl_operation_v1 operation;
    char *text;
    int minimum;
    int maximum;
    int version;
    size_t child_count;
    struct sl_value_v1 **children;
};

typedef struct text_buffer {
    char *data;
    size_t length;
    size_t capacity;
} text_buffer;

typedef struct serialization_state {
    text_buffer steps;
    size_t next_id;
    size_t node_count;
    int first_step;
} serialization_state;

static char *copy_string(const char *value)
{
    size_t length;
    char *copy;
    if (value == NULL) {
        return NULL;
    }
    length = strlen(value);
    if (length == SIZE_MAX) {
        return NULL;
    }
    copy = (char *)malloc(length + 1);
    if (copy != NULL) {
        memcpy(copy, value, length + 1);
    }
    return copy;
}

static int buffer_reserve(text_buffer *buffer, size_t additional)
{
    size_t required;
    size_t capacity;
    char *replacement;
    if (additional > SIZE_MAX - buffer->length - 1) {
        return 0;
    }
    required = buffer->length + additional + 1;
    if (required <= buffer->capacity) {
        return 1;
    }
    capacity = buffer->capacity == 0 ? 256 : buffer->capacity;
    while (capacity < required) {
        if (capacity > SIZE_MAX / 2) {
            capacity = required;
            break;
        }
        capacity *= 2;
    }
    replacement = (char *)realloc(buffer->data, capacity);
    if (replacement == NULL) {
        return 0;
    }
    buffer->data = replacement;
    buffer->capacity = capacity;
    if (buffer->length == 0) {
        buffer->data[0] = '\0';
    }
    return 1;
}

static int buffer_append_n(text_buffer *buffer, const char *value, size_t length)
{
    if (!buffer_reserve(buffer, length)) {
        return 0;
    }
    memcpy(buffer->data + buffer->length, value, length);
    buffer->length += length;
    buffer->data[buffer->length] = '\0';
    return 1;
}

static int buffer_append(text_buffer *buffer, const char *value)
{
    return buffer_append_n(buffer, value, strlen(value));
}

static int buffer_append_size(text_buffer *buffer, size_t value)
{
    char digits[32];
    int written = snprintf(digits, sizeof(digits), "%zu", value);
    return written > 0 && (size_t)written < sizeof(digits) &&
           buffer_append_n(buffer, digits, (size_t)written);
}

static int buffer_append_int(text_buffer *buffer, int value)
{
    char digits[32];
    int written = snprintf(digits, sizeof(digits), "%d", value);
    return written > 0 && (size_t)written < sizeof(digits) &&
           buffer_append_n(buffer, digits, (size_t)written);
}

static int buffer_append_json_string_n(text_buffer *buffer,
                                       const char *value,
                                       size_t length)
{
    static const char hex[] = "0123456789abcdef";
    size_t index;
    if (!buffer_append(buffer, "\"")) {
        return 0;
    }
    for (index = 0; index < length; ++index) {
        unsigned char byte = (unsigned char)value[index];
        if (byte == '"' || byte == '\\') {
            char escaped[2] = {'\\', (char)byte};
            if (!buffer_append_n(buffer, escaped, sizeof(escaped))) {
                return 0;
            }
        } else if (byte < 0x20) {
            char escaped[6] = {'\\', 'u', '0', '0', hex[byte >> 4],
                               hex[byte & 0x0f]};
            if (!buffer_append_n(buffer, escaped, sizeof(escaped))) {
                return 0;
            }
        } else if (!buffer_append_n(buffer, value + index, 1)) {
            return 0;
        }
    }
    return buffer_append(buffer, "\"");
}

static int buffer_append_json_string(text_buffer *buffer, const char *value)
{
    return value != NULL &&
           buffer_append_json_string_n(buffer, value, strlen(value));
}

static void buffer_dispose(text_buffer *buffer)
{
    free(buffer->data);
    buffer->data = NULL;
    buffer->length = 0;
    buffer->capacity = 0;
}

static sl_pattern_t new_value(sl_operation_v1 operation, size_t child_count)
{
    sl_pattern_t value = (sl_pattern_t)calloc(1, sizeof(*value));
    if (value == NULL) {
        return NULL;
    }
    value->operation = operation;
    value->version = SL_STDLIB_NO_VERSION;
    if (child_count != 0) {
        value->children =
            (sl_pattern_t *)calloc(child_count, sizeof(*value->children));
        if (value->children == NULL) {
            free(value);
            return NULL;
        }
        value->child_count = child_count;
    }
    return value;
}

static sl_pattern_t unary_value(sl_operation_v1 operation, sl_pattern_t child)
{
    sl_pattern_t value;
    if (child == NULL) {
        return NULL;
    }
    value = new_value(operation, 1);
    if (value == NULL) {
        return NULL;
    }
    value->children[0] = child;
    return value;
}

static size_t utf8_scalar_width(const unsigned char *value, size_t remaining)
{
    uint32_t codepoint;
    size_t width;
    size_t index;
    if (remaining == 0) {
        return 0;
    }
    if (value[0] < 0x80) {
        return 1;
    }
    if ((value[0] & 0xe0) == 0xc0) {
        width = 2;
        codepoint = value[0] & 0x1f;
    } else if ((value[0] & 0xf0) == 0xe0) {
        width = 3;
        codepoint = value[0] & 0x0f;
    } else if ((value[0] & 0xf8) == 0xf0) {
        width = 4;
        codepoint = value[0] & 0x07;
    } else {
        return 0;
    }
    if (width > remaining) {
        return 0;
    }
    for (index = 1; index < width; ++index) {
        if ((value[index] & 0xc0) != 0x80) {
            return 0;
        }
        codepoint = (codepoint << 6) | (value[index] & 0x3f);
    }
    if ((width == 2 && codepoint < 0x80) ||
        (width == 3 && codepoint < 0x800) ||
        (width == 4 && codepoint < 0x10000) ||
        (codepoint >= 0xd800 && codepoint <= 0xdfff) || codepoint > 0x10ffff) {
        return 0;
    }
    return width;
}

static int valid_scalar_string(const char *value)
{
    const unsigned char *cursor = (const unsigned char *)value;
    size_t remaining;
    if (value == NULL || *value == '\0') {
        return 0;
    }
    remaining = strlen(value);
    while (remaining != 0) {
        size_t width = utf8_scalar_width(cursor, remaining);
        if (width == 0) {
            return 0;
        }
        cursor += width;
        remaining -= width;
    }
    return 1;
}

sl_options_v1 sl_options_default_v1(void)
{
    sl_options_v1 options = {0, 0, 0};
    return options;
}

sl_pattern_t sl_literal(const char *text)
{
    sl_pattern_t value;
    if (text == NULL) {
        return NULL;
    }
    value = new_value(SL_OPERATION_LITERAL, 0);
    if (value != NULL) {
        value->text = copy_string(text);
        if (value->text == NULL) {
            sl_free(value);
            return NULL;
        }
    }
    return value;
}

sl_pattern_t sl_digit(int count)
{
    sl_pattern_t digit;
    sl_pattern_t repeat;
    if (count <= 0) {
        return NULL;
    }
    digit = new_value(SL_OPERATION_DIGIT, 0);
    if (digit == NULL || count == 1) {
        return digit;
    }
    repeat = unary_value(SL_OPERATION_REPEAT, digit);
    if (repeat == NULL) {
        sl_free(digit);
        return NULL;
    }
    repeat->minimum = count;
    repeat->maximum = count;
    return repeat;
}

sl_pattern_t sl_any_of(const char *characters)
{
    sl_pattern_t value;
    if (!valid_scalar_string(characters)) {
        return NULL;
    }
    value = new_value(SL_OPERATION_CHARACTER_SET, 0);
    if (value != NULL) {
        value->text = copy_string(characters);
        if (value->text == NULL) {
            sl_free(value);
            return NULL;
        }
    }
    return value;
}

sl_pattern_t sl_dot(void)
{
    return new_value(SL_OPERATION_WILDCARD, 0);
}

sl_pattern_t sl_start(void)
{
    sl_pattern_t value = new_value(SL_OPERATION_POSITION, 0);
    if (value != NULL) {
        value->text = copy_string("line_start");
    }
    return value;
}

sl_pattern_t sl_end(void)
{
    sl_pattern_t value = new_value(SL_OPERATION_POSITION, 0);
    if (value != NULL) {
        value->text = copy_string("line_end");
    }
    return value;
}

sl_pattern_t sl_capture(sl_pattern_t value)
{
    return unary_value(SL_OPERATION_CAPTURE, value);
}

sl_pattern_t sl_may(sl_pattern_t value)
{
    sl_pattern_t repeat = unary_value(SL_OPERATION_REPEAT, value);
    if (repeat != NULL) {
        repeat->minimum = 0;
        repeat->maximum = 1;
    }
    return repeat;
}

sl_pattern_t sl_merge(int count, ...)
{
    va_list arguments;
    sl_pattern_t value;
    int index;
    if (count <= 0) {
        return NULL;
    }
    value = new_value(SL_OPERATION_SEQUENCE, (size_t)count);
    if (value == NULL) {
        return NULL;
    }
    va_start(arguments, count);
    for (index = 0; index < count; ++index) {
        value->children[index] = va_arg(arguments, sl_pattern_t);
        if (value->children[index] == NULL) {
            va_end(arguments);
            sl_free(value);
            return NULL;
        }
    }
    va_end(arguments);
    if (count == 1) {
        sl_pattern_t only = value->children[0];
        value->children[0] = NULL;
        sl_free(value);
        return only;
    }
    return value;
}

sl_pattern_t sl_stdlib_helper_v1(const char *helper_id, int version)
{
    sl_pattern_t value;
    if (helper_id == NULL) {
        return NULL;
    }
    value = new_value(SL_OPERATION_STDLIB_HELPER, 0);
    if (value != NULL) {
        value->text = copy_string(helper_id);
        value->version = version;
        if (value->text == NULL) {
            sl_free(value);
            return NULL;
        }
    }
    return value;
}

static int append_step_id(text_buffer *buffer, size_t id)
{
    return buffer_append(buffer, "\"step") && buffer_append_size(buffer, id) &&
           buffer_append(buffer, "\"");
}

static int begin_step(serialization_state *state, size_t id, const char *operation)
{
    if (!state->first_step && !buffer_append(&state->steps, ",")) {
        return 0;
    }
    state->first_step = 0;
    return buffer_append(&state->steps, "{\"step_id\":") &&
           append_step_id(&state->steps, id) &&
           buffer_append(&state->steps, ",\"operation\":") &&
           buffer_append_json_string(&state->steps, operation) &&
           buffer_append(&state->steps, ",\"arguments\":{");
}

static int emit_node(serialization_state *state,
                     const sl_pattern_t value,
                     size_t depth,
                     size_t *out_id)
{
    size_t id;
    size_t *child_ids = NULL;
    size_t index;
    int ok = 0;
    if (value == NULL || depth > 256 || state->node_count >= 4096) {
        return 0;
    }
    id = state->next_id++;
    state->node_count++;
    if (value->child_count != 0) {
        child_ids = (size_t *)calloc(value->child_count, sizeof(*child_ids));
        if (child_ids == NULL) {
            return 0;
        }
        for (index = 0; index < value->child_count; ++index) {
            if (!emit_node(state, value->children[index], depth + 1,
                           &child_ids[index])) {
                goto complete;
            }
        }
    }

    switch (value->operation) {
    case SL_OPERATION_LITERAL:
        ok = begin_step(state, id, "literal") &&
             buffer_append(&state->steps, "\"text\":") &&
             buffer_append_json_string(&state->steps, value->text) &&
             buffer_append(&state->steps, "}}");
        break;
    case SL_OPERATION_DIGIT:
        ok = begin_step(state, id, "character_set") &&
             buffer_append(
                 &state->steps,
                 "\"negated\":false,\"members\":[{\"kind\":\"builtin\","
                 "\"name\":\"digit\",\"negated\":false}]}}");
        break;
    case SL_OPERATION_CHARACTER_SET: {
        const unsigned char *cursor = (const unsigned char *)value->text;
        size_t remaining = strlen(value->text);
        int first = 1;
        ok = begin_step(state, id, "character_set") &&
             buffer_append(&state->steps,
                           "\"negated\":false,\"members\":[");
        while (ok && remaining != 0) {
            size_t width = utf8_scalar_width(cursor, remaining);
            ok = width != 0 &&
                 (first || buffer_append(&state->steps, ",")) &&
                 buffer_append(&state->steps,
                               "{\"kind\":\"literal\",\"value\":") &&
                 buffer_append_json_string_n(&state->steps,
                                             (const char *)cursor, width) &&
                 buffer_append(&state->steps, "}");
            first = 0;
            cursor += width;
            remaining -= width;
        }
        ok = ok && buffer_append(&state->steps, "]}}");
        break;
    }
    case SL_OPERATION_WILDCARD:
        ok = begin_step(state, id, "wildcard") &&
             buffer_append(&state->steps, "}}");
        break;
    case SL_OPERATION_POSITION:
        ok = begin_step(state, id, "position") &&
             buffer_append(&state->steps, "\"position\":") &&
             buffer_append_json_string(&state->steps, value->text) &&
             buffer_append(&state->steps, "}}");
        break;
    case SL_OPERATION_CAPTURE:
        ok = begin_step(state, id, "capture") &&
             buffer_append(&state->steps, "\"value\":") &&
             append_step_id(&state->steps, child_ids[0]) &&
             buffer_append(&state->steps, ",\"capture_key\":\"capture.step") &&
             buffer_append_size(&state->steps, id) &&
             buffer_append(&state->steps, "\"}}");
        break;
    case SL_OPERATION_REPEAT:
        ok = begin_step(state, id, "repeat") &&
             buffer_append(&state->steps, "\"value\":") &&
             append_step_id(&state->steps, child_ids[0]) &&
             buffer_append(&state->steps, ",\"min\":") &&
             buffer_append_int(&state->steps, value->minimum) &&
             buffer_append(&state->steps, ",\"max\":") &&
             buffer_append_int(&state->steps, value->maximum) &&
             buffer_append(&state->steps, ",\"mode\":\"greedy\"}}");
        break;
    case SL_OPERATION_SEQUENCE:
        ok = begin_step(state, id, "sequence") &&
             buffer_append(&state->steps, "\"values\":[");
        for (index = 0; ok && index < value->child_count; ++index) {
            ok = (index == 0 || buffer_append(&state->steps, ",")) &&
                 append_step_id(&state->steps, child_ids[index]);
        }
        ok = ok && buffer_append(&state->steps, "]}}");
        break;
    case SL_OPERATION_STDLIB_HELPER:
        ok = begin_step(state, id, "stdlib_helper") &&
             buffer_append(&state->steps, "\"helper_id\":") &&
             buffer_append_json_string(&state->steps, value->text) &&
             buffer_append(&state->steps, ",\"parameters\":{");
        if (ok && value->version != SL_STDLIB_NO_VERSION) {
            ok = buffer_append(&state->steps, "\"version\":") &&
                 (value->version == SL_STDLIB_NULL_VERSION
                      ? buffer_append(&state->steps, "null")
                      : buffer_append_int(&state->steps, value->version));
        }
        ok = ok && buffer_append(&state->steps, "}}}");
        break;
    }

complete:
    free(child_ids);
    if (ok) {
        *out_id = id;
    }
    return ok;
}

char *sl_builder_request_json_v1(const sl_pattern_t value,
                                 const sl_options_v1 *options)
{
    serialization_state state;
    text_buffer request = {0};
    sl_options_v1 effective = sl_options_default_v1();
    size_t root_id;
    int ok;
    memset(&state, 0, sizeof(state));
    state.first_step = 1;
    if (options != NULL) {
        effective = *options;
    }
    if (effective.case_insensitive > 1 ||
        effective.ascii_character_domain > 1 ||
        effective.include_line_terminators > 1 ||
        !emit_node(&state, value, 0, &root_id)) {
        buffer_dispose(&state.steps);
        return NULL;
    }

    ok = buffer_append(
             &request,
             "{\"protocol_version\":\"1.1.0\",\"contract_version\":\"1.0.0\","
             "\"specification_version\":\"1.0-draft.1\","
             "\"identity_namespace\":\"c.adapter\",\"semantic_options\":{"
             "\"case_matching\":") &&
         buffer_append_json_string(
             &request,
             effective.case_insensitive ? "insensitive" : "sensitive") &&
         buffer_append(&request,
                       ",\"text_model\":\"unicode_scalar_values\","
                       "\"builtin_character_domain\":") &&
         buffer_append_json_string(
             &request,
             effective.ascii_character_domain ? "ascii" : "unicode") &&
         buffer_append(&request, ",\"wildcard_line_terminators\":") &&
         buffer_append_json_string(
             &request,
             effective.include_line_terminators ? "include" : "exclude") &&
         buffer_append(&request, "},\"steps\":[") &&
         buffer_append_n(&request, state.steps.data, state.steps.length) &&
         buffer_append(&request, "],\"root_step_id\":") &&
         append_step_id(&request, root_id) &&
         buffer_append(
             &request,
             ",\"compile\":{\"requested_outputs\":[\"semantic\",\"analysis\"],"
             "\"compiler_options\":{\"partial_semantics\":\"forbid\","
             "\"diagnostic_policy\":{\"minimum_severity\":\"warning\"}}}}}");
    buffer_dispose(&state.steps);
    if (!ok) {
        buffer_dispose(&request);
        return NULL;
    }
    return request.data;
}

strling_c_result_v1 sl_compile_v1(const sl_pattern_t value,
                                  const sl_options_v1 *options)
{
    char *request = sl_builder_request_json_v1(value, options);
    strling_c_result_v1 result;
    if (request == NULL) {
        result.transport_status = STRLING_INTEROP_STATUS_INVALID_ARGUMENT;
        result.response.data = NULL;
        result.response.len = 0;
        return result;
    }
    result = strling_simply_compile_json_v1(request, NULL);
    free(request);
    return result;
}

void sl_string_free_v1(char *value)
{
    free(value);
}

void sl_free(sl_pattern_t value)
{
    size_t index;
    if (value == NULL) {
        return;
    }
    for (index = 0; index < value->child_count; ++index) {
        sl_free(value->children[index]);
    }
    free(value->children);
    free(value->text);
    free(value);
}
