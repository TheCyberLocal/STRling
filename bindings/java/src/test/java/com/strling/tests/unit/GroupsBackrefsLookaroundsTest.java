package com.strling.tests.unit;

import com.strling.core.Nodes.*;
import com.strling.core.Parser;
import com.strling.core.STRlingParseError;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

import java.util.List;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.*;

/**
 * @file Test Design — GroupsBackrefsLookaroundsTest.java
 *
 * <h2>Purpose</h2>
 * This test suite validates the parser's handling of all grouping constructs,
 * backreferences, and lookarounds. It ensures that different group types are
 * parsed correctly into their corresponding AST nodes, that backreferences are
 * validated against defined groups, that lookarounds are constructed properly,
 * and that all syntactic errors raise the correct `ParseError`.
 *
 * <h2>Description</h2>
 * Groups, backreferences, and lookarounds are the primary features for defining
 * structure and context within a pattern.
 * <ul>
 * <li><strong>Groups</strong> {@code (...)} are used to create sub-patterns, apply quantifiers to
 * sequences, and capture text for later use.</li>
 * <li><strong>Backreferences</strong> {@code \1}, {@code \k<name>} match the exact text previously
 * captured by a group.</li>
 * <li><strong>Lookarounds</strong> {@code (?=...)}, {@code (?<=...)}, etc., are zero-width assertions that
 * check for patterns before or after the current position without consuming
 * characters.</li>
 * </ul>
 * This suite verifies that the parser correctly implements the rich syntax and
 * validation rules for these powerful features.
 *
 * <h2>Scope</h2>
 * <ul>
 * <li><strong>In scope:</strong></li>
 * <ul>
 * <li>Parsing of all group types: capturing {@code ()}, non-capturing {@code (?:...)},
 * named {@code (?<name>...)}, and atomic {@code (?>...)}.</li>
 * <li>Parsing of numeric ({@code \1}) and named ({@code \k<name>}) backreferences.</li>
 * <li>Validation of backreferences (e.g., ensuring no forward references).</li>
 * <li>Parsing of all four lookaround types: positive/negative lookahead and
 * positive/negative lookbehind.</li>
 * <li>Error handling for unterminated constructs and invalid backreferences.</li>
 * <li>The structure of the resulting {@code nodes.Group}, {@code nodes.Backref}, and
 * {@code nodes.Look} AST nodes.</li>
 * </ul>
 * <li><strong>Out of scope:</strong></li>
 * <ul>
 * <li>Quantification of these constructs (covered in {@code QuantifiersTest.java}).</li>
 * <li>Semantic validation of lookbehind contents (e.g., the fixed-length
 * requirement).</li>
 * <li>Emitter-specific syntax transformations.</li>
 * </ul>
 * </ul>
 */
public class GroupsBackrefsLookaroundsTest {

    // Helper to get the AST root from a parse
    private Node parseToAST(String dsl) {
        return Parser.parse(dsl).ast;
    }

    /**
     * Covers all positive cases for valid group, backreference, and lookaround syntax.
     */
    @Nested
    class CategoryAPositiveCases {

        static Stream<Arguments> groupTypes() {
            return Stream.of(
                Arguments.of("(a)", true, null, null, "capturing"),
                Arguments.of("(?:a)", false, null, null, "non_capturing"),
                Arguments.of("(?<name>a)", true, "name", null, "named_capturing"),
                Arguments.of("(?>a)", false, null, true, "atomic_ext")
            );
        }

        @ParameterizedTest(name = "should parse group type for \"{0}\" (ID: {4})")
        @MethodSource("groupTypes")
        void shouldParseGroupTypeFor(String inputDsl, boolean expectedCapturing, String expectedName, Boolean expectedAtomic, String id) {
            /** Tests that various group types are parsed with the correct attributes. */
            Node ast = parseToAST(inputDsl);
            assertInstanceOf(Group.class, ast);
            Group g = (Group) ast;
            assertEquals(expectedCapturing, g.capturing);
            assertEquals(expectedName, g.name);
            assertEquals(expectedAtomic, g.atomic);
            assertTrue(g.body instanceof Lit);
        }

        static Stream<Arguments> backreferenceCases() {
            // This now mirrors the JS test.each
            return Stream.of(
                Arguments.of("(a)\\1", 1, null, "numeric_backref"),
                Arguments.of("(?<A>a)\\k<A>", null, "A", "named_backref")
            );
        }

