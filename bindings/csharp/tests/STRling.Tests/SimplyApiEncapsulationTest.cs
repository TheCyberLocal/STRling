using System;
using System.Linq;
using System.Reflection;
using Xunit;

namespace STRling.Tests
{
    public class SimplyApiEncapsulationTest
    {
        [Fact]
        public void SimplyPublicApiDoesNotExposeCoreAstTypes()
        {
            const string forbidden = "Strling.Core";

            var patternType = typeof(Strling.Simply.Pattern);
            var sType = typeof(Strling.Simply.S);

            Assert.NotNull(patternType);
            Assert.NotNull(sType);

            void CheckMemberTypes(Type t)
            {
                var methods = t.GetMethods(BindingFlags.Public | BindingFlags.Instance | BindingFlags.Static | BindingFlags.DeclaredOnly);
                foreach (var m in methods)
                {
                    Assert.DoesNotContain(forbidden, m.ReturnType?.FullName ?? string.Empty, StringComparison.Ordinal);
                    foreach (var p in m.GetParameters()) Assert.DoesNotContain(forbidden, p.ParameterType?.FullName ?? string.Empty, StringComparison.Ordinal);
                }

                var props = t.GetProperties(BindingFlags.Public | BindingFlags.Instance | BindingFlags.Static | BindingFlags.DeclaredOnly);
                foreach (var p in props) Assert.DoesNotContain(forbidden, p.PropertyType?.FullName ?? string.Empty, StringComparison.Ordinal);
            }

            CheckMemberTypes(patternType);
            CheckMemberTypes(sType);
        }
    }
}
