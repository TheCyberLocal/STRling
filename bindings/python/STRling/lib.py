import re

####################################################
##  This is just the setup and helpers functions  ##
##  Scroll further down to see the user tools     ##
####################################################

# Range syntax
def repeat(min=None, max=None):
    """
    Create a repetition pattern for the preceding symbol.

    Args:
        min (int, optional): Minimum number of repetitions. Defaults to None.
                             When only `min` is specified, it means an exact count.
        max (int, str, optional): Maximum number of repetitions. Can be an empty string
                                  for open-ended repetition. Defaults to None.
                                  When both `min` and `max` are specified, it represents
                                  the range {min, max}.

    Returns:
        str: A string representing the repetition pattern.

    RegEx: {min,max}
    """
    if min is not None and max is not None:
        if max == '':  # Special case to handle the 'min,' syntax
            return f'{{{min},}}'
        if min > max:
            raise ValueError('min cannot be greater than max')
        return f'{{{min},{max}}}'
    elif min is not None:
        return f'{{{min}}}'
    return ''


# Pattern class
class Pattern:
    """
    A class representing a regex pattern.

    Methods:
        __call__(self, min=None, max=None): Adds repetition to the pattern before
                                            returning the pattern as a string.
        __str__(self): Returns the pattern as a string.
    """
    def __init__(self, pattern):
        self.pattern = pattern

    def __call__(self, min=None, max=None):
        """
        Adds repetition to the pattern.

        Args:
            min (int, optional): Minimum number of repetitions. Defaults to None.
                                 When only `min` is specified, it means an exact count.
            max (int, str, optional): Maximum number of repetitions. Can be an empty string
                                      for open-ended repetition. Defaults to None.
                                      When both `min` and `max` are specified, it represents
                                      the range {min, max}.

        Returns:
            str: The pattern with the repetition added.
        """
        return self.pattern + repeat(min, max)

    def __str__(self):
        """
        Returns the pattern as a string.

        Returns:
            str: The pattern string.
        """
        return self.pattern


# Decorators
def repeat_on_invoke(func, *args):
    """
    Decorator to apply repetition to specific pattern functions.

    Args:
        func (function): The function to decorate.
        *args: Positional arguments for the function.

    Returns:
        Pattern: A Pattern object with the specified repetition.
    """
    pattern = func(*args)
    return Pattern(pattern)


###############################################
##   All functions below are for the user    ##
###############################################

# Symbols with positional arguments
def lit(text, min=None, max=None):
    """
    No magic tricks here! Just match exactly what I type!

    Match the literal string `text`.

    Args:
        text (str): The literal string to match.
        min (int, optional): Minimum number of repetitions. Defaults to None.
                             When only `min` is specified, it means an exact count.
        max (int, str, optional): Maximum number of repetitions. Can be an empty string
                                  for open-ended repetition. Defaults to None.
                                  When both `min` and `max` are specified, it represents
                                  the range {min, max}.

    Returns:
        str: The escaped literal string with repetition if specified.

    RegEx: escaped\-text{min,max}
    """
    regular_text = text.encode("unicode_escape").decode("utf-8")
    return re.escape(regular_text).replace(' ', 's') + repeat(min, max)

def between(start_char=None, end_char=None, min=None, max=None):
    """
    I'm not a typist! Just match any letters or
    numbers between the start and end character.

    Match any character between `start_char` and `end_char`.

    Args:
        start_char (str): The starting character of the range.
        end_char (str): The ending character of the range.
        min (int, optional): Minimum number of repetitions. Defaults to None.
                             When only `min` is specified, it means an exact count.
        max (int, str, optional): Maximum number of repetitions. Can be an empty string
                                  for open-ended repetition. Defaults to None.
                                  When both `min` and `max` are specified, it represents
                                  the range {min, max}.

    Returns:
        str: The character range with repetition if specified.

    RegEx: [start_char-end_char]
    """
    return f'[{start_char}-{end_char}]' + repeat(min, max)

