from STRling import lib, group, merge, templates as tmp
import re

# Sample string containing phone numbers
text = """
ars
tim.3imt@gmail.com
nst
"""

# Using the re package to search for the phone number pattern
print(tmp.email)
matches = re.finditer(tmp.email, text)

# Displaying the matches
count = 0
for match in matches:
    print('Index:', count)
    print("Matched group:", match.group())
    count += 1
    print()
