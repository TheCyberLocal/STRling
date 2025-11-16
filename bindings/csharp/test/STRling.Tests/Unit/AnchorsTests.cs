using Strling.Core;
using Xunit;

namespace STRling.Tests.Unit;

/// <summary>
/// Test Design — AnchorsTests.cs
///
/// ## Purpose
/// This test suite validates the correct parsing of all anchor tokens (^, $, \b, \B, etc.).
/// It ensures that each anchor is correctly mapped to a corresponding Anchor AST node
/// with the proper type and that its parsing is unaffected by flags or surrounding
/// constructs.
///
/// ## Description
/// Anchors are zero-width assertions that do not consume characters but instead
/// match a specific **position** within the input string, such as the start of a
/// line or a boundary between a word and a space. This suite tests the parser's
/// ability to correctly identify all supported core and extension anchors and
/// produce the corresponding `Anchor` AST object.
///
/// ## Scope
/// -   **In scope:**
/// -   Parsing of core line anchors (`^`, `$`) and word boundary anchors
/// (`\b`, `\B`).
/// -   Parsing of non-core, engine-specific absolute anchors (`\A`, `\Z`).
/// -   The structure and `at` value of the resulting `Anchor` AST node.
/// -   How anchors are parsed when placed at the start, middle, or end of a sequence.
/// -   Ensuring the parser's output for `^` and `$` is consistent regardless
/// of the multiline (`m`) flag's presence.
/// -   **Out of scope:**
/// -   The runtime *behavioral change* of `^` and `$` when the `m` flag is
/// active (this is an emitter/engine concern).
/// -   Quantification of anchors.
/// -   The behavior of `\b` inside a character class, where it represents a
/// backspace literal (covered in CharClassesTests).
/// </summary>
public class AnchorsTests
{
    /// <summary>
    /// Category A: Positive Cases
    /// Covers all positive cases for valid anchor syntax. These tests verify
    /// that each anchor token is parsed into the correct Anchor node with the
    /// expected `at` value.
    /// </summary>
    [Theory]
    [InlineData("^", "Start", "line_start")]
    [InlineData("$", "End", "line_end")]
    [InlineData(@"\b", "WordBoundary", "word_boundary")]
    [InlineData(@"\B", "NotWordBoundary", "not_word_boundary")]
    [InlineData(@"\A", "AbsoluteStart", "absolute_start_ext")]
    [InlineData(@"\Z", "EndBeforeFinalNewline", "end_before_newline_ext")]
    public void ShouldParseAnchor(string inputDsl, string expectedAtValue, string id)
    {
        // Tests that each individual anchor token is parsed into the correct
        // Anchor AST node.
        var (_, ast) = Strling.Parser.Parse(inputDsl);
        Assert.IsType<Anchor>(ast);
        var anchor = (Anchor)ast;
        Assert.Equal(expectedAtValue, anchor.At);
    }

    /// <summary>
    /// Category C: Edge Cases
    /// Covers edge cases related to the position and combination of anchors.
    /// </summary>
    [Fact]
    public void ShouldParsePatternWithOnlyAnchors()
    {
        // Tests that a pattern containing multiple anchors is parsed into a
        // correct sequence of Anchor nodes.
        var (_, ast) = Strling.Parser.Parse(@"^\A\b$");
        Assert.IsType<Seq>(ast);
        var seqNode = (Seq)ast;

        Assert.Equal(4, seqNode.Parts.Count);
        Assert.All(seqNode.Parts, part => Assert.IsType<Anchor>(part));
        
        var atValues = seqNode.Parts.Select(p => ((Anchor)p).At).ToList();
        Assert.Equal(new[] { "Start", "AbsoluteStart", "WordBoundary", "End" }, atValues);
    }

    [Theory]
    [InlineData("^a", 0, "Start", "at_start")]
    [InlineData(@"a\bb", 1, "WordBoundary", "in_middle")]
    [InlineData("ab$", 1, "End", "at_end")]
    public void ShouldParseAnchorsInDifferentPositions(string inputDsl, int expectedPosition, string expectedAtValue, string id)
    {
        // Tests that anchors are correctly parsed as part of a sequence at
        // various positions.
        var (_, ast) = Strling.Parser.Parse(inputDsl);
        Assert.IsType<Seq>(ast);
        var seqNode = (Seq)ast;
        var anchorNode = seqNode.Parts[expectedPosition];
        Assert.IsType<Anchor>(anchorNode);
        Assert.Equal(expectedAtValue, ((Anchor)anchorNode).At);
    }

    /// <summary>
    /// Category D: Interaction Cases
    /// Covers how anchors interact with other DSL features, such as flags
    /// and grouping constructs.
    /// </summary>
    [Fact]
    public void ShouldNotChangeTheParsedAstWhenMultilineFlagIsPresent()
    {
        // A critical test to ensure the parser's output for `^` and `$` is
        // identical regardless of the multiline flag. The flag's semantic
        // effect is a runtime concern for the regex engine.
        var (_, astNoM) = Strling.Parser.Parse("^a$");
        var (_, astWithM) = Strling.Parser.Parse("%flags m\n^a$");

        // The AST structure should be the same
        Assert.IsType<Seq>(astNoM);
        Assert.IsType<Seq>(astWithM);
        
        var seqNoM = (Seq)astNoM;
        var seqWithM = (Seq)astWithM;
        
        Assert.Equal(seqNoM.Parts.Count, seqWithM.Parts.Count);
        Assert.IsType<Anchor>(seqNoM.Parts[0]);
        Assert.IsType<Anchor>(seqWithM.Parts[0]);
        Assert.Equal(((Anchor)seqNoM.Parts[0]).At, ((Anchor)seqWithM.Parts[0]).At);
    }

    [Theory]
    [InlineData("(^a)", typeof(Group), "Start", "in_capturing_group")]
    [InlineData(@"(?:a\b)", typeof(Group), "WordBoundary", "in_noncapturing_group")]
    [InlineData("(?=a$)", typeof(Look), "End", "in_lookahead")]
    [InlineData("(?<=^a)", typeof(Look), "Start", "in_lookbehind")]
    public void ShouldParseAnchorsInsideGroupsAndLookarounds(string inputDsl, Type containerType, string expectedAtValue, string id)
    {
        // Tests that anchors are correctly parsed when nested inside other
        // syntactic constructs.
        var (_, ast) = Strling.Parser.Parse(inputDsl);
        Assert.IsType(containerType, ast);

        // The anchor may be part of a sequence inside the container, find it
        Anchor? anchorNode = null;
        var body = containerType == typeof(Group) ? ((Group)ast).Body : ((Look)ast).Body;
        
        if (body is Seq seq)
        {
            // Find the anchor in the sequence
            anchorNode = seq.Parts.OfType<Anchor>().FirstOrDefault();
        }
        else if (body is Anchor anchor)
        {
            // Direct anchor
            anchorNode = anchor;
        }

        Assert.NotNull(anchorNode);
        Assert.Equal(expectedAtValue, anchorNode.At);
    }
}
