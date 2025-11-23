# API Reference

## Pattern

Create a new pattern using the entry point.

```python
from STRling import simply as s

# Create a literal pattern
pattern = s.lit("hello")
```

## Quantifiers

Control how many times an element should match.

```python
# Match "a" one or more times
s.lit("a").plus()

# Match "b" zero or more times
s.lit("b").star()

# Match "c" optionally
s.lit("c").opt()
```

## Groups

Group elements together for capturing or applying quantifiers.

```python
# Capturing group
s.group(s.lit("abc"))

# Named group
s.capture("my_group", s.lit("123"))
```

## Character Classes

Match specific sets of characters.

```python
# Digit
s.digit()

# Word character
s.word()

# Custom class [a-z]
s.set("a-z")
```

## Anchors

Bind matches to specific positions in the string.

```python
# Start of string
s.start()

# End of string
s.end()
```

## Lookarounds

Assert what follows or precedes the current position without including it in the match.

```python
# Positive lookahead
s.lookahead(s.lit("foo"))

# Negative lookbehind
s.lookbehind_not(s.lit("bar"))
```