        @ParameterizedTest(name = "should parse backreference for \"{0}\" (ID: {3})")
        @MethodSource("backreferenceCases")
        void shouldParseBackreferenceFor(String inputDsl, Integer expectedIndex, String expectedName, String id) {
            /** Tests that valid backreferences are parsed into the correct Backref node. */
            Node ast = parseToAST(inputDsl);
            assertInstanceOf(Seq.class, ast);
            Seq s = (Seq) ast;
            Backref backref = (Backref) s.parts.get(1);
            assertInstanceOf(Backref.class, backref);
            assertEquals(expectedIndex, backref.byIndex);
            assertEquals(expectedName, backref.byName);
        }


        static Stream<Arguments> lookarounds() {
            return Stream.of(
                Arguments.of("a(?=b)", "Ahead", false, "lookahead_pos"),
                Arguments.of("a(?!b)", "Ahead", true, "lookahead_neg"),
                Arguments.of("(?<=a)b", "Behind", false, "lookbehind_pos"),
                Arguments.of("(?<!a)b", "Behind", true, "lookbehind_neg")
            );
        }

        @ParameterizedTest(name = "should parse lookaround for \"{0}\" (ID: {3})")
        @MethodSource("lookarounds")
        void shouldParseLookaroundFor(String inputDsl, String expectedDir, boolean expectedNeg, String id) {
            /** Tests that all four lookaround types are parsed correctly. */
            Node ast = parseToAST(inputDsl);
            assertInstanceOf(Seq.class, ast);
            Seq s = (Seq) ast;
            Look l;
            if (expectedDir.equals("Ahead")) {
                l = (Look) s.parts.get(1);
            } else {
                l = (Look) s.parts.get(0);
            }
            assertInstanceOf(Look.class, l);
            assertEquals(expectedDir, l.dir);
            assertEquals(expectedNeg, l.neg);
        }
    }

    /**
     * Covers all negative cases for malformed or invalid syntax.
     */
    @Nested
    class CategoryBNegativeCases {

        static Stream<Arguments> negativeCases() {
            return Stream.of(
                // B.1: Unterminated constructs
                Arguments.of("(a", "Unterminated group", 2, "unterminated_group"),
                Arguments.of("(?<name", "Unterminated group name", 7, "unterminated_named_group"),
                Arguments.of("(?=a", "Unterminated lookahead", 4, "unterminated_lookahead"),
                Arguments.of("\\k<A", "Unterminated named backref", 0, "unterminated_named_backref"),
                // B.2: Invalid backreferences
                Arguments.of("\\k<A>(?<A>a)", "Backreference to undefined group <A>", 0, "forward_ref_by_name"),
                Arguments.of("\\2(a)(b)", "Backreference to undefined group \\2", 0, "forward_ref_by_index"),
                Arguments.of("(a)\\2", "Backreference to undefined group \\2", 3, "nonexistent_ref_by_index"),
                // B.3: Invalid syntax
                Arguments.of("(?i)a", "Inline modifiers", 1, "disallowed_inline_modifier")
            );
        }

        @ParameterizedTest(name = "should fail for \"{0}\" (ID: {3})")
        @MethodSource("negativeCases")
        void shouldFailFor(String invalidDsl, String errorPrefix, int errorPos, String id) {
            /**
             * Tests that invalid syntax for groups and backrefs raises a ParseError.
             */
            STRlingParseError error = assertThrows(STRlingParseError.class, () -> Parser.parse(invalidDsl));
            assertTrue(error.getMessage().contains(errorPrefix));
            assertEquals(errorPos, error.getPos());
        }

        @Test
        void duplicateGroupNameRaisesError() {
            /**
             * Tests that duplicate group names raise a semantic error.
             * (Moved from Category H)
             */
            STRlingParseError e = assertThrows(STRlingParseError.class, () -> Parser.parse("(?<a>x)(?<a>y)"));
            assertTrue(e.getMessage().contains("Duplicate group name"));
        }
    }

    /**
     * Covers edge cases for groups and backreferences.
     */
    @Nested
    class CategoryCEdgeCases {

