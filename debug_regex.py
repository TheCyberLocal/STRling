import re

strings = [
    'const [, ast] = parse("a{,5}");',
    'const [, ast] = parse("(?:)*");',
    'const [, ast] = parse("ab*");',
]

regex = r'parse\s*\(\s*(?:String\.raw)?(`|"|\')(.*?)\1'

for s in strings:
    print(f"Testing: {s}")
    m = re.search(regex, s)
    if m:
        print(f"Match: {m.groups()}")
    else:
        print("No match")
