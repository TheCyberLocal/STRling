from STRling import lib, group, merge
import re

first = group('first', lib.digit(3)) #
second = group('second', lib.digit(3)) #
third = group('third', lib.digit(4)) #
h = lib.lit('-')

phone_pattern = lib.group('phone', first + h + second + h + third)

# Sample string containing phone numbers
text = "Here are some phone numbers: 987-654-3210, 123-456-7890."

# Using the re package to search for the phone number pattern
matches = re.finditer(phone_pattern, text)

# Displaying the matches
for match in matches:
    print('Match Index Range:', match.span())
    print('"first" group:', match.group('first'))
    print('"second" group:', match.group('second'))
    print('"third" group:', match.group('third'))
    print('"phone" group:', match.group('phone'))

# Match Index Range: (29, 41)
# "first" group: 987
# "second" group: 654
# "third" group: 3210
# "phone" group: 987-654-3210

# Match Index Range: (43, 55)
# "first" group: 123
# "second" group: 456
# "third" group: 7890
# "phone" group: 123-456-7890
