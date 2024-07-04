
import { STRlingError, Pattern, lit } from './pattern';


// Constructor Methods


function anyOf(...patterns) {
    // Check all patterns are instance of Pattern or str
    const cleanPatterns = []
    for (let pattern in patterns) {
        if (pattern instanceof str) {
            pattern = lit(pattern)
        }

        if (!(pattern instanceof Pattern)) {
            const message = ```
            Method: simply.anyOf(...patterns)

            The parameters must be instances of 'Pattern' or 'str'.

            Use a string such as "123abc$" to match literal characters, or use a predefined set like 'simply.letter()'.
            ```
            throw STRlingError(message)
        }

        cleanPatterns.append(pattern)
    }

    // Count named groups and raise error if not unique
    const named_group_counts = {}

    for (const pattern in cleanPatterns) {
        for (const groupName in pattern.namedGroups) {
            if (groupName in named_group_counts) {
                named_group_counts[groupName] += 1
            } else {
                named_group_counts[groupName] = 1
            }
        }
    }

    duplicates = {}
    for (const key in duplicates) {
        if (named_group_counts[key] > 1) {
            duplicates[key] = (duplicates[key] ?? 0) + 1
        }
    }

    if (duplicates) {
        const duplicate_info = ", ".join(
            duplicates.items().map(groupName, count => `${groupName}: ${count}`)
        );

        message = ```
        Method: simply.anyOf(...patterns)

        Named groups must be unique.
        Duplicate named groups found: ${duplicate_info}.

        If you need later reference change the named group argument to 'simply.capture()'.
        If you don't need later reference change the named group argument to 'simply.merge()'.
        ```
        throw STRlingError(message)
    }

    sub_names = Object.keys(named_group_counts)

    let cleanPatternStrings = cleanPatterns.map(e => e.toString());
    cleanPatternStrings
    joined = cleanPatternStrings.join('|');
    new_pattern = `?:${joined})`

    return Pattern(new_pattern, composite=true, namedGroups=sub_names)
}


// def may(...patterns):
//     ```
//     Optionally matches the provided patterns. If this pattern is absent, surrounding patterns can still match.

//     Example: simply as s
//         - Matches any letter, along with any trailing digit.

//         pattern = s.merge(s.letter(), s.may(s.digit()))

//         In the text, "AB2" the pattern above matches 'A' and 'B2'.

//     Parameters:
//     - ...patterns (Pattern/str): One or more patterns to be optionally matched.

//     Returns:
//     - Pattern: A Pattern object representing the optional match of the given patterns.
//     ```

//     // Check all patterns are instance of Pattern or str
//     cleanPatterns = []
//     for pattern in patterns:
//         if isinstance(pattern, str):
//             pattern = lit(pattern)

//         if not isinstance(pattern, Pattern):
//             message = ```
//             Method: simply.may(...patterns)

//             The parameters must be instances of 'Pattern' or 'str'.

//             Use a string such as "123abc$" to match literal characters, or use a predefined set like 'simply.letter()'.
//             ```
//             throw STRlingError(message)

//         cleanPatterns.append(pattern)


//     // Count named groups and raise error if not unique
//     named_group_counts = {}

//     for pattern in cleanPatterns:
//         for groupName in pattern.namedGroups:
//             if groupName in named_group_counts:
//                 named_group_counts[groupName] += 1
//             else:
//                 named_group_counts[groupName] = 1

//     duplicates = {name: count for name, count in named_group_counts.items() if count > 1}
//     if duplicates:
//         duplicate_info = ", ".join([f"{name}: {count}" for name, count in duplicates.items()])
//         message = ```
//         Method: simply.may(...patterns)

//         Named groups must be unique.
//         Duplicate named groups found: {duplicate_info}.

//         If you need later reference change the named group argument to 'simply.capture()'.
//         If you don't need later reference change the named group argument to 'simply.merge()'.
//         ```
//         throw STRlingError(message)

//     sub_names = named_group_counts.keys()

//     joined = merge(...cleanPatterns)
//     new_pattern = f'{joined}?'

//     return Pattern(new_pattern, composite=true, namedGroups=sub_names)



