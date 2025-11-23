# API Reference

## Pattern

Create a new pattern using the entry point.

```java
import com.strling.simply.Simply;

// Create a literal pattern
var pattern = Simply.lit("hello");
```

## Quantifiers

Control how many times an element should match.

```java
// Match "a" one or more times
Simply.lit("a").plus();

// Match "b" zero or more times
Simply.lit("b").star();

// Match "c" optionally
Simply.lit("c").opt();
```

## Groups

Group elements together for capturing or applying quantifiers.

```java
// Capturing group
Simply.group(Simply.lit("abc"));

// Named group
Simply.capture("my_group", Simply.lit("123"));
```

## Character Classes

Match specific sets of characters.

```java
// Digit
Simply.digit();

// Word character
Simply.word();

// Custom class [a-z]
Simply.set("a-z");
```

## Anchors

Bind matches to specific positions in the string.

```java
// Start of string
Simply.start();

// End of string
Simply.end();
```

## Lookarounds

Assert what follows or precedes the current position without including it in the match.

```java
// Positive lookahead
Simply.lookahead(Simply.lit("foo"));

// Negative lookbehind
Simply.lookbehindNot(Simply.lit("bar"));
```