def in_(chars=None, min=None, max=None):
    """
    I've got a VIP list. Make sure the character here is on it!

    Match any character in `chars`.

    Args:
        chars (str): A string of characters to match.
        min (int, optional): Minimum number of repetitions. Defaults to None.
                             When only `min` is specified, it means an exact count.
        max (int, str, optional): Maximum number of repetitions. Can be an empty string
                                  for open-ended repetition. Defaults to None.
                                  When both `min` and `max` are specified, it represents
                                  the range {min, max}.

    Returns:
        str: The character class with repetition if specified.

    RegEx: [chars]
    """
    # When taking user input into a character set
    # ensure that any sets are flattened
    # When taking user input into a character set
    # ensure that any sets are flattened
    clean_chars = re.sub(r'(?<!\\)[\[\]]', '', chars)
    return f'[{clean_chars}]' + repeat(min, max)

def not_in(chars=None, min=None, max=None):
    """
    I've got a blacklist. Any character can
    go here, except the ones on this list!

    Match any character not in `chars`.

    Args:
        chars (str): A string of characters to exclude.
        min (int, optional): Minimum number of repetitions. Defaults to None.
                             When only `min` is specified, it means an exact count.
        max (int, str, optional): Maximum number of repetitions. Can be an empty string
                                  for open-ended repetition. Defaults to None.
                                  When both `min` and `max` are specified, it represents
                                  the range {min, max}.

    Returns:
        str: The negated character class with repetition if specified.

    RegEx: [^chars]
    """
    # When taking user input into a character set
    # ensure that any sets are flattened
    clean_chars = re.sub(r'(?<!\\)[\[\]]', '', chars)
    return f'[^{clean_chars}]' + repeat(min, max)


# Symbols without positional arguments
@repeat_on_invoke
def digit():
    """
    I'm counting on you to match a number here!

    Match any digit.

    Returns:
        str: The digit character class.

    RegEx: \d
    """
    return r'\d'

@repeat_on_invoke
def letter():
    """
    This letter spot is family friendly.
    Big and small letters will do.

    Match any letter.

    Returns:
        str: The letter character class.

    RegEx: r'[A-Za-z]'
    """
    return r'[A-Za-z]'

@repeat_on_invoke
def upper():
    """
    No little letters in the
    office. Adults only please.

    Match any uppercase letter.

    Returns:
        str: The uppercase letter character class.

    RegEx: [A-Z]
    """
    return r'[A-Z]'

@repeat_on_invoke
def lower():
    """
    No adults here. Only little letters
    are allowed on the playground.

    Match any lowercase letter.

    Returns:
        str: The lowercase letter character class.

    RegEx: [a-z]
    """
    return r'[a-z]'

@repeat_on_invoke
def space():
    """
    PLEASE... just give me some (  space  ).

    Match any whitespace character.

    Returns:
        str: The whitespace character class.

    RegEx: \s
    """
    return r'\s'

@repeat_on_invoke
def any():
    """
    I'm not picky. Any letter will do,
    just not those pesky newlines.

    Match any character except newline.

    Returns:
        str: The any character dot.

    RegEx: .
    """
    return r'.'


# Whitespace characters
@repeat_on_invoke
def newline():
    """
    Let's take it to the next line.

    Match a newline character.

    Returns:
        str: The newline character.

    RegEx: \n
    """
    return r'\n'

@repeat_on_invoke
def tab():
    """
    There should be a tab here.

    Match a tab character.

    Returns:
        str: The tab character.

    RegEx: \t
    """
    return r'\t'

@repeat_on_invoke
def carriage():
    """
    There should be a carriage return here.

    Match a carriage return character.

    Returns:
        str: The carriage return character.

    RegEx: \r
    """
    return r'\r'

@repeat_on_invoke
def bound():
    """
    That's it! I'm setting up some boundaries!

    Match a word boundary.

    Returns:
        str: The word boundary character.

    RegEx: \b
    """
    return r'\b'



# Anchors
def start():
    """
    Stop! Behind the line please.
    I haven't even said go.

    Match the start of the string.

    Returns:
        str: The start of a line pattern.

    RegEx: ^
    """
    return r'^'