        static Stream<Arguments> emptyGroups() {
            return Stream.of(
                Arguments.of("()", true, null, "empty_capturing"),
                Arguments.of("(?:)", false, null, "empty_noncapturing"),
                Arguments.of("(?<A>)", true, "A", "empty_named")
            );
        }

        @ParameterizedTest(name = "should parse empty group for \"{0}\" (ID: {3})")
        @MethodSource("emptyGroups")
        void shouldParseEmptyGroupFor(String inputDsl, boolean expectedCapturing, String expectedName, String id) {
            /** Tests that empty groups parse into a Group node with an empty body. */
            Node ast = parseToAST(inputDsl);
            assertInstanceOf(Group.class, ast);
            Group groupNode = (Group) ast;
            assertEquals(expectedCapturing, groupNode.capturing);
            assertEquals(expectedName, groupNode.name);
            // Empty body is parsed as an empty Seq
            assertInstanceOf(Seq.class, groupNode.body);
            assertTrue(((Seq) groupNode.body).parts.isEmpty());
        }

        @Test
        void backreferenceToAnOptionalGroupShouldBeValidSyntax() {
            /**
             * Tests that a backreference to an optional group is syntactically valid.
             * (Split from testBackrefToOptionalGroupAndNullByte)
             */
            Node ast = parseToAST("(a)?\\1");
            assertInstanceOf(Seq.class, ast);
            Seq s = (Seq) ast;
            assertInstanceOf(Quant.class, s.parts.get(0));
            assertInstanceOf(Backref.class, s.parts.get(1));
            assertEquals(Integer.valueOf(1), ((Backref) s.parts.get(1)).byIndex);
        }

        @Test
        void shouldParse0AsANullByteNotABackreference() {
            /**
             * Tests that \0 is parsed as a literal null byte, not backreference 0.
             * (Split from testBackrefToOptionalGroupAndNullByte)
             */
            Node ast = parseToAST("\\0");
            assertInstanceOf(Lit.class, ast);
            assertEquals("\0", ((Lit) ast).value);
        }
    }

    /**
     * Covers interactions between groups, lookarounds, and other DSL features.
     */
    @Nested
    class CategoryDInteractionCases {

        @Test
        void shouldHandleABackreferenceInsideALookaround() {
            /**
             * Tests that a backreference can refer to a group defined before a lookaround.
             * (Split from testBackrefInsideLookaroundAndFreeSpacingInGroups)
             */
            Node ast = parseToAST("(?<A>a)(?=\\k<A>)");
            assertInstanceOf(Seq.class, ast);
            Seq s = (Seq) ast;
            assertInstanceOf(Group.class, s.parts.get(0));
            Look look = (Look) s.parts.get(1);
            assertInstanceOf(Backref.class, look.body);
            assertEquals("A", ((Backref) look.body).byName);
        }

        @Test
        void shouldHandleFreeSpacingModeInsideGroups() {
            /**
             * Tests that free-spacing and comments work correctly inside groups.
             * (Split from testBackrefInsideLookaroundAndFreeSpacingInGroups)
             */
            Node ast = parseToAST("%flags x\n(?<name> a #comment\n b)");
            assertInstanceOf(Group.class, ast);
            Group g = (Group) ast;
            assertEquals("name", g.name);
            assertInstanceOf(Seq.class, g.body);
            Seq body = (Seq) g.body;
            // Free spacing mode should still parse "a" and "b" as two literals in a sequence
            assertEquals(2, body.parts.size());
            assertEquals("a", ((Lit) body.parts.get(0)).value);
            assertEquals("b", ((Lit) body.parts.get(1)).value);
        }
    }

    /**
     * Tests for nested groups of the same and different types.
     * Validates that the parser correctly handles deep nesting.
     */
    @Nested
    class CategoryENestedGroups {

        @Test
        void shouldParseNestedCapturingGroups() {
            /** Tests nested capturing groups: ((a)) */
            Node ast = parseToAST("((a))");
            assertInstanceOf(Group.class, ast);
            Group group1 = (Group) ast;
            assertTrue(group1.capturing);
            assertInstanceOf(Group.class, group1.body);
            Group group2 = (Group) group1.body;
            assertTrue(group2.capturing);
            assertInstanceOf(Lit.class, group2.body);
            assertEquals("a", ((Lit) group2.body).value);
        }