// def merge(...patterns):
//     ```
//     Combines the provided patterns into one larger pattern.

//     Example: simply as s
//         - Matches any digit, comma, or period.

//         merged_pattern = s.merge(s.digit(), ',.')

//     Parameters:
//     - ...patterns (Pattern/str): One or more patterns to be concatenated.

//     Returns:
//     - Pattern: A Pattern object representing the concatenation of the given patterns.
//     ```

//     // Check all patterns are instance of Pattern or str
//     cleanPatterns = []
//     for pattern in patterns:
//         if isinstance(pattern, str):
//             pattern = lit(pattern)

//         if not isinstance(pattern, Pattern):
//             message = ```
//             Method: simply.merge(...patterns)

//             The parameters must be instances of 'Pattern' or 'str'.

//             Use a string such as "123abc$" to match literal characters, or use a predefined set like 'simply.letter()'.
//             ```
//             throw STRlingError(message)

//         cleanPatterns.append(pattern)


//     // Count named groups and raise error if not unique
//     named_group_counts = {}

//     for pattern in cleanPatterns:
//         for groupName in pattern.namedGroups:
//             if groupName in named_group_counts:
//                 named_group_counts[groupName] += 1
//             else:
//                 named_group_counts[groupName] = 1

//     duplicates = {name: count for name, count in named_group_counts.items() if count > 1}
//     if duplicates:
//         duplicate_info = ", ".join([f"{name}: {count}" for name, count in duplicates.items()])
//         message = ```
//         Method: simply.merge(...patterns)

//         Named groups must be unique.
//         Duplicate named groups found: {duplicate_info}.

//         If you need later reference change the named group argument to 'simply.capture()'.
//         If you don't need later reference change the named group argument to 'simply.merge()'.
//         ```
//         throw STRlingError(message)

//     sub_names = named_group_counts.keys()

//     joined = ''.join(str(p) for p in cleanPatterns)
//     new_pattern = f'(?:{joined})'

//     return Pattern(new_pattern, composite=true, namedGroups=sub_names)

// def capture(...patterns):
//     ```
//     Creates a numbered group that can be indexed for extracting this part of the match.

//     - Captures CANNOT be invoked with a range.

//     s.capture(s.digit(), s.letter())(1, 2) <== INVALID

//     - Captures CAN be invoked with a number of copies.

//     s.capture(s.digit(), s.letter())(3) <== VALID

//     Example: simply as s
//         - Matches any digit, comma, or period.

//         captured_pattern = s.capture(s.digit(), ',.')


//     Parameters:
//     - ...patterns (Pattern/str): One or more patterns to be captured.

//     Returns:
//     - Pattern: A Pattern object representing the capturing group of the given patterns.

//     Referencing: simply as s
//         three_digit_group = s.capture(s.digit(3))

//         four_groups_of_three = three_digit_groups(4)

//         example_text = "Here is a number: 111222333444"

//         match = re.search(str(four_groups_of_three), example_text)  // Notice str(pattern)

//         console.log("Full Match:", match.group())
//         console.log("First:", match.group(1))
//         console.log("Second:", match.group(2))
//         console.log("Third:", match.group(3))
//         console.log("Fourth:", match.group(4))

//         // Output:
//         // Full Match: 111222333444
//         // First: 111
//         // Second: 222
//         // Third: 333
//         // Fourth: 444
//     ```

//     // Check all patterns are instance of Pattern or str
//     cleanPatterns = []
//     for pattern in patterns:
//         if isinstance(pattern, str):
//             pattern = lit(pattern)

//         if not isinstance(pattern, Pattern):
//             message = ```
//             Method: simply.capture(...patterns)

//             The parameters must be instances of 'Pattern' or 'str'.

//             Use a string such as "123abc$" to match literal characters, or use a predefined set like 'simply.letter()'.
//             ```
//             throw STRlingError(message)

//         cleanPatterns.append(pattern)


//     // Count named groups and raise error if not unique
//     named_group_counts = {}

