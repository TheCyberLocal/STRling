using Xunit;
using Strling.Simply;

namespace STRling.Tests;

public class UsPhoneTest
{
    [Fact]
    public void FluentApiProducesExpectedRegexString()
    {
        var phone = S.Sequence(
            S.Start(),
            S.Digit(3).Capture(),
            S.AnyOf("-. ").Optional(),
            S.Digit(3).Capture(),
            S.AnyOf("-. ").Optional(),
            S.Digit(4).Capture(),
            S.End()
        );

        var regex = phone.Compile();
        System.IO.File.WriteAllText("/tmp/us_phone_regex.txt", regex);

        Assert.Equal(@"^(\d{3})[-. ]?(\d{3})[-. ]?(\d{4})$", regex);
    }
}
