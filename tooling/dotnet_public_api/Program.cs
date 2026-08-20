using System.Reflection;
using System.Runtime.Loader;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace STRling.Tooling.DotNetPublicApi;

internal static class Program
{
    private const BindingFlags DeclaredPublic =
        BindingFlags.Public | BindingFlags.Instance | BindingFlags.Static | BindingFlags.DeclaredOnly;

    private static int Main(string[] args)
    {
        if (args.Length != 4 || args[0] != "--assembly" || args[2] != "--prefix")
        {
            Console.Error.WriteLine(
                "usage: STRling.DotNetPublicApi --assembly <path> --prefix <stable-prefix>"
            );
            return 2;
        }

        var assemblyPath = Path.GetFullPath(args[1]);
        var prefix = args[3];
        if (!Path.IsPathFullyQualified(assemblyPath) || !File.Exists(assemblyPath))
        {
            Console.Error.WriteLine($"assembly does not exist: {assemblyPath}");
            return 2;
        }

        var directory = Path.GetDirectoryName(assemblyPath)!;
        AssemblyLoadContext.Default.Resolving += (_, name) =>
        {
            var candidate = Path.Combine(directory, $"{name.Name}.dll");
            if (File.Exists(candidate))
            {
                return AssemblyLoadContext.Default.LoadFromAssemblyPath(candidate);
            }
            var dotnetRoot = Path.GetDirectoryName(Environment.ProcessPath);
            var sdkRoot = dotnetRoot is null ? null : Path.Combine(dotnetRoot, "sdk");
            var sdkCandidate = sdkRoot is not null && Directory.Exists(sdkRoot)
                ? Directory.EnumerateFiles(
                        sdkRoot,
                        $"{name.Name}.dll",
                        SearchOption.AllDirectories
                    )
                    .Where(path => path.Contains($"{Path.DirectorySeparatorChar}FSharp{Path.DirectorySeparatorChar}", StringComparison.Ordinal))
                    .OrderDescending(StringComparer.Ordinal)
                    .FirstOrDefault()
                : null;
            return sdkCandidate is not null
                ? AssemblyLoadContext.Default.LoadFromAssemblyPath(sdkCandidate)
                : null;
        };

        try
        {
            var assembly = AssemblyLoadContext.Default.LoadFromAssemblyPath(assemblyPath);
            var symbols = Extract(prefix, assembly);
            Console.WriteLine(JsonSerializer.Serialize(symbols));
            return 0;
        }
        catch (Exception error)
        {
            Console.Error.WriteLine(error);
            return 1;
        }
    }

    private static SortedDictionary<string, string> Extract(string prefix, Assembly assembly)
    {
        var symbols = new SortedDictionary<string, string>(StringComparer.Ordinal);
        var identity = assembly.GetName();
        Add(
            symbols,
            prefix,
            "assembly",
            identity.Name ?? "<unnamed>",
            $"assembly {identity.Name} version {identity.Version}"
        );

        foreach (var type in assembly.GetExportedTypes().OrderBy(StableTypeName, StringComparer.Ordinal))
        {
            var typeName = StableTypeName(type);
            Add(symbols, prefix, "type", typeName, FormatTypeDeclaration(type));

            foreach (var constructor in type.GetConstructors(DeclaredPublic).OrderBy(FormatMethod, StringComparer.Ordinal))
            {
                Add(symbols, prefix, typeName, "constructor", FormatMethod(constructor));
            }

            foreach (var method in type.GetMethods(DeclaredPublic).OrderBy(FormatMethod, StringComparer.Ordinal))
            {
                if (method.IsSpecialName && IsAccessor(method.Name))
                {
                    continue;
                }
                Add(symbols, prefix, typeName, "method", FormatMethod(method));
            }

            foreach (var property in type.GetProperties(DeclaredPublic).OrderBy(FormatProperty, StringComparer.Ordinal))
            {
                if (property.GetMethod?.IsPublic == true || property.SetMethod?.IsPublic == true)
                {
                    Add(symbols, prefix, typeName, "property", FormatProperty(property));
                }
            }

            foreach (var field in type.GetFields(DeclaredPublic).OrderBy(FormatField, StringComparer.Ordinal))
            {
                Add(symbols, prefix, typeName, "field", FormatField(field));
            }

            foreach (var eventInfo in type.GetEvents(DeclaredPublic).OrderBy(FormatEvent, StringComparer.Ordinal))
            {
                Add(symbols, prefix, typeName, "event", FormatEvent(eventInfo));
            }
        }
        return symbols;
    }

