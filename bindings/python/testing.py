from STRling import simply as s
import re
text = "A1B2C3D"

pattern1 = s.merge(s.letter(), s.digit())(1, 2)

results = re.findall(str(pattern1), text)
print(results) # ['A1B2', 'C3']