        @Test
        void shouldParseNestedNonCapturingGroups() {
            /** Tests nested non-capturing groups: (?:(?:a)) */
            Node ast = parseToAST("(?:(?:a))");
            assertInstanceOf(Group.class, ast);
            Group group1 = (Group) ast;
            assertFalse(group1.capturing);
            assertInstanceOf(Group.class, group1.body);
            Group group2 = (Group) group1.body;
            assertFalse(group2.capturing);
            assertInstanceOf(Lit.class, group2.body);
            assertEquals("a", ((Lit) group2.body).value);
        }

        @Test
        void shouldParseNestedAtomicGroups() {
            /** Tests nested atomic groups: (?>(?>(a))) */
            Node ast = parseToAST("(?>(?>(a)))");
            assertInstanceOf(Group.class, ast);
            Group group1 = (Group) ast;
            assertTrue(group1.atomic);
            assertInstanceOf(Group.class, group1.body);
            Group group2 = (Group) group1.body;
            assertTrue(group2.atomic);
            assertInstanceOf(Group.class, group2.body);
            Group group3 = (Group) group2.body;
            assertTrue(group3.capturing); // Innermost is (a)
            assertInstanceOf(Lit.class, group3.body);
        }

        @Test
        void shouldParseCapturingGroupInsideNonCapturing() {
            /** Tests capturing group inside non-capturing: (?:(a)) */
            Node ast = parseToAST("(?:(a))");
            assertInstanceOf(Group.class, ast);
            Group group1 = (Group) ast;
            assertFalse(group1.capturing);
            assertInstanceOf(Group.class, group1.body);
            Group group2 = (Group) group1.body;
            assertTrue(group2.capturing);
            assertInstanceOf(Lit.class, group2.body);
            assertEquals("a", ((Lit) group2.body).value);
        }

        @Test
        void shouldParseNamedGroupInsideCapturing() {
            /** Tests named group inside capturing: ((?<name>a)) */
            Node ast = parseToAST("((?<name>a))");
            assertInstanceOf(Group.class, ast);
            Group group1 = (Group) ast;
            assertTrue(group1.capturing);
            assertNull(group1.name);
            assertInstanceOf(Group.class, group1.body);
            Group group2 = (Group) group1.body;
            assertTrue(group2.capturing);
            assertEquals("name", group2.name);
            assertInstanceOf(Lit.class, group2.body);
        }

        @Test
        void shouldParseAtomicGroupInsideNonCapturing() {
            /** Tests atomic group inside non-capturing: (?:(?>a)) */
            Node ast = parseToAST("(?:(?>a))");
            assertInstanceOf(Group.class, ast);
            Group group1 = (Group) ast;
            assertFalse(group1.capturing);
            assertInstanceOf(Group.class, group1.body);
            Group group2 = (Group) group1.body;
            assertTrue(group2.atomic);
            assertInstanceOf(Lit.class, group2.body);
            assertEquals("a", ((Lit) group2.body).value);
        }

        @Test
        void shouldParseDeeplyNestedGroups() {
            /** Tests deeply nested groups (3+ levels): ((?:(?<x>(?>a)))) */
            Node ast = parseToAST("((?:(?<x>(?>a))))");
            assertInstanceOf(Group.class, ast);
            Group level1 = (Group) ast;
            assertTrue(level1.capturing);
            // Level 2
            assertInstanceOf(Group.class, level1.body);
            Group level2 = (Group) level1.body;
            assertFalse(level2.capturing);
            // Level 3
            assertInstanceOf(Group.class, level2.body);
            Group level3 = (Group) level2.body;
            assertTrue(level3.capturing);
            assertEquals("x", level3.name);
            // Level 4
            assertInstanceOf(Group.class, level3.body);
            Group level4 = (Group) level3.body;
            assertTrue(level4.atomic);
            assertInstanceOf(Lit.class, level4.body);
        }
    }

    /**
     * Tests for lookarounds containing complex patterns like alternations
     * and nested lookarounds.
     */
    @Nested
    class CategoryFLookaroundWithComplexContent {