def end():
    """
    Finally..., just how far did you
    have to make the finish line.

    Match the end of the string.

    Returns:
        str: The end of a line pattern.

    RegEx: $
    """
    return r'$'


# Lookarounds
def ahead(pattern):
    """
    I've got my eyes on the prize.
    Only match if this pattern is up ahead!

    Match if the pattern matches ahead.

    Args:
        pattern (str): The pattern to look ahead for.

    Returns:
        str: The positive lookahead pattern.

    RegEx: (?=pattern)
    """
    return f'(?={pattern})'

def behind(pattern):
    """
    Don't forget to check your rear-view mirror!
    Only match if this pattern is behind.

    Match if the pattern matches behind.

    Args:
        pattern (str): The pattern to look behind for.

    Returns:
        str: The positive lookbehind pattern.

    RegEx: (?<=pattern)
    """
    return f'(?<={pattern})'

def not_ahead(pattern):
    """
    Keep moving forward! Just be careful of cliffs,
    only match if this pattern is NOT up ahead.

    Match if the pattern does not match ahead.

    Args:
        pattern (str): The pattern to look ahead for.

    Returns:
        str: The negative lookahead pattern.

    RegEx: (?!pattern)
    """
    return f'(?!{pattern})'

def not_behind(pattern):
    """
    If you see this bear pattern... RUN!
    No matches, just get out of there.

    Match if the pattern does not match behind.

    Args:
        pattern (str): The pattern to look behind for.

    Returns:
        str: The negative lookbehind pattern.

    RegEx: (?<!pattern)
    """
    return f'(?<!{pattern})'


# Conditionals
def or_(*patterns):
    """
    I'm easy to please.
    Any of these patterns will do!

    Match any of the given patterns.

    Args:
        patterns (str): The patterns to match.

    Returns:
        Pattern: A Pattern object that will match any patterns provided.

    RegEx: (?:pattern1|pattern2|pattern3|...)
    """
    joined = '|'.join(f'(?:{p})' for p in patterns)
    return Pattern(f'(?:{joined})')

def may(*patterns):
    """
    To be or not to be, that is the question.
    This pattern may or may not be here.

    Match zero or one occurrence of the pattern.

    Args:
        pattern (str): The pattern to match.

    Returns:
        str: The optional pattern.

    RegEx: (?:pattern)?
    """
    joined = merge(*patterns)
    return f'{joined}?'


# Grouping
def merge(*patterns):
    """
    We may not have a team name,
    but we always work together.

    Create a non-capturing group with the given patterns.
    A non-capturing group can't be extracted from a match.

    While addition syntax seems to have the same effect,
    patterns don't truly become one unless they are merged.

    Args:
        patterns (str): The patterns to include in the group.

    Returns:
        Pattern: A Pattern object for the non-capturing group.

    RegEx: (?: pattern1 pattern2 pattern3...)
    """
    joined = ''.join(str(p) for p in patterns)
    return Pattern(f'(?:{joined})')

def capture(*patterns):
    """
    We may not have a team name,
    but at least we COUNT.

    Create a numbered capturing group with the given patterns.
    A capturing group can be extracted from a match.

    While addition syntax seems to have the same effect,
    captured patterns can be indexed from the match later.

    Args:
        patterns (str): The patterns to include in the group.

    Returns:
        Pattern: A Pattern object for the capturing group.

    RegEx: (pattern1 pattern2 pattern3...)
    """
    joined = ''.join(str(p) for p in patterns)
    return Pattern(f'({joined})')

def group(name, *patterns):
    """
    These patterns are now a team, and I want to name them
    so I can easily extract this part of the match later.

    Create a named capture group with the given patterns.
    A capture group can easily be extracted from a match.

    Args:
        name (str): The name of the capture group.
        patterns (str): The patterns to include in the group.

    Returns:
        str: The named capture group pattern.

    RegEx: (?P<name> pattern1 pattern2 pattern3...)
    """
    joined = ''.join(str(p) for p in patterns)
    return f'(?P<{name}>{joined})'
