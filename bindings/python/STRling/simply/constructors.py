
from .pattern import Pattern


############################
# Constructor Methods
########



def or_(*patterns):
    if not all(isinstance(pattern, Pattern) for pattern in patterns):
        msg = (
        """
        Problem:
            Not all the parameters are an instance of Pattern.

        Solution:
            Use `simply.lit('abc123$')` to match literal characters,
            or use a predefined set like `simply.letters()`.
        """)
        raise ValueError(msg)
    joined = '|'.join(f'(?:{str(p)})' for p in patterns)
    return Pattern(f'(?:{joined})')

def may(*patterns):
    if not all(isinstance(pattern, Pattern) for pattern in patterns):
        msg = (
        """
        Problem:
            Not all the parameters are an instance of Pattern.

        Solution:
            Use `simply.lit('abc123$')` to match literal characters,
            or use a predefined set like `simply.letters()`.
        """)
        raise ValueError(msg)

    if len(patterns) == 1:
        return Pattern(f'{patterns[0]}?')

    joined = merge(*patterns)
    return Pattern(f'{joined}?', composite=True)



def merge(*patterns):
    if not all(isinstance(pattern, Pattern) for pattern in patterns):
        msg = (
        """
        Problem:
            Not all the parameters are an instance of Pattern.

        Solution:
            Use `simply.lit('abc123$')` to match literal characters,
            or use a predefined set like `simply.letters()`.
        """)
        raise ValueError(msg)
    joined = ''.join(str(p) for p in patterns)
    new_pattern = f'(?:{joined})'
    return Pattern(new_pattern, composite=True)

def capture(*patterns):
    if not all(isinstance(pattern, Pattern) for pattern in patterns):
        msg = (
        """
        Problem:
            Not all the parameters are an instance of Pattern.

        Solution:
            Use `simply.lit('abc123$')` to match literal characters,
            or use a predefined set like `simply.letters()`.
        """)
        raise ValueError(msg)

    joined = ''.join(str(p) for p in patterns)
    return Pattern(f'({joined})', composite=True)

def group(name, *patterns):
    if not all(isinstance(pattern, Pattern) for pattern in patterns):
        msg = (
        """
        Problem:
            Not all the parameters are an instance of Pattern.

        Solution:
            Use `simply.lit('abc123$')` to match literal characters,
            or use a predefined set like `simply.letters()`.
        """)
        raise ValueError(msg)

    joined = ''.join(str(p) for p in patterns)
    return Pattern(f'(?P<{name}>{joined})', composite=True, repeatable=False)
