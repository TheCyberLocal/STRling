using Strling.Core;
using Strling.Emit;
using Xunit;

namespace STRling.Tests;

public class EmitterDebugTest
{
    [Fact]
    public void LiteralEscapeRoundtrip()
    {
        var lit = new Lit("\\d");
        var ir = Compiler.Compile(lit);
        Assert.IsType<IRLit>(ir);
        var irlit = (IRLit)ir;

        // The IR literal value should contain a single backslash followed by 'd'
        Assert.Equal("\\d", irlit.Value);

        // Emitting the literal should produce a single backslash + 'd'
        var emitted = Pcre2Emitter.Emit(irlit, null);
        Assert.Equal("\\d", emitted);
    }

    [Fact]
    public void QuantInsideCaptureProducesExpectedForm()
    {
        var lit = new Lit("\\d");
        var quant = new Quant(lit, 3, 3, true, false, false);
        var group = new Group(true, quant, null, false);

        var ir = Compiler.Compile(group);
        var emitted = Pcre2Emitter.Emit(ir, null);

        // Expect a capturing group containing \d{3}
        Assert.Equal("(\\d{3})", emitted);
    }

    [Fact]
    public void SimplyDigitCaptureProducesExpectedForm()
    {
        var p = Strling.Simply.S.Digit(3).Capture();
        var regex = p.Compile();

        // Should be a capturing group with \d{3}
        Assert.Equal("(\\d{3})", regex);
    }

    [Fact]
    public void InspectDigitCaptureCompiledChars()
    {
        var p = Strling.Simply.S.Digit(3).Capture();
        var regex = p.Compile();

        // Check the char sequence so we can see whether there are one or two backslashes
        // Expect: '(' '\\' 'd' '{' '3' '}' ')' ...
        Assert.True(regex.Length >= 5, "regex too short");
        Assert.Equal('(', regex[0]);
        Assert.Equal('\\', regex[1]);
        // Check for a single backslash at position 1 and 'd' at 2
        Assert.Equal('d', regex[2]);
        Assert.Equal('{', regex[3]);
    }

    [Fact]
    public void InspectPhoneCompiledChars()
    {
        var phone = Strling.Simply.S.Sequence(
            Strling.Simply.S.Start(),
            Strling.Simply.S.Digit(3).Capture(),
            Strling.Simply.S.AnyOf("-. ").Optional(),
            Strling.Simply.S.Digit(3).Capture(),
            Strling.Simply.S.AnyOf("-. ").Optional(),
            Strling.Simply.S.Digit(4).Capture(),
            Strling.Simply.S.End()
        );

        var regex = phone.Compile();
        // Expect at '^(' then a single backslash then 'd'
        Assert.True(regex.Length >= 4);
        Assert.Equal('^', regex[0]);
        Assert.Equal('(', regex[1]);
        Assert.Equal('\\', regex[2]);
        Assert.Equal('d', regex[3]);
    }

    [Fact]
    public void DumpPhoneRegexToFile()
    {
        var phone = Strling.Simply.S.Sequence(
            Strling.Simply.S.Start(),
            Strling.Simply.S.Digit(3).Capture(),
            Strling.Simply.S.AnyOf("-. ").Optional(),
            Strling.Simply.S.Digit(3).Capture(),
            Strling.Simply.S.AnyOf("-. ").Optional(),
            Strling.Simply.S.Digit(4).Capture(),
            Strling.Simply.S.End()
        );

        var regex = phone.Compile();
        System.IO.File.WriteAllText("/tmp/phone_regex.txt", regex);
    }
}
