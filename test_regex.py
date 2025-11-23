import re

s = 'const [, ast] = parse("a{,5}");'
regex = r'parse\s*\(\s*(?:String\.raw)?(`|"|\')(.*?)\1'
m = re.search(regex, s)
if m:
    print(f"Match: {m.groups()}")
else:
    print("No match")
