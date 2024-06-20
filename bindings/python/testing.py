from STRling import lib
import re

# Test script
def test_strling():
    # Test literal
    pattern = lib.lit("hello")
    assert re.fullmatch(pattern, "hello")

    # Test digit with range
    pattern = lib.digit(min=2, max=4)
    assert re.fullmatch(pattern, "123")
    assert not re.fullmatch(pattern, "1")

    # Test letter with range
    pattern = lib.letter(min=1, max=3)
    assert re.fullmatch(pattern, "abc")
    assert not re.fullmatch(pattern, "abcd")

    # Test between
    pattern = lib.between('a', 'f', 2)
    assert re.fullmatch(pattern, "ab")
    assert not re.fullmatch(pattern, "agh")

    # Test in and notin
    pattern = lib.in_("abc", 2)
    assert re.fullmatch(pattern, "ab")
    pattern = lib.notin("abc", 1, 2)
    assert re.fullmatch(pattern, "de")
    assert not re.fullmatch(pattern, "ae")

    # Test space, newline, tab, carriage
    pattern = lib.space(1)
    assert re.fullmatch(pattern, " ")
    pattern = lib.newline(1)
    assert re.fullmatch(pattern, "\n")
    pattern = lib.tab(1)
    assert re.fullmatch(pattern, "\t")
    pattern = lib.carriage(1)
    assert re.fullmatch(pattern, "\r")

    # Test or
    pattern = lib.or_(lib.digit(), lib.letter())
    assert re.fullmatch(pattern, "1")
    assert re.fullmatch(pattern, "a")
    assert not re.fullmatch(pattern, "&")

    # Test may
    pattern = lib.may(lib.digit())
    assert re.fullmatch(pattern, "")
    assert re.fullmatch(pattern, "1")

    # Test start and end
    pattern = lib.start() + lib.lit("start") + lib.end()
    assert re.fullmatch(pattern, "start")
    assert not re.fullmatch(pattern, " notstart")

    # Test lookarounds
    pattern = lib.ahead(lib.lit("hello")) + lib.lit("world")
    assert re.search(pattern, "helloworld")
    pattern = lib.behind(lib.lit("hello")) + lib.lit("world")
    assert re.search(pattern, "helloworld")
    pattern = lib.notahead(lib.lit("hello")) + lib.lit("world")
    assert not re.search(pattern, "helloworld")
    pattern = lib.notbehind(lib.lit("hello")) + lib.lit("world")
    assert not re.search(pattern, "helloworld")

    # Test grouping
    pattern = lib.group("digits", lib.digit(min=3))
    match = re.match(pattern, "123")
    assert match and match.group("digits") == "123"

    # Test merging
    pattern = lib.merge(lib.lit("hello"), lib.lit("world"))
    assert re.fullmatch(pattern, "helloworld")

    print("All tests passed!")

# Run the test script
test_strling()


"""
Here is the current problem with between:
Traceback (most recent call last):
  File "/home/tim3i/my-projects/STRling/test.py", line 80, in <module>
    test_strling()
  File "/home/tim3i/my-projects/STRling/test.py", line 21, in test_strling
    pattern = lib.between('a', 'f', 2)
  File "/home/tim3i/my-projects/STRling/STRling/lib.py", line 7, in wrapper
    pattern = func(*args, **kwargs)
TypeError: between() takes 2 positional arguments but 3 were given
"""