        @Test
        void shouldParseLookaheadWithAlternation() {
            /** Tests positive lookahead with alternation: (?=a|b) */
            Node ast = parseToAST("(?=a|b)");
            assertInstanceOf(Look.class, ast);
            Look lookNode = (Look) ast;
            assertEquals("Ahead", lookNode.dir);
            assertFalse(lookNode.neg);
            assertInstanceOf(Alt.class, lookNode.body);
            assertEquals(2, ((Alt) lookNode.body).branches.size());
        }

        @Test
        void shouldParseLookbehindWithAlternation() {
            /** Tests positive lookbehind with alternation: (?<=x|y) */
            Node ast = parseToAST("(?<=x|y)");
            assertInstanceOf(Look.class, ast);
            Look lookNode = (Look) ast;
            assertEquals("Behind", lookNode.dir);
            assertFalse(lookNode.neg);
            assertInstanceOf(Alt.class, lookNode.body);
            assertEquals(2, ((Alt) lookNode.body).branches.size());
        }

        @Test
        void shouldParseNegativeLookaheadWithAlternation() {
            /** Tests negative lookahead with alternation: (?!a|b|c) */
            Node ast = parseToAST("(?!a|b|c)");
            assertInstanceOf(Look.class, ast);
            Look lookNode = (Look) ast;
            assertEquals("Ahead", lookNode.dir);
            assertTrue(lookNode.neg);
            assertInstanceOf(Alt.class, lookNode.body);
            assertEquals(3, ((Alt) lookNode.body).branches.size());
        }

        @Test
        void shouldParseNestedLookaheads() {
            /** Tests nested positive lookaheads: (?=(?=a)) */
            Node ast = parseToAST("(?=(?=a))");
            assertInstanceOf(Look.class, ast);
            Look outer = (Look) ast;
            assertEquals("Ahead", outer.dir);
            assertInstanceOf(Look.class, outer.body);
            Look inner = (Look) outer.body;
            assertEquals("Ahead", inner.dir);
            assertInstanceOf(Lit.class, inner.body);
        }

        @Test
        void shouldParseNestedLookbehinds() {
            /** Tests nested lookbehinds: (?<=(?<!a)) */
            Node ast = parseToAST("(?<=(?<!a))");
            assertInstanceOf(Look.class, ast);
            Look outer = (Look) ast;
            assertEquals("Behind", outer.dir);
            assertFalse(outer.neg);
            assertInstanceOf(Look.class, outer.body);
            Look inner = (Look) outer.body;
            assertEquals("Behind", inner.dir);
            assertTrue(inner.neg);
            assertInstanceOf(Lit.class, inner.body);
        }

        @Test
        void shouldParseMixedNestedLookarounds() {
            /** Tests lookahead inside lookbehind: (?<=a(?=b)) */
            Node ast = parseToAST("(?<=a(?=b))");
            assertInstanceOf(Look.class, ast);
            Look lookNode = (Look) ast;
            assertEquals("Behind", lookNode.dir);
            assertInstanceOf(Seq.class, lookNode.body);
            Seq seqBody = (Seq) lookNode.body;
            assertEquals(2, seqBody.parts.size());
            assertInstanceOf(Lit.class, seqBody.parts.get(0));
            assertInstanceOf(Look.class, seqBody.parts.get(1));
            assertEquals("Ahead", ((Look) seqBody.parts.get(1)).dir);
        }
    }

    /**
     * Tests for atomic groups with complex content.
     */
    @Nested
    class CategoryGAtomicGroupEdgeCases {

        @Test
        void shouldParseAtomicGroupWithAlternation() {
            /** Tests atomic group with alternation: (?>(a|b)) */
            Node ast = parseToAST("(?>(a|b))");
            assertInstanceOf(Group.class, ast);
            Group atomicGroup = (Group) ast;
            assertTrue(atomicGroup.atomic);
            // The atomic group contains a capturing group with alternation
            assertInstanceOf(Group.class, atomicGroup.body);
            Group innerGroup = (Group) atomicGroup.body;
            assertTrue(innerGroup.capturing);
            assertInstanceOf(Alt.class, innerGroup.body);
            assertEquals(2, ((Alt) innerGroup.body).branches.size());
        }

