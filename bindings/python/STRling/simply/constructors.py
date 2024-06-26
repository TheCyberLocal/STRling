
from .pattern import Pattern, clean_params, check_unique_groups



############################
# Constructor Methods
########


def any_of(*patterns):
    """
    Matches any provided pattern, including patterns consisting of subpatterns.

    Example: simply as s
        - Matches 3 digits followed by 3 letters.

        pattern1 = s.merge(s.digit(3), s.letter(3))

        - Matches 3 letters followed by 3 digits.

        pattern2 = s.merge(s.letter(3), s.digit(3))

        - Matches either pattern1 or pattern2.

        either_pattern = s.any_of(pattern1, pattern2)

    Parameters:
    - *patterns (Pattern/str): One or more patterns to be matched.

    Returns:
    - Pattern: A Pattern object representing the OR combination of the given patterns.

    Raises:
    - ValueError: If any of the parameters are not an instance of Pattern or str.
    """

    clean_patterns = clean_params(*patterns)

    sub_names = check_unique_groups(*clean_patterns)

    joined = '|'.join(f'(?:{str(p)})' for p in clean_patterns)
    new_pattern = f'(?:{joined})'

    return Pattern(new_pattern, composite=True, named_groups=sub_names)

def may(*patterns):
    """
    Optionally matches the provided patterns. If this pattern is absent, surrounding patterns can still match.

    Example: simply as s
        - Matches any letter, along with any trailing digit.

        pattern = s.merge(s.letter(), s.may(s.digit()))

        In the text, "AB2" the pattern above matches 'A' and 'B2'.

    Parameters:
    - *patterns (Pattern/str): One or more patterns to be optionally matched.

    Returns:
    - Pattern: A Pattern object representing the optional match of the given patterns.

    Raises:
    - ValueError: If any of the parameters are not an instance of Pattern or str.
    """

    clean_patterns = clean_params(*patterns)

    sub_names = check_unique_groups(*clean_patterns)

    joined = merge(*clean_patterns)
    new_pattern = f'{joined}?'

    return Pattern(new_pattern, composite=True, named_groups=sub_names)



def merge(*patterns):
    """
    Combines the provided patterns into one larger pattern.

    Example: simply as s
        - Matches any digit, comma, or period.

        merged_pattern = s.merge(s.digit(), ',.')

    Parameters:
    - *patterns (Pattern/str): One or more patterns to be concatenated.

    Returns:
    - Pattern: A Pattern object representing the concatenation of the given patterns.

    Raises:
    - ValueError: If any of the parameters are not an instance of Pattern or str.
    """

    clean_patterns = clean_params(*patterns)

    sub_names = check_unique_groups(*clean_patterns)

    joined = ''.join(str(p) for p in clean_patterns)
    new_pattern = f'(?:{joined})'

    return Pattern(new_pattern, composite=True, named_groups=sub_names)

def capture(*patterns):
    """
    Creates a numbered group that can be indexed for extracting this part of the match.

    - Captures CANNOT be invoked with a range.

    s.capture(s.digit(), s.letter())(1, 2) <== INVALID

    - Captures CAN be invoked with a number of copies.

    s.capture(s.digit(), s.letter())(3) <== VALID

    Example: simply as s
        - Matches any digit, comma, or period.

        captured_pattern = s.capture(s.digit(), ',.')


    Parameters:
    - *patterns (Pattern/str): One or more patterns to be captured.

    Returns:
    - Pattern: A Pattern object representing the capturing group of the given patterns.

    Raises:
    - ValueError: If any of the parameters are not an instance of Pattern or str.

    Referencing: simply as s
        three_digit_group = s.capture(s.digit(3))

        four_groups_of_three = three_digit_groups(4)

        example_text = "Here is a number: 111222333444"

        match = re.search(str(four_groups_of_three), example_text)  # Notice str(pattern)

        print("Full Match:", match.group())
        print("First:", match.group(1))
        print("Second:", match.group(2))
        print("Third:", match.group(3))
        print("Fourth:", match.group(4))

        # Output:
        # Full Match: 111222333444
        # First: 111
        # Second: 222
        # Third: 333
        # Fourth: 444
    """

    clean_patterns = clean_params(*patterns)

    sub_names = check_unique_groups(*clean_patterns)

    joined = ''.join(str(p) for p in clean_patterns)
    new_pattern = f'({joined})'

    return Pattern(new_pattern, composite=True, numbered_group=True, named_groups=sub_names)

def group(name, *patterns):
    """
    Creates a unique named group that can be referenced for extracting this part of the match.

    - Groups CANNOT be invoked with a range.

    s.group('name', s.digit())(1, 2) <== INVALID

    Example: simply as s
        - Matches any digit followed by a comma and period.

        named_pattern = s.group('my_group', s.digit(), ',.')

    Parameters:
    - name (str): The name of the capturing group.
    - *patterns (Pattern/str): One or more patterns to be captured.

    Returns:
    - Pattern: A Pattern object representing the named capturing group of the given patterns.

    Raises:
    - ValueError: If any of the parameters are not an instance of Pattern or str.

    Referencing: simply as s
        first = s.group("first", s.digit(3))

        second = s.group("second", s.digit(3))

        third = s.group("third", s.digit(4))

        phone_number_pattern = s.merge(first, "-", second, "-", third)

        example_text = "Here is a phone number: 123-456-7890."

        match = re.search(str(phone_number_pattern), example_text) # Notice str(pattern)

        print("Full Match:", match.group())
        print("First:", match.group("first"))
        print("Second:", match.group("second"))
        print("Third:", match.group("third"))

        # Output:
        # Full Match: 123-456-7890
        # First: 123
        # Second: 456
        # Third: 7890
    """

    if not isinstance(name, str):
        raise ValueError("The `name` parameter must be a string like 'group_name'.")

    clean_patterns = clean_params(*patterns)

    sub_names = check_unique_groups(*clean_patterns)

    joined = ''.join(str(p) for p in clean_patterns)
    new_pattern = f'(?P<{name}>{joined})'

    return Pattern(new_pattern, composite=True, named_groups=[name, *sub_names])
