from STRling import lib, group, merge, templates as tmp
import re

# # Sample string containing phone numbers
# text = """
#         The matches include:
#          - https://example.net
#          - https://mywebsite.dev/user2
#          - http://randomSite33.org/blogs/here
# """

# # Using the re package to search for the phone number pattern
# matches = re.finditer(tmp.url, text)

# # Displaying the matches
# count = 0
# for match in matches:
#     print('Index:', count)
#     print("Matched group:", match.group())
#     count += 1
