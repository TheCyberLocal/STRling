# STRling - C Binding

> Part of the [STRling Project](https://github.com/TheCyberLocal/STRling/blob/main/README.md)

<table>
  <tr>
    <td style="padding: 10px;"><img src="https://raw.githubusercontent.com/TheCyberLocal/STRling/main/strling_logo.jpg" alt="STRling Logo" width="100" /></td>
    <td style="padding: 10px;">
      <strong>The Universal Regular Expression Compiler.</strong><br><br>
      STRling is a next-generation production-grade syntax designed to make Regex readable, maintainable, and robust. It abstracts the cryptic nature of raw regex strings into a clean, object-oriented, and strictly typed interface that compiles to standard PCRE2 (or native) patterns.
    </td>
  </tr>
</table>

## 💿 Installation

Build the C binding from source (requires a C compiler and make):

```bash
cd bindings/c
make
```

## 📦 Usage

### Simply API (Recommended)

The Simply API provides a fluent, ergonomic interface for building patterns with minimal boilerplate.

Here is how to match a US Phone number (e.g., `555-0199`) using the **Simply API**:

```c
#include <stdio.h>
#include "strling.h"
#include "strling_simply.h"

int main(void) {
    /* Build a US Phone Number pattern using the Simply API.
     * Pattern: ^(\d{3})[-. ]?(\d{3})[-. ]?(\d{4})$
     * Matches: 555-0199, 555.0199, 555 0199, 5550199
     */
    sl_pattern_t phone = sl_seq(7,
        sl_start(),
        sl_capture(sl_digit(3)),
        sl_optional(sl_any_of("-. ")),
        sl_capture(sl_digit(3)),
        sl_optional(sl_any_of("-. ")),
        sl_capture(sl_digit(4)),
        sl_end()
    );

    /* NOTE: The C binding currently compiles from JSON AST to PCRE2.
     * In the future, we'll add AST->JSON serialization to enable direct
     * compilation. For now, the Simply API constructs the correct AST
     * structure that can be used with future serialization capabilities.
     * 
     * The JSON below represents the same pattern for demonstration.
     */
    const char* phone_json =
        "{\"type\":\"Sequence\",\"parts\":["
        "{\"type\":\"Anchor\",\"at\":\"Start\"},"
        "{\"type\":\"Group\",\"capturing\":true,\"body\":{\"type\":\"Quantifier\",\"min\":3,\"max\":3,\"mode\":\"Greedy\",\"target\":{\"type\":\"CharacterClass\",\"negated\":false,\"members\":[{\"type\":\"Escape\",\"kind\":\"digit\"}]}}},"
        "{\"type\":\"Quantifier\",\"min\":0,\"max\":1,\"mode\":\"Greedy\",\"target\":{\"type\":\"CharacterClass\",\"negated\":false,\"members\":[{\"type\":\"Literal\",\"value\":\"-\"},{\"type\":\"Literal\",\"value\":\".\"},{\"type\":\"Literal\",\"value\":\" \"}]}},"
        "{\"type\":\"Group\",\"capturing\":true,\"body\":{\"type\":\"Quantifier\",\"min\":3,\"max\":3,\"mode\":\"Greedy\",\"target\":{\"type\":\"CharacterClass\",\"negated\":false,\"members\":[{\"type\":\"Escape\",\"kind\":\"digit\"}]}}},"
        "{\"type\":\"Quantifier\",\"min\":0,\"max\":1,\"mode\":\"Greedy\",\"target\":{\"type\":\"CharacterClass\",\"negated\":false,\"members\":[{\"type\":\"Literal\",\"value\":\"-\"},{\"type\":\"Literal\",\"value\":\".\"},{\"type\":\"Literal\",\"value\":\" \"}]}},"
        "{\"type\":\"Group\",\"capturing\":true,\"body\":{\"type\":\"Quantifier\",\"min\":4,\"max\":4,\"mode\":\"Greedy\",\"target\":{\"type\":\"CharacterClass\",\"negated\":false,\"members\":[{\"type\":\"Escape\",\"kind\":\"digit\"}]}}},"
        "{\"type\":\"Anchor\",\"at\":\"End\"}]}";

    strling_result_t result = strling_compile_compat(phone_json, NULL);
    if (result.error_code == STRling_OK) {
        printf("compiled: %s\n", result.pcre2_pattern);
    } else {
        fprintf(stderr, "compile error: %s\n", result.error_message);
    }

    /* Cleanup - single root free handles all child nodes */
    strling_result_free_compat(&result);
    sl_free(phone);  /* Equivalent to strling_ast_node_free(phone) */

    /* This example compiles to: ^([\d]{3})[\-. ]?([\d]{3})[\-. ]?([\d]{4})$ */
    return (result.error_code == STRling_OK) ? 0 : 1;
}
```

**Key Features:**
- **Zero Boilerplate:** Simple, readable pattern construction with `sl_*` functions
- **Memory Safety:** Single `sl_free(phone)` call cleans up entire pattern
- **Fluent API:** Chain operations naturally with `sl_seq`, `sl_capture`, `sl_optional`, etc.

### Low-Level API

For advanced use cases requiring direct AST manipulation, the low-level API is also available:

<details>
<summary>Click to expand low-level API example</summary>

```c
/* Build the STRling AST using the thin C helpers and then compile the
 * equivalent JSON AST. The C binding supplies convenient constructors
 * and matching free() helpers for every node type.
 *
 * Note: comments and logic below are intentionally identical to the
 * Python reference example to provide a one-to-one mental model for
 * readers switching languages.
 */

#include <stdio.h>
#include "strling.h"
#include "core/nodes.h"

int main(void) {
    // Start of line.
    // Match the area code (3 digits)
    STRlingASTNode* area = strling_ast_group_create(true,
        strling_ast_quant_create(strling_ast_lit_create("\\d"), 3, 3, "Greedy"),
        NULL, false);

    // Optional separator: [-. ]
    STRlingClassItem* sep_items_a[3] = {
        strling_class_literal_create("-"),
        strling_class_literal_create("."),
        strling_class_literal_create(" ")
    };
    STRlingASTNode* sep_a = strling_ast_charclass_create(false, sep_items_a, 3);
    STRlingASTNode* opt_sep_a = strling_ast_quant_create(sep_a, 0, 1, "Greedy");

    // Match the central office code (3 digits)
    STRlingASTNode* central = strling_ast_group_create(true,
        strling_ast_quant_create(strling_ast_lit_create("\\d"), 3, 3, "Greedy"),
        NULL, false);

    // Optional separator: [-. ]
    STRlingClassItem* sep_items_b[3] = {
        strling_class_literal_create("-"),
        strling_class_literal_create("."),
        strling_class_literal_create(" ")
    };
    STRlingASTNode* sep_b = strling_ast_charclass_create(false, sep_items_b, 3);
    STRlingASTNode* opt_sep_b = strling_ast_quant_create(sep_b, 0, 1, "Greedy");

    // Match the station number (4 digits)
    STRlingASTNode* station = strling_ast_group_create(true,
        strling_ast_quant_create(strling_ast_lit_create("\\d"), 4, 4, "Greedy"),
        NULL, false);

    // End of line.
    STRlingASTNode* parts[7] = {
        strling_ast_anchor_create("Start"),
        area,
        opt_sep_a,
        central,
        opt_sep_b,
        station,
        strling_ast_anchor_create("End"),
    };

    STRlingASTNode* ast = strling_ast_seq_create(parts, 7);

    /* The public compiler expects a JSON AST. For clarity we provide the
     * JSON string equivalent (in real code you can serialize the AST into
     * JSON before calling the compiler).
     */
    const char* phone_json =
        "{\"type\":\"Sequence\",\"parts\":["
        "{\"type\":\"Anchor\",\"at\":\"Start\"},"
        "{\"type\":\"Group\",\"capturing\":true,\"body\":{\"type\":\"Quantifier\",\"min\":3,\"max\":3,\"target\":{\"type\":\"Escape\",\"kind\":\"digit\"}}},"
        "{\"type\":\"Quantifier\",\"min\":0,\"max\":1,\"target\":{\"type\":\"CharacterClass\",\"members\":[{\"type\":\"Literal\",\"value\":\"-\"},{\"type\":\"Literal\",\"value\":\".\"},{\"type\":\"Literal\",\"value\":\" \"}] } },"
        "{\"type\":\"Group\",\"capturing\":true,\"body\":{\"type\":\"Quantifier\",\"min\":3,\"max\":3,\"target\":{\"type\":\"Escape\",\"kind\":\"digit\"}}},"
        "{\"type\":\"Quantifier\",\"min\":0,\"max\":1,\"target\":{\"type\":\"CharacterClass\",\"members\":[{\"type\":\"Literal\",\"value\":\"-\"},{\"type\":\"Literal\",\"value\":\".\"},{\"type\":\"Literal\",\"value\":\" \"}] } },"
        "{\"type\":\"Group\",\"capturing\":true,\"body\":{\"type\":\"Quantifier\",\"min\":4,\"max\":4,\"target\":{\"type\":\"Escape\",\"kind\":\"digit\"}}},"
        "{\"type\":\"Anchor\",\"at\":\"End\"}]}";

    STRlingFlags* flags = strling_flags_create();
    strling_result_t result = strling_compile_compat(phone_json, flags);
    if (result.error_code == STRling_OK) {
        printf("compiled: %s\n", result.pcre2_pattern);
    } else {
        fprintf(stderr, "compile error: %s\n", result.error_message);
    }

    /* cleanup */
    strling_result_free_compat(&result);
    strling_flags_free(flags);
    strling_ast_node_free(ast);

    /* This example compiles to the optimized regex: ^(\d{3})[-. ]?(\d{3})[-. ]?(\d{4})$ */
    return (result.error_code == STRling_OK) ? 0 : 1;
}
```

This example shows how to build AST nodes using the `strling_ast_*_create` helpers
and how to compile a JSON AST (here provided inline) with `strling_compile_compat`.

Memory ownership: all constructors return heap-allocated objects — call the
corresponding free helpers like `strling_ast_node_free()` and
`strling_result_free_compat()` when finished.

</details>
