from STRling import simply as s
import textwrap

s.between(1, 'a')

class STRlingError(ValueError):
    def __init__(self, problem, solution):
        self.problem = textwrap.dedent(problem).strip().replace('\n', '\n\t\t')
        self.solution = textwrap.dedent(solution).strip().replace('\n', '\n\t\t')
        super().__init__(self.problem)

    def __str__(self):
        return f"\n\nSTRlingError: Invalid Pattern Detected.\n\n\tProblem:\n\t\t{self.problem}\n\n\tSolution:\n\t\t{self.solution}"



def check_pattern(pattern):

    if pattern == 1:
        problem = """
        Here is the problem.
    Here is the problem.
        """
        solution = """
        Here is the solution.
            Here is the solution.
        """
        raise STRlingError(problem, solution)
    if pattern == 0:
        if pattern == 0:
            if pattern == 0:
                problem = """
                Here is the problem.
            Here is the problem.
                """
                solution = """
                Here is the solution.
                    Here is the solution.
                """
                raise STRlingError(problem, solution)




def func1(p):
    func2(p)
def func2(p):
    func3(p)
def func3(p):
    check_pattern(p)

# func1(0)


# Traceback (most recent call last):
#   File "/home/tim3i/my-projects/STRling/testing.py", line 27, in <module>
#     func1(0)
#   File "/home/tim3i/my-projects/STRling/testing.py", line 21, in func1
#     func2(p)
#   File "/home/tim3i/my-projects/STRling/testing.py", line 23, in func2
#     func3(p)
#   File "/home/tim3i/my-projects/STRling/testing.py", line 25, in func3
#     check_pattern(p)
#   File "/home/tim3i/my-projects/STRling/testing.py", line 16, in check_pattern
#     raise STRlingError("The pattern provided is invalid.")
# __main__.STRlingError:

# STRlingError: Invalid Pattern Detected.

#         The pattern provided is invalid.

digit = s.group('digit', s.digit(1, 4))
letter = s.group('letter', s.letter())

alpha_num = s.group('alpha_num', digit, letter)

print(alpha_num.named_groups)

# print(digit.named_groups) # ['digit']
# print(letter.named_groups) # ['letter']
