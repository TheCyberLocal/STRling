from .pattern import STRlingError, Pattern, lit


def any_of(*patterns):
    """
    Matches any provided pattern, including patterns consisting of subpatterns.

    Parameters:
    - *patterns (Pattern/str): One or more patterns to be matched.

    Returns:
    - An instance of the Pattern class.

    Examples:
        ```
        # Matches 3 digits followed by 3 letters.
        pattern1 = s.merge(s.digit(3), s.letter(3))

        # Matches 3 letters followed by 3 digits.
        pattern2 = s.merge(s.letter(3), s.digit(3))

        # Matches either pattern1 or pattern2.
        either_pattern = s.any_of(pattern1, pattern2)
        ```
    """

    clean_patterns = []
    for pattern in patterns:
        if isinstance(pattern, str):
            pattern = lit(pattern)

        if not isinstance(pattern, Pattern):
            message = """
            Method: simply.any_of(*patterns)

            The parameters must be instances of `Pattern` or `str`.

            Use a string such as "123abc$" to match literal characters, or use a predefined set like `simply.letter()`.
            """
            raise STRlingError(message)

        clean_patterns.append(pattern)


    named_group_counts = {}
    for pattern in clean_patterns:
        for group_name in pattern.named_groups:
            if group_name in named_group_counts:
                named_group_counts[group_name] += 1
            else:
                named_group_counts[group_name] = 1

    duplicates = {name: count for name, count in named_group_counts.items() if count > 1}
    if duplicates:
        duplicate_info = ", ".join([f"{name}: {count}" for name, count in duplicates.items()])
        message = f"""
        Method: simply.any_of(*patterns)

        Named groups must be unique.
        Duplicate named groups found: {duplicate_info}.

        If you need later reference change the named group argument to `simply.capture()`.
        If you don't need later reference change the named group argument to `simply.merge()`.
        """
        raise STRlingError(message)

    sub_names = named_group_counts.keys()

    joined = '|'.join(str(p) for p in clean_patterns)
    new_pattern = f'(?:{joined})'

    return Pattern(new_pattern, composite=True, named_groups=sub_names)

def may(*patterns):
    """
    Optionally matches the provided patterns. If this pattern is absent, surrounding patterns can still match.

    Parameters:
    - *patterns (Pattern/str): One or more patterns to be optionally matched.

    Returns:
    - An instance of the Pattern class.

    Examples:
        ```
        # Matches any letter, along with any trailing digit.
        pattern = s.merge(s.letter(), s.may(s.digit()))

        # In the text "AB2" the pattern above matches 'A' and 'B2'.
        ```
    """

    clean_patterns = []
    for pattern in patterns:
        if isinstance(pattern, str):
            pattern = lit(pattern)

        if not isinstance(pattern, Pattern):
            message = """
            Method: simply.may(*patterns)

            The parameters must be instances of `Pattern` or `str`.

            Use a string such as "123abc$" to match literal characters, or use a predefined set like `simply.letter()`.
            """
            raise STRlingError(message)

        clean_patterns.append(pattern)


    named_group_counts = {}
    for pattern in clean_patterns:
        for group_name in pattern.named_groups:
            if group_name in named_group_counts:
                named_group_counts[group_name] += 1
            else:
                named_group_counts[group_name] = 1

    duplicates = {name: count for name, count in named_group_counts.items() if count > 1}
    if duplicates:
        duplicate_info = ", ".join([f"{name}: {count}" for name, count in duplicates.items()])
        message = f"""
        Method: simply.may(*patterns)

        Named groups must be unique.
        Duplicate named groups found: {duplicate_info}.

        If you need later reference change the named group argument to `simply.capture()`.
        If you don't need later reference change the named group argument to `simply.merge()`.
        """
        raise STRlingError(message)

    sub_names = named_group_counts.keys()

    joined = merge(*clean_patterns)
    new_pattern = f'{joined}?'

    return Pattern(new_pattern, composite=True, named_groups=sub_names)



def merge(*patterns):
    """
    Combines the provided patterns into one larger pattern.

    Parameters:
    - *patterns (Pattern/str): One or more patterns to be concatenated.

    Returns:
    - An instance of the Pattern class.

    Examples:
        ```
        # Matches any digit followed by a comma and period.
        merged_pattern = s.merge(s.digit(), ',.')
        ```
    """

    clean_patterns = []
    for pattern in patterns:
        if isinstance(pattern, str):
            pattern = lit(pattern)

        if not isinstance(pattern, Pattern):
            message = """
            Method: simply.merge(*patterns)

            The parameters must be instances of `Pattern` or `str`.

            Use a string such as "123abc$" to match literal characters, or use a predefined set like `simply.letter()`.
            """
            raise STRlingError(message)

        clean_patterns.append(pattern)


    named_group_counts = {}
    for pattern in clean_patterns:
        for group_name in pattern.named_groups:
            if group_name in named_group_counts:
                named_group_counts[group_name] += 1
            else:
                named_group_counts[group_name] = 1

    duplicates = {name: count for name, count in named_group_counts.items() if count > 1}
    if duplicates:
        duplicate_info = ", ".join([f"{name}: {count}" for name, count in duplicates.items()])
        message = f"""
        Method: simply.merge(*patterns)

        Named groups must be unique.
        Duplicate named groups found: {duplicate_info}.

        If you need later reference change the named group argument to `simply.capture()`.
        If you don't need later reference change the named group argument to `simply.merge()`.
        """
        raise STRlingError(message)

    sub_names = named_group_counts.keys()

    joined = ''.join(str(p) for p in clean_patterns)
    new_pattern = f'(?:{joined})'

    return Pattern(new_pattern, composite=True, named_groups=sub_names)

