# from .lib_v1 import group, merge
# from . import lib_v1

# class Templates:
#     @property
#     def phone_number_US(self):
#         """
#         The matched formats include:
#         - No Delimiters: 1234567890
#         - All Groups Separated:
#             - 123 456 7890
#             - 123-456-7890
#             - 123.456.7890
#         - Grouped Area Code:
#             - (123) 456 7890
#             - (123) 456-7890
#             - (123) 456.7890
#         - Matched Edge Cases:
#             - 123456-7890
#             - (123)-456 7890
#             - (123).456 7890
#         """
#         first = group('first', lib_v1.digit(3))
#         second = group('second', lib_v1.digit(3))
#         third = group('third', lib_v1.digit(4))

#         first_maybe_grouped = merge(lib_v1.may(lib_v1.lit('(')), first, lib_v1.may(lib_v1.lit(')')))

#         sep = lib_v1.in_chars(lib_v1.lit('. -'))
#         maybe_sep = lib_v1.may(sep)

#         main_number = merge(first_maybe_grouped, maybe_sep, second, maybe_sep, third)

#         no_nums_behind = lib_v1.not_behind(lib_v1.digit())
#         no_nums_ahead = lib_v1.not_ahead(lib_v1.digit())

#         phone_pattern = merge(no_nums_behind, main_number, no_nums_ahead)
#         return phone_pattern()

#     @property
#     def email(self):
#         """
#         The matches include:
#          - user123.name@subdomain.domain.org
#          - randomuser@temporarymail.net
#          - john.doe+spam@gmail.com
#          - webmaster@mywebsite.dev
#          - support@company.co.uk
#         """
#         first = group('first', lib_v1.in_chars(lib_v1.lower() + lib_v1.digit() + lib_v1.lit('_.+-'), 1, ''))
#         second = group('second', lib_v1.in_chars(lib_v1.lower() + lib_v1.digit() + lib_v1.lit('.-'), 1, ''))
#         third = group('third', lib_v1.in_chars(lib_v1.lower(), 2, ''))

#         email_pattern = merge(first, lib_v1.lit('@'), second, lib_v1.lit('.'), third)
#         return email_pattern()

#     @property
#     def url(self):
#         """
#         The matches include:
#          - https://example.net
#          - https://mywebsite.dev/user2
#          - http://randomSite33.org/blogs/here
#         """
#         alpha_num = lib_v1.letter() + lib_v1.digit()

#         first = lib_v1.may(lib_v1.lit('http') + lib_v1.may(lib_v1.lit('s')) + lib_v1.lit('://'))

#         second = lib_v1.in_chars(alpha_num  + lib_v1.lit('-.'), 1, '') + lib_v1.lit('.') + lib_v1.letter(2,'')

#         third = merge(lib_v1.in_chars(alpha_num + lib_v1.lit('./-')))(0,'')

#         url_pattern = merge(first, second, third)
#         return url_pattern()


# template = Templates()
