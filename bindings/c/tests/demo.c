/**
 * @file demo.c
 * 
 * Demonstration of Phase 3 features: Character Classes and Flags
 */

#include <stdio.h>
#include <stdlib.h>
#include "../include/strling.h"

static void demo_compile(const char* description, const char* json) {
    printf("%-40s", description);
    
    STRlingResult* result = strling_compile(json, NULL);
    if (result && result->pattern) {
        printf(" → %s\n", result->pattern);
    } else if (result && result->error) {
        printf(" → ERROR: %s\n", result->error->message);
    } else {
        printf(" → ERROR: NULL result\n");
    }
    
    strling_result_free(result);
}

int main(void) {
    printf("\n");
    printf("╔════════════════════════════════════════════════════════════════╗\n");
    printf("║  STRling Phase 3 - Character Classes & Flags Demonstration    ║\n");
    printf("╚════════════════════════════════════════════════════════════════╝\n");
    printf("\n");
    
    printf("Character Class Examples:\n");
    printf("─────────────────────────────────────────────────────────────────\n");
    
    demo_compile("Simple literal class [a]",
        "{\"pattern\":{\"type\":\"CharacterClass\",\"negated\":false,"
        "\"members\":[{\"type\":\"Literal\",\"value\":\"a\"}]}}");
    
    demo_compile("Multiple literals [abc]",
        "{\"pattern\":{\"type\":\"CharacterClass\",\"negated\":false,"
        "\"members\":[{\"type\":\"Literal\",\"value\":\"a\"},"
        "{\"type\":\"Literal\",\"value\":\"b\"},"
        "{\"type\":\"Literal\",\"value\":\"c\"}]}}");
    
    demo_compile("Negated class [^a]",
        "{\"pattern\":{\"type\":\"CharacterClass\",\"negated\":true,"
        "\"members\":[{\"type\":\"Literal\",\"value\":\"a\"}]}}");
    
    demo_compile("Range [a-z]",
        "{\"pattern\":{\"type\":\"CharacterClass\",\"negated\":false,"
        "\"members\":[{\"type\":\"Range\",\"from\":\"a\",\"to\":\"z\"}]}}");
    
    demo_compile("Multiple ranges [a-zA-Z0-9]",
        "{\"pattern\":{\"type\":\"CharacterClass\",\"negated\":false,"
        "\"members\":[{\"type\":\"Range\",\"from\":\"a\",\"to\":\"z\"},"
        "{\"type\":\"Range\",\"from\":\"A\",\"to\":\"Z\"},"
        "{\"type\":\"Range\",\"from\":\"0\",\"to\":\"9\"}]}}");
    
    demo_compile("Meta digit [\\d]",
        "{\"pattern\":{\"type\":\"CharacterClass\",\"negated\":false,"
        "\"members\":[{\"type\":\"Meta\",\"value\":\"d\"}]}}");
    
    demo_compile("Meta word & space [\\w\\s]",
        "{\"pattern\":{\"type\":\"CharacterClass\",\"negated\":false,"
        "\"members\":[{\"type\":\"Meta\",\"value\":\"w\"},"
        "{\"type\":\"Meta\",\"value\":\"s\"}]}}");
    
    demo_compile("Mixed [a-f\\d]",
        "{\"pattern\":{\"type\":\"CharacterClass\",\"negated\":false,"
        "\"members\":[{\"type\":\"Range\",\"from\":\"a\",\"to\":\"f\"},"
        "{\"type\":\"Meta\",\"value\":\"d\"}]}}");
    
    demo_compile("Unicode property [\\p{L}]",
        "{\"pattern\":{\"type\":\"CharacterClass\",\"negated\":false,"
        "\"members\":[{\"type\":\"UnicodeProperty\",\"value\":\"L\",\"negated\":false}]}}");
    
    demo_compile("Unicode named [\\p{Script=Latin}]",
        "{\"pattern\":{\"type\":\"CharacterClass\",\"negated\":false,"
        "\"members\":[{\"type\":\"UnicodeProperty\",\"name\":\"Script\","
        "\"value\":\"Latin\",\"negated\":false}]}}");
    
    printf("\n");
    printf("Flag Examples:\n");
    printf("─────────────────────────────────────────────────────────────────\n");
    
    demo_compile("Case insensitive (?i)",
        "{\"pattern\":{\"type\":\"Literal\",\"value\":\"test\"},"
        "\"flags\":{\"ignoreCase\":true,\"multiline\":false,\"dotAll\":false,\"extended\":false}}");
    
    demo_compile("Multiline (?m)",
        "{\"pattern\":{\"type\":\"Literal\",\"value\":\"test\"},"
        "\"flags\":{\"ignoreCase\":false,\"multiline\":true,\"dotAll\":false,\"extended\":false}}");
    
    demo_compile("Dot all (?s)",
        "{\"pattern\":{\"type\":\"Literal\",\"value\":\"test\"},"
        "\"flags\":{\"ignoreCase\":false,\"multiline\":false,\"dotAll\":true,\"extended\":false}}");
    
    demo_compile("Free spacing (?x)",
        "{\"pattern\":{\"type\":\"Literal\",\"value\":\"test\"},"
        "\"flags\":{\"ignoreCase\":false,\"multiline\":false,\"dotAll\":false,\"extended\":true}}");
    
    demo_compile("Combined flags (?ims)",
        "{\"pattern\":{\"type\":\"Literal\",\"value\":\"test\"},"
        "\"flags\":{\"ignoreCase\":true,\"multiline\":true,\"dotAll\":true,\"extended\":false}}");
    
    printf("\n");
    printf("Complex Examples:\n");
    printf("─────────────────────────────────────────────────────────────────\n");
    
    demo_compile("Email pattern ^[a-z]+@[a-z]+$",
        "{\"pattern\":{\"type\":\"Sequence\",\"parts\":["
        "{\"type\":\"Anchor\",\"at\":\"Start\"},"
        "{\"type\":\"Quantifier\",\"target\":{\"type\":\"CharacterClass\",\"negated\":false,"
        "\"members\":[{\"type\":\"Range\",\"from\":\"a\",\"to\":\"z\"}]},"
        "\"min\":1,\"max\":null,\"lazy\":false,\"possessive\":false},"
        "{\"type\":\"Literal\",\"value\":\"@\"},"
        "{\"type\":\"Quantifier\",\"target\":{\"type\":\"CharacterClass\",\"negated\":false,"
        "\"members\":[{\"type\":\"Range\",\"from\":\"a\",\"to\":\"z\"}]},"
        "\"min\":1,\"max\":null,\"lazy\":false,\"possessive\":false},"
        "{\"type\":\"Anchor\",\"at\":\"End\"}]}}");
    
    demo_compile("Hex color with flags (?i)[a-f0-9]{6}",
        "{\"pattern\":{\"type\":\"Quantifier\",\"target\":{\"type\":\"CharacterClass\","
        "\"negated\":false,\"members\":[{\"type\":\"Range\",\"from\":\"a\",\"to\":\"f\"},"
        "{\"type\":\"Range\",\"from\":\"0\",\"to\":\"9\"}]},\"min\":6,\"max\":6,"
        "\"lazy\":false,\"possessive\":false},"
        "\"flags\":{\"ignoreCase\":true,\"multiline\":false,\"dotAll\":false,\"extended\":false}}");
    
    demo_compile("Not whitespace [^\\s]+",
        "{\"pattern\":{\"type\":\"Quantifier\",\"target\":{\"type\":\"CharacterClass\","
        "\"negated\":true,\"members\":[{\"type\":\"Meta\",\"value\":\"s\"}]},"
        "\"min\":1,\"max\":null,\"lazy\":false,\"possessive\":false}}");
    
    printf("\n");
    printf("╔════════════════════════════════════════════════════════════════╗\n");
    printf("║  All demonstrations completed successfully!                   ║\n");
    printf("╚════════════════════════════════════════════════════════════════╝\n");
    printf("\n");
    
    return 0;
}
