# API Reference

## Pattern

Create a new pattern using the entry point.

```go
import "github.com/thecyberlocal/strling/bindings/go/simply"

// Create a literal pattern
pattern := simply.Lit("hello")
```

## Quantifiers

Control how many times an element should match.

```go
// Match "a" one or more times
simply.Lit("a").Plus()

// Match "b" zero or more times
simply.Lit("b").Star()

// Match "c" optionally
simply.Lit("c").Opt()
```

## Groups

Group elements together for capturing or applying quantifiers.

```go
// Capturing group
simply.Group(simply.Lit("abc"))

// Named group
simply.Capture("my_group", simply.Lit("123"))
```

## Character Classes

Match specific sets of characters.

```go
// Digit
simply.Digit()

// Word character
simply.Word()

// Custom class [a-z]
simply.Set("a-z")
```

## Anchors

Bind matches to specific positions in the string.

```go
// Start of string
simply.Start()

// End of string
simply.End()
```

## Lookarounds

Assert what follows or precedes the current position without including it in the match.

```go
// Positive lookahead
simply.Lookahead(simply.Lit("foo"))

// Negative lookbehind
simply.LookbehindNot(simply.Lit("bar"))
```
