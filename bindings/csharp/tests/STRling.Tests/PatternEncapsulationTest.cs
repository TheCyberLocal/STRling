using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using Xunit;

namespace STRling.Tests;

public class PatternEncapsulationTest
{
    [Fact]
    public void PublicApiDoesNotExposeCoreAstTypes()
    {
        var asm = typeof(Strling.Simply.Pattern).Assembly;

        var exported = asm.GetExportedTypes()
            .Where(t => t.Namespace != null && t.Namespace.StartsWith("Strling.Simply", StringComparison.Ordinal));

        var issues = new List<string>();

        foreach (var t in exported)
        {
            // Inspect public methods
            var methods = t.GetMethods(BindingFlags.Public | BindingFlags.Instance | BindingFlags.Static | BindingFlags.DeclaredOnly);
            foreach (var m in methods)
            {
                CheckType(m.ReturnType, t, m.Name, issues);
                foreach (var p in m.GetParameters()) CheckType(p.ParameterType, t, m.Name, issues);
            }

            // Inspect public properties
            var props = t.GetProperties(BindingFlags.Public | BindingFlags.Instance | BindingFlags.Static | BindingFlags.DeclaredOnly);
            foreach (var p in props) CheckType(p.PropertyType, t, p.Name, issues);

            // Inspect public fields
            var fields = t.GetFields(BindingFlags.Public | BindingFlags.Static | BindingFlags.Instance | BindingFlags.DeclaredOnly);
            foreach (var f in fields) CheckType(f.FieldType, t, f.Name, issues);
        }

        if (issues.Count > 0)
        {
            var msg = string.Join("\n", issues);
            Assert.False(true, "Public API surface leaks internal core types:\n" + msg);
        }
    }

    private void CheckType(Type t, Type owner, string memberName, List<string> issues)
    {
        if (t == null) return;

        // Unwrap arrays and generics
        if (t.IsArray) t = t.GetElementType()!;

        if (IsCoreType(t))
        {
            issues.Add($"{owner.FullName}.{memberName} -> {t.FullName}");
            return;
        }

        if (t.IsGenericType)
        {
            foreach (var arg in t.GetGenericArguments())
            {
                CheckType(arg, owner, memberName, issues);
            }
        }
    }

    private bool IsCoreType(Type t)
    {
        if (t == null || t.Namespace == null) return false;
        // Consider types from the core AST namespace a failure
        return t.Namespace.StartsWith("Strling.Core", StringComparison.Ordinal);
    }
}