        @Test
        void shouldParseAtomicGroupWithQuantifiedContent() {
            /** Tests atomic group with quantified atoms: (?>a+b*) */
            Node ast = parseToAST("(?>a+b*)");
            assertInstanceOf(Group.class, ast);
            Group atomicGroup = (Group) ast;
            assertTrue(atomicGroup.atomic);
            assertInstanceOf(Seq.class, atomicGroup.body);
            Seq seqBody = (Seq) atomicGroup.body;
            assertEquals(2, seqBody.parts.size());
            assertInstanceOf(Quant.class, seqBody.parts.get(0));
            assertInstanceOf(Quant.class, seqBody.parts.get(1));
        }

        @Test
        void shouldParseEmptyAtomicGroup() {
            /** Tests empty atomic group: (?>) */
            Node ast = parseToAST("(?>)");
            assertInstanceOf(Group.class, ast);
            Group atomicGroup = (Group) ast;
            assertTrue(atomicGroup.atomic);
            assertInstanceOf(Seq.class, atomicGroup.body);
            assertEquals(0, ((Seq) atomicGroup.body).parts.size());
        }
    }

    /**
     * Tests for patterns with multiple backreferences and complex
     * backreference interactions.
     */
    @Nested
    class CategoryHMultipleBackreferences {

        @Test
        void shouldParseMultipleNumericBackrefsSequential() {
            /** Tests multiple sequential backreferences: (a)(b)\1\2 */
            Node ast = parseToAST("(a)(b)\\1\\2");
            assertInstanceOf(Seq.class, ast);
            Seq seqNode = (Seq) ast;
            assertEquals(4, seqNode.parts.size());
            assertInstanceOf(Group.class, seqNode.parts.get(0));
            assertInstanceOf(Group.class, seqNode.parts.get(1));
            assertInstanceOf(Backref.class, seqNode.parts.get(2));
            assertEquals(Integer.valueOf(1), ((Backref) seqNode.parts.get(2)).byIndex);
            assertInstanceOf(Backref.class, seqNode.parts.get(3));
            assertEquals(Integer.valueOf(2), ((Backref) seqNode.parts.get(3)).byIndex);
        }

        @Test
        void shouldParseMultipleNamedBackrefs() {
            /** Tests multiple named backreferences: (?<x>a)(?<y>b)\k<x>\k<y> */
            Node ast = parseToAST("(?<x>a)(?<y>b)\\k<x>\\k<y>");
            assertInstanceOf(Seq.class, ast);
            Seq seqNode = (Seq) ast;
            assertEquals(4, seqNode.parts.size());
            assertInstanceOf(Group.class, seqNode.parts.get(0));
            assertEquals("x", ((Group) seqNode.parts.get(0)).name);
            assertInstanceOf(Group.class, seqNode.parts.get(1));
            assertEquals("y", ((Group) seqNode.parts.get(1)).name);
            assertInstanceOf(Backref.class, seqNode.parts.get(2));
            assertEquals("x", ((Backref) seqNode.parts.get(2)).byName);
            assertInstanceOf(Backref.class, seqNode.parts.get(3));
            assertEquals("y", ((Backref) seqNode.parts.get(3)).byName);
        }

        @Test
        void shouldParseMixedNumericAndNamedBackrefs() {
            /** Tests mixed backreference types: (a)(?<x>b)\1\k<x> */
            Node ast = parseToAST("(a)(?<x>b)\\1\\k<x>");
            assertInstanceOf(Seq.class, ast);
            Seq seqNode = (Seq) ast;
            assertEquals(4, seqNode.parts.size());
            assertInstanceOf(Group.class, seqNode.parts.get(0));
            assertInstanceOf(Group.class, seqNode.parts.get(1));
            assertEquals("x", ((Group) seqNode.parts.get(1)).name);
            assertInstanceOf(Backref.class, seqNode.parts.get(2));
            assertEquals(Integer.valueOf(1), ((Backref) seqNode.parts.get(2)).byIndex);
            assertInstanceOf(Backref.class, seqNode.parts.get(3));
            assertEquals("x", ((Backref) seqNode.parts.get(3)).byName);
        }

        @Test
        void shouldParseBackrefInAlternation() {
            /** Tests backreference in alternation: (a)(\1|b) */
            Node ast = parseToAST("(a)(\\1|b)");
            assertInstanceOf(Seq.class, ast);
            Seq seqNode = (Seq) ast;
            assertEquals(2, seqNode.parts.size());
            assertInstanceOf(Group.class, seqNode.parts.get(0));
            Group group2 = (Group) seqNode.parts.get(1);
            assertInstanceOf(Group.class, group2);
            assertInstanceOf(Alt.class, group2.body);
            Alt altBody = (Alt) group2.body;
            assertEquals(2, altBody.branches.size());
            assertInstanceOf(Backref.class, altBody.branches.get(0));
            assertEquals(Integer.valueOf(1), ((Backref) altBody.branches.get(0)).byIndex);
        }

