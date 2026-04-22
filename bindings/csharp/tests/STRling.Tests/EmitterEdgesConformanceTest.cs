using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using Strling.Core;
using Strling.Emit;
using Xunit;

namespace Strling.Tests
{
    /// <summary>
    /// Emitter Edges Conformance — C# bridge.
    ///
    /// Drives the global pathological-AST fixture
    /// <c>tests/conformance/inputs/emitter_edges/pathological.json</c>
    /// through the C# <see cref="Pcre2Emitter"/> and asserts each safety guard
    /// fires:
    ///   1. Variable-Length Lookbehind Rejection — STRlingCompilationError
    ///   2. AST Depth Limit Exceeded             — STRlingCompilationError
    ///   3. ReDoS Risk Warning (`(a+)+`)         — non-fatal STRlingWarning
    ///
    /// The fixture's <c>ast</c> field is the user-facing AST sketch
    /// (e.g. <c>{type: "Lookbehind", content: ...}</c>), not the
    /// post-lowering IR. The local <see cref="AstToIR"/> adapter mirrors
    /// the TypeScript bridge's <c>astToIR</c> so the test targets the
    /// emitter without coupling to the parser/compiler stages. Keep the
    /// adapter minimal — supporting only node types currently appearing
    /// in <c>pathological.json</c> — so adapter omissions cannot mask
    /// emitter bugs by silently dropping nodes.
    /// </summary>
    public class EmitterEdgesConformanceTest
    {
        private static string FixturePath()
        {
            // xUnit runs from the test project's bin/<config>/<tfm>/ folder.
            // Climb until we find the workspace marker (toolchain.json) or hit root.
            var dir = AppContext.BaseDirectory;
            for (int i = 0; i < 12 && dir != null; i++)
            {
                var marker = Path.Combine(dir, "toolchain.json");
                if (File.Exists(marker))
                {
                    return Path.Combine(dir, "tests", "conformance", "inputs",
                        "emitter_edges", "pathological.json");
                }
                dir = Path.GetDirectoryName(dir);
            }
            throw new FileNotFoundException(
                "Could not locate workspace root (toolchain.json) from " + AppContext.BaseDirectory);
        }

        private static IROp AstToIR(JsonElement node)
        {
            var type = node.GetProperty("type").GetString();
            switch (type)
            {
                case "Literal":
                    var val = node.TryGetProperty("value", out var v) ? (v.GetString() ?? "") : "";
                    return new IRLit(val);

                case "Group":
                    return new IRGroup(false, AstToIR(node.GetProperty("content")), null, false);

                case "Quantifier":
                    {
                        var child = AstToIR(node.GetProperty("content"));
                        var min = node.TryGetProperty("min", out var mn) ? mn.GetInt32() : 0;
                        object max;
                        if (node.TryGetProperty("max", out var mx) && mx.ValueKind != JsonValueKind.Null)
                        {
                            max = mx.GetInt32();
                        }
                        else
                        {
                            // null in the user-facing AST means unbounded → IR sentinel "Inf".
                            max = "Inf";
                        }
                        var mode = node.TryGetProperty("mode", out var md) ? (md.GetString() ?? "Greedy") : "Greedy";
                        return new IRQuant(child, min, max, mode);
                    }

                case "Lookbehind":
                    return new IRLook("Behind", false, AstToIR(node.GetProperty("content")));
                case "NegativeLookbehind":
                    return new IRLook("Behind", true, AstToIR(node.GetProperty("content")));
                case "Lookahead":
                    return new IRLook("Ahead", false, AstToIR(node.GetProperty("content")));
                case "NegativeLookahead":
                    return new IRLook("Ahead", true, AstToIR(node.GetProperty("content")));

                default:
                    throw new ArgumentException(
                        $"AstToIR: unsupported pathological AST node type \"{type}\". " +
                        "Extend the adapter when new pathological vectors are added.");
            }
        }

        // Strip the "STRlingCompilationError: " / "STRlingWarning [CODE]: " prefix.
        private static string ExpectedSubstring(string prefixed)
        {
            const string errPrefix = "STRlingCompilationError:";
            const string warnPrefix = "STRlingWarning";
            if (prefixed.StartsWith(errPrefix))
            {
                return prefixed.Substring(errPrefix.Length).TrimStart();
            }
            if (prefixed.StartsWith(warnPrefix))
            {
                var idx = prefixed.IndexOf(']');
                if (idx >= 0)
                {
                    return prefixed.Substring(idx + 1).TrimStart(':', ' ');
                }
            }
            return prefixed;
        }

        public static IEnumerable<object[]> PathologicalCases()
        {
            var json = File.ReadAllText(FixturePath());
            using var doc = JsonDocument.Parse(json);
            foreach (var tc in doc.RootElement.GetProperty("tests").EnumerateArray())
            {
                yield return new object[] { tc.GetProperty("name").GetString()!, tc.GetRawText() };
            }
        }

        [Theory]
        [MemberData(nameof(PathologicalCases))]
        public void RunPathologicalCase(string name, string rawJson)
        {
            using var doc = JsonDocument.Parse(rawJson);
            var tc = doc.RootElement;
            var ir = AstToIR(tc.GetProperty("ast"));
            int maxDepth = tc.TryGetProperty("depth_override_for_test", out var d) ? d.GetInt32() : 0;

            if (tc.TryGetProperty("expected_error", out var ee))
            {
                var needle = ExpectedSubstring(ee.GetString()!);
                var ex = Assert.Throws<STRlingCompilationError>(
                    () => Pcre2Emitter.EmitWithDiagnostics(ir, null, maxDepth));
                Assert.Contains(needle, ex.Message);
                return;
            }
            if (tc.TryGetProperty("expected_warning", out var ew))
            {
                var needle = ExpectedSubstring(ew.GetString()!);
                var result = Pcre2Emitter.EmitWithDiagnostics(ir, null, maxDepth);
                // Warnings must NOT abort emission — the pattern is still produced.
                Assert.False(string.IsNullOrEmpty(result.Pattern),
                    "expected non-empty pattern when only a warning fires");
                Assert.Contains(result.Warnings, w => w.Code == "REDOS_RISK" && w.Message.Contains(needle));
                return;
            }
            Assert.Fail($"Test case \"{name}\" declares neither expected_error nor expected_warning.");
        }

        // --- Negative controls -------------------------------------------------

        [Fact]
        public void NonPathologicalPatternEmitsNoWarnings()
        {
            var result = Pcre2Emitter.EmitWithDiagnostics(new IRLit("abc"));
            Assert.Equal("abc", result.Pattern);
            Assert.Empty(result.Warnings);
        }

        [Fact]
        public void DepthCapDoesNotFireUnderLimit()
        {
            // Two nested groups under a depth cap of 5 must compile cleanly.
            IROp deep = new IRGroup(false, new IRGroup(false, new IRLit("ok"), null, false), null, false);
            var result = Pcre2Emitter.EmitWithDiagnostics(deep, null, 5);
            Assert.Empty(result.Warnings);
            Assert.Contains("ok", result.Pattern);
        }
    }
}