    private static bool IsAccessor(string name) =>
        name.StartsWith("get_", StringComparison.Ordinal)
        || name.StartsWith("set_", StringComparison.Ordinal)
        || name.StartsWith("add_", StringComparison.Ordinal)
        || name.StartsWith("remove_", StringComparison.Ordinal);

    private static void Add(
        IDictionary<string, string> symbols,
        params string[] parts
    )
    {
        var value = parts[^1];
        var signature = Convert.ToHexString(
            SHA256.HashData(Encoding.UTF8.GetBytes(value))
        ).ToLowerInvariant();
        var key = $"{string.Join(":", parts[..^1].Select(EscapeKey))}:{signature}";
        if (!symbols.TryAdd(key, value))
        {
            throw new InvalidOperationException($"duplicate normalized public symbol: {key}");
        }
    }

    private static string EscapeKey(string value) =>
        value.Replace("%", "%25", StringComparison.Ordinal)
            .Replace(":", "%3A", StringComparison.Ordinal);

    private static string FormatTypeDeclaration(Type type)
    {
        var kind = type.IsInterface
            ? "interface"
            : type.IsEnum
                ? "enum"
                : typeof(MulticastDelegate).IsAssignableFrom(type.BaseType)
                    ? "delegate"
                    : type.IsValueType
                        ? "struct"
                        : "class";
        var modifiers = new List<string> { "public" };
        if (type.IsAbstract && type.IsSealed)
        {
            modifiers.Add("static");
        }
        else
        {
            if (type.IsAbstract) modifiers.Add("abstract");
            if (type.IsSealed) modifiers.Add("sealed");
        }
        modifiers.Add(kind);
        modifiers.Add(StableTypeName(type));
        if (type.BaseType is not null && type.BaseType != typeof(object) && !type.IsEnum)
        {
            modifiers.Add($": {FormatType(type.BaseType)}");
        }
        var interfaces = type.GetInterfaces().Select(FormatType).Order(StringComparer.Ordinal).ToArray();
        if (interfaces.Length > 0)
        {
            modifiers.Add($" interfaces [{string.Join(", ", interfaces)}]");
        }
        return string.Concat(string.Join(" ", modifiers), FormatGenericConstraints(type), FormatAttributes(type));
    }

    private static string FormatMethod(MethodBase method)
    {
        var modifiers = new List<string> { "public" };
        if (method.IsStatic) modifiers.Add("static");
        if (method.IsAbstract) modifiers.Add("abstract");
        if (method.IsVirtual && !method.IsAbstract && !method.IsFinal) modifiers.Add("virtual");
        if (method.IsFinal && method.IsVirtual) modifiers.Add("final");
        var returnType = method is MethodInfo info ? FormatType(info.ReturnType) : "void";
        var generic = method.IsGenericMethodDefinition
            ? $"<{string.Join(",", method.GetGenericArguments().Select(argument => argument.Name))}>"
            : string.Empty;
        var parameters = string.Join(", ", method.GetParameters().Select(FormatParameter));
        return string.Concat(
            string.Join(" ", modifiers),
            " ",
            returnType,
            " ",
            method.Name,
            generic,
            "(",
            parameters,
            ")",
            FormatGenericConstraints(method),
            FormatAttributes(method)
        );
    }

    private static string FormatProperty(PropertyInfo property)
    {
        var accessors = new List<string>();
        if (property.GetMethod?.IsPublic == true) accessors.Add("get");
        if (property.SetMethod?.IsPublic == true) accessors.Add("set");
        var index = property.GetIndexParameters();
        var name = index.Length == 0
            ? property.Name
            : $"{property.Name}[{string.Join(", ", index.Select(FormatParameter))}]";
        return $"public {FormatType(property.PropertyType)} {name} {{ {string.Join("; ", accessors)}; }}{FormatAttributes(property)}";
    }

    private static string FormatField(FieldInfo field)
    {
        var modifiers = new List<string> { "public" };
        if (field.IsStatic) modifiers.Add("static");
        if (field.IsLiteral) modifiers.Add("const");
        else if (field.IsInitOnly) modifiers.Add("readonly");
        var constant = field.IsLiteral ? $" = {FormatValue(field.GetRawConstantValue())}" : string.Empty;
        return $"{string.Join(" ", modifiers)} {FormatType(field.FieldType)} {field.Name}{constant}{FormatAttributes(field)}";
    }