//     for pattern in cleanPatterns:
//         for groupName in pattern.namedGroups:
//             if groupName in named_group_counts:
//                 named_group_counts[groupName] += 1
//             else:
//                 named_group_counts[groupName] = 1

//     duplicates = {name: count for name, count in named_group_counts.items() if count > 1}
//     if duplicates:
//         duplicate_info = ", ".join([f"{name}: {count}" for name, count in duplicates.items()])
//         message = ```
//         Method: simply.capture(...patterns)

//         Named groups must be unique.
//         Duplicate named groups found: {duplicate_info}.

//         If you need later reference change the named group argument to 'simply.capture()'.
//         If you don't need later reference change the named group argument to 'simply.merge()'.
//         ```
//         throw STRlingError(message)

//     sub_names = named_group_counts.keys()

//     joined = ''.join(str(p) for p in cleanPatterns)
//     new_pattern = f'({joined})'

//     return Pattern(new_pattern, composite=true, numbered_group=true, namedGroups=sub_names)

// def group(name, ...patterns):
//     ```
//     Creates a unique named group that can be referenced for extracting this part of the match.

//     - Groups CANNOT be invoked with a range.

//     s.group('name', s.digit())(1, 2) <== INVALID

//     Example: simply as s
//         - Matches any digit followed by a comma and period.

//         named_pattern = s.group('my_group', s.digit(), ',.')

//     Parameters:
//     - name (str): The name of the capturing group.
//     - ...patterns (Pattern/str): One or more patterns to be captured.

//     Returns:
//     - Pattern: A Pattern object representing the named capturing group of the given patterns.

//     Referencing: simply as s
//         first = s.group("first", s.digit(3))

//         second = s.group("second", s.digit(3))

//         third = s.group("third", s.digit(4))

//         phone_number_pattern = s.merge(first, "-", second, "-", third)

//         example_text = "Here is a phone number: 123-456-7890."

//         match = re.search(str(phone_number_pattern), example_text) // Notice str(pattern)

//         console.log("Full Match:", match.group())
//         console.log("First:", match.group("first"))
//         console.log("Second:", match.group("second"))
//         console.log("Third:", match.group("third"))

//         // Output:
//         // Full Match: 123-456-7890
//         // First: 123
//         // Second: 456
//         // Third: 7890
//     ```

//     if not isinstance(name, str):
//         message = ```
//         Method: simply.group(name, ...patterns)

//         The group is missing a specified name.
//         The 'name' parameter must be a string like 'groupName'.
//         ```
//         throw STRlingError(message)


//     // Check all patterns are instance of Pattern or str
//     cleanPatterns = []
//     for pattern in patterns:
//         if isinstance(pattern, str):
//             pattern = lit(pattern)

//         if not isinstance(pattern, Pattern):
//             message = ```
//             Method: simply.group(name, ...patterns)

//             The parameters must be instances of 'Pattern' or 'str'.

//             Use a string such as "123abc$" to match literal characters, or use a predefined set like 'simply.letter()'.
//             ```
//             throw STRlingError(message)

//         cleanPatterns.append(pattern)


//     // Count named groups and raise error if not unique
//     named_group_counts = {}

//     for pattern in cleanPatterns:
//         for groupName in pattern.namedGroups:
//             if groupName in named_group_counts:
//                 named_group_counts[groupName] += 1
//             else:
//                 named_group_counts[groupName] = 1

//     duplicates = {name: count for name, count in named_group_counts.items() if count > 1}
//     if duplicates:
//         duplicate_info = ", ".join([f"{name}: {count}" for name, count in duplicates.items()])
//         message = ```
//         Method: simply.group(name, ...patterns)

//         Named groups must be unique.
//         Duplicate named groups found: {duplicate_info}.

//         If you need later reference change the named group argument to 'simply.capture()'.
//         If you don't need later reference change the named group argument to 'simply.merge()'.
//         ```
//         throw STRlingError(message)

//     sub_names = named_group_counts.keys()

//     joined = ''.join(str(p) for p in cleanPatterns)
//     new_pattern = f'(?P<{name}>{joined})'

//     return Pattern(new_pattern, composite=true, namedGroups=[name, ...sub_names])