def capture(*patterns):
    """
    Creates a numbered group that can be indexed for extracting this part of the match.

    Parameters:
    - *patterns (Pattern/str): One or more patterns to be captured.

    Returns:
    - An instance of the Pattern class.

    Ranges:
        ```
        # Captures CANNOT be invoked with a range.
        s.capture(s.digit(), s.letter())(1, 2) # <== INVALID

        # Captures CAN be invoked with a number of copies.
        s.capture(s.digit(), s.letter())(3) # <== VALID
        ```

    Examples:
        ```
        # Matches any digit followed by a comma and period.
        captured_pattern = s.capture(s.digit(), ',.')
        ```

    Referencing:
        ```
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
        ```
    """

    clean_patterns = []
    for pattern in patterns:
        if isinstance(pattern, str):
            pattern = lit(pattern)

        if not isinstance(pattern, Pattern):
            message = """
            Method: simply.capture(*patterns)

            The parameters must be instances of `Pattern` or `str`.

            Use a string such as "123abc$" to match literal characters, or use a predefined set like `simply.letter()`.
            """
            raise STRlingError(message)

        clean_patterns.append(pattern)


    named_group_counts = {}
    for pattern in clean_patterns:
        for group_name in pattern.named_groups:
            if group_name in named_group_counts:
                named_group_counts[group_name] += 1
            else:
                named_group_counts[group_name] = 1

    duplicates = {name: count for name, count in named_group_counts.items() if count > 1}
    if duplicates:
        duplicate_info = ", ".join([f"{name}: {count}" for name, count in duplicates.items()])
        message = f"""
        Method: simply.capture(*patterns)

        Named groups must be unique.
        Duplicate named groups found: {duplicate_info}.

        If you need later reference change the named group argument to `simply.capture()`.
        If you don't need later reference change the named group argument to `simply.merge()`.
        """
        raise STRlingError(message)

    sub_names = named_group_counts.keys()

    joined = ''.join(str(p) for p in clean_patterns)
    new_pattern = f'({joined})'

    return Pattern(new_pattern, composite=True, numbered_group=True, named_groups=sub_names)

def group(name, *patterns):
    """
    Creates a unique named group that can be referenced for extracting this part of the match.

    Parameters:
    - name (str): The name of the capturing group.
    - *patterns (Pattern/str): One or more patterns to be captured.

    Returns:
    - An instance of the Pattern class.

    Ranges:
        ```
        # Groups CANNOT be invoked with a range.
        s.group('name', s.digit())(1, 2) # <== INVALID
        ```

    Examples:
        ```
        # Matches any digit followed by a comma and period.
        named_pattern = s.group('my_group', s.digit(), ',.')
        ```

    Referencing:
        ```
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
        ```
    """

    if not isinstance(name, str):
        message = """
        Method: simply.group(name, *patterns)

        The group is missing a specified name.
        The `name` parameter must be a string like 'group_name'.
        """
        raise STRlingError(message)


    clean_patterns = []
    for pattern in patterns:
        if isinstance(pattern, str):
            pattern = lit(pattern)

        if not isinstance(pattern, Pattern):
            message = """
            Method: simply.group(name, *patterns)

            The parameters must be instances of `Pattern` or `str`.

            Use a string such as "123abc$" to match literal characters, or use a predefined set like `simply.letter()`.
            """
            raise STRlingError(message)

        clean_patterns.append(pattern)


    named_group_counts = {}
    for pattern in clean_patterns:
        for group_name in pattern.named_groups:
            if group_name in named_group_counts:
                named_group_counts[group_name] += 1
            else:
                named_group_counts[group_name] = 1

    duplicates = {name: count for name, count in named_group_counts.items() if count > 1}
    if duplicates:
        duplicate_info = ", ".join([f"{name}: {count}" for name, count in duplicates.items()])
        message = f"""
        Method: simply.group(name, *patterns)

        Named groups must be unique.
        Duplicate named groups found: {duplicate_info}.

        If you need later reference change the named group argument to `simply.capture()`.
        If you don't need later reference change the named group argument to `simply.merge()`.
        """
        raise STRlingError(message)

    sub_names = named_group_counts.keys()

    joined = ''.join(str(p) for p in clean_patterns)
    new_pattern = f'(?P<{name}>{joined})'

    return Pattern(new_pattern, composite=True, named_groups=[name, *sub_names])