    private static string FormatEvent(EventInfo eventInfo) =>
        $"public event {FormatType(eventInfo.EventHandlerType ?? typeof(void))} {eventInfo.Name}{FormatAttributes(eventInfo)}";

    private static string FormatParameter(ParameterInfo parameter)
    {
        var modifiers = new List<string>();
        if (parameter.IsOut) modifiers.Add("out");
        else if (parameter.ParameterType.IsByRef) modifiers.Add("ref");
        if (parameter.GetCustomAttributesData().Any(attribute => attribute.AttributeType.FullName == "System.ParamArrayAttribute"))
        {
            modifiers.Add("params");
        }
        modifiers.Add(FormatType(parameter.ParameterType));
        modifiers.Add(parameter.Name ?? $"arg{parameter.Position}");
        if (parameter.HasDefaultValue)
        {
            modifiers.Add($"= {FormatValue(parameter.DefaultValue)}");
        }
        return string.Join(" ", modifiers) + FormatAttributes(parameter);
    }

    private static string FormatType(Type type)
    {
        if (type.IsByRef) return $"{FormatType(type.GetElementType()!)}&";
        if (type.IsPointer) return $"{FormatType(type.GetElementType()!)}*";
        if (type.IsArray) return $"{FormatType(type.GetElementType()!)}[{new string(',', type.GetArrayRank() - 1)}]";
        if (type.IsGenericParameter) return $"!{type.Name}";
        if (!type.IsGenericType) return StableTypeName(type);
        var definition = type.GetGenericTypeDefinition();
        var name = StableTypeName(definition);
        var tick = name.IndexOf('`');
        if (tick >= 0) name = name[..tick];
        return $"{name}<{string.Join(",", type.GetGenericArguments().Select(FormatType))}>";
    }

    private static string StableTypeName(Type type) =>
        (type.FullName ?? type.Name).Replace('+', '.');

    private static string FormatGenericConstraints(MemberInfo member)
    {
        var arguments = member switch
        {
            Type type when type.IsGenericTypeDefinition => type.GetGenericArguments(),
            MethodInfo method when method.IsGenericMethodDefinition => method.GetGenericArguments(),
            _ => Array.Empty<Type>(),
        };
        var clauses = new List<string>();
        foreach (var argument in arguments)
        {
            var constraints = new List<string>();
            var attributes = argument.GenericParameterAttributes;
            if (attributes.HasFlag(GenericParameterAttributes.ReferenceTypeConstraint)) constraints.Add("class");
            if (attributes.HasFlag(GenericParameterAttributes.NotNullableValueTypeConstraint)) constraints.Add("struct");
            constraints.AddRange(argument.GetGenericParameterConstraints().Select(FormatType));
            if (attributes.HasFlag(GenericParameterAttributes.DefaultConstructorConstraint)) constraints.Add("new()");
            if (constraints.Count > 0) clauses.Add($" where {argument.Name} : {string.Join(", ", constraints)}");
        }
        return string.Concat(clauses);
    }

    private static string FormatAttributes(ICustomAttributeProvider provider)
    {
        IEnumerable<CustomAttributeData> attributes = provider switch
        {
            MemberInfo member => member.GetCustomAttributesData(),
            ParameterInfo parameter => parameter.GetCustomAttributesData(),
            _ => Array.Empty<CustomAttributeData>(),
        };
        var normalized = attributes
            .Select(attribute => attribute.AttributeType.FullName ?? attribute.AttributeType.Name)
            .Where(name => name != "System.Runtime.CompilerServices.CompilerGeneratedAttribute")
            .Order(StringComparer.Ordinal)
            .ToArray();
        return normalized.Length == 0 ? string.Empty : $" attributes [{string.Join(", ", normalized)}]";
    }

    private static string FormatValue(object? value) => value switch
    {
        null => "null",
        string text => JsonSerializer.Serialize(text),
        char character => JsonSerializer.Serialize(character.ToString()),
        bool boolean => boolean ? "true" : "false",
        _ => Convert.ToString(value, System.Globalization.CultureInfo.InvariantCulture) ?? "null",
    };
}
