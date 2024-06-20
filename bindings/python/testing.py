from STRling import lib, group, merge
import re


# Test the functionality
def test_strling():
    # Test digit with range
    num1 = lib.digit()
    pattern = group('group1', num1(3))
    print("num1 =>", num1)
    print("pattern =>", pattern)
    assert re.fullmatch(str(pattern), "123")
    print("Digit group test passed")

    # Test letter with range
    let1 = lib.letter()
    pattern = group('group2', let1(1, 3))
    assert re.fullmatch(str(pattern), "abc")
    assert not re.fullmatch(str(pattern), "abcd")
    print("Letter range group test passed")

    # Test between with range
    between1 = lib.between('a', 'f')
    pattern = group('group3', between1(1, 2))
    assert re.fullmatch(str(pattern), "ab")
    assert not re.fullmatch(str(pattern), "agh")
    print("Between range group test passed")

    # Test in and notin with range
    in1 = lib.in_("abc")
    pattern = group('group4', in1(1, 2))
    assert re.fullmatch(str(pattern), "ab")
    notin1 = lib.notin("abc")
    pattern = group('group5', notin1(1, 2))
    assert re.fullmatch(str(pattern), "de")
    assert not re.fullmatch(str(pattern), "ae")
    print("In and NotIn range group test passed")

    # Test whitespace characters with range
    space1 = lib.space()
    pattern = group('group6', space1(1))
    assert re.fullmatch(str(pattern), " ")
    newline1 = lib.newline()
    pattern = group('group7', newline1(1))
    assert re.fullmatch(str(pattern), "\n")
    tab1 = lib.tab()
    pattern = group('group8', tab1(1))
    assert re.fullmatch(str(pattern), "\t")
    carriage1 = lib.carriage()
    pattern = group('group9', carriage1(1))
    assert re.fullmatch(str(pattern), "\r")
    print("Whitespace characters range group tests passed")

    # Test or
    pattern = lib.or_(lib.digit(), lib.letter())
    assert re.fullmatch(str(pattern), "1")
    assert re.fullmatch(str(pattern), "a")
    assert not re.fullmatch(str(pattern), "&")
    print("Or test passed")

    # Test may
    pattern = lib.may(lib.digit())
    assert re.fullmatch(str(pattern), "")
    assert re

test_strling()