        @Test
        void shouldParseBackrefToEarlierAlternationBranch() {
            /** Tests backreference to group in alternation: (a|b)c\1 */
            Node ast = parseToAST("(a|b)c\\1");
            assertInstanceOf(Seq.class, ast);
            Seq seqNode = (Seq) ast;
            assertEquals(3, seqNode.parts.size());
            assertInstanceOf(Group.class, seqNode.parts.get(0));
            assertInstanceOf(Alt.class, ((Group) seqNode.parts.get(0)).body);
            assertInstanceOf(Lit.class, seqNode.parts.get(1));
            assertInstanceOf(Backref.class, seqNode.parts.get(2));
            assertEquals(Integer.valueOf(1), ((Backref) seqNode.parts.get(2)).byIndex);
        }

        @Test
        void shouldParseRepeatedBackreference() {
            /** Tests same backreference used multiple times: (a)\1\1 */
            Node ast = parseToAST("(a)\\1\\1");
            assertInstanceOf(Seq.class, ast);
            Seq seqNode = (Seq) ast;
            assertEquals(3, seqNode.parts.size());
            assertInstanceOf(Group.class, seqNode.parts.get(0));
            assertInstanceOf(Backref.class, seqNode.parts.get(1));
            assertEquals(Integer.valueOf(1), ((Backref) seqNode.parts.get(1)).byIndex);
            assertInstanceOf(Backref.class, seqNode.parts.get(2));
            assertEquals(Integer.valueOf(1), ((Backref) seqNode.parts.get(2)).byIndex);
        }
    }

    /**
     * Tests for groups and lookarounds inside alternation patterns.
     */
    @Nested
    class CategoryIGroupsInAlternation {

        @Test
        void shouldParseGroupsInAlternationBranches() {
            /** Tests capturing groups in alternation: (a)|(b) */
            Node ast = parseToAST("(a)|(b)");
            assertInstanceOf(Alt.class, ast);
            Alt altNode = (Alt) ast;
            assertEquals(2, altNode.branches.size());
            assertInstanceOf(Group.class, altNode.branches.get(0));
            assertTrue(((Group) altNode.branches.get(0)).capturing);
            assertInstanceOf(Group.class, altNode.branches.get(1));
            assertTrue(((Group) altNode.branches.get(1)).capturing);
        }

        @Test
        void shouldParseLookaroundsInAlternation() {
            /** Tests lookarounds in alternation: (?=a)|(?=b) */
            Node ast = parseToAST("(?=a)|(?=b)");
            assertInstanceOf(Alt.class, ast);
            Alt altNode = (Alt) ast;
            assertEquals(2, altNode.branches.size());
            assertInstanceOf(Look.class, altNode.branches.get(0));
            assertEquals("Ahead", ((Look) altNode.branches.get(0)).dir);
            assertInstanceOf(Look.class, altNode.branches.get(1));
            assertEquals("Ahead", ((Look) altNode.branches.get(1)).dir);
        }

        @Test
        void shouldParseMixedGroupTypesInAlternation() {
            /** Tests mixed group types in alternation: (a)|(?:b)|(?<x>c) */
            Node ast = parseToAST("(a)|(?:b)|(?<x>c)");
            assertInstanceOf(Alt.class, ast);
            Alt altNode = (Alt) ast;
            List<Node> branches = altNode.branches;
            assertEquals(3, branches.size());

            Group branch0 = (Group) branches.get(0);
            assertInstanceOf(Group.class, branch0);
            assertTrue(branch0.capturing);
            assertNull(branch0.name);

            Group branch1 = (Group) branches.get(1);
            assertInstanceOf(Group.class, branch1);
            assertFalse(branch1.capturing);

            Group branch2 = (Group) branches.get(2);
            assertInstanceOf(Group.class, branch2);
            assertTrue(branch2.capturing);
            assertEquals("x", branch2.name);
        }
    }
}
