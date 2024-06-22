from .lib import group, merge
from . import lib

class Templates:
    @property
    def phone_number_US(self):
        """
        The matched formats include:
        - No Delimiters: 1234567890
        - All Groups Separated:
            - 123 456 7890
            - 123-456-7890
            - 123.456.7890
        - Grouped Area Code:
            - (123) 456 7890
            - (123) 456-7890
            - (123) 456.7890
        - Matched Edge Cases:
            - 123456-7890
            - (123)-456 7890
            - (123).456 7890
        """
        first = group('first', lib.digit(3))
        second = group('second', lib.digit(3))
        third = group('third', lib.digit(4))

        first_maybe_grouped = merge(lib.may(lib.lit('(')), first, lib.may(lib.lit(')')))

        sep = lib.in_(lib.lit('. -'))
        maybe_sep = lib.may(sep)

        main_number = merge(first_maybe_grouped, maybe_sep, second, maybe_sep, third)

        no_nums_behind = lib.not_behind(lib.digit())
        no_nums_ahead = lib.not_ahead(lib.digit())

        phone_pattern = merge(no_nums_behind, main_number, no_nums_ahead)
        return phone_pattern()

    @property
    def email(self):
        """
        The matches include:
         - user123.name@subdomain.domain.org
         - randomuser@temporarymail.net
         - john.doe+spam@gmail.com
         - webmaster@mywebsite.dev
         - support@company.co.uk
        """
        first = group('first', lib.in_(lib.lower() + lib.digit() + lib.lit('_.+-'), 1, ''))
        second = group('second', lib.in_(lib.lower() + lib.digit() + lib.lit('.-'), 1, ''))
        third = group('third', lib.in_(lib.lower(), 2, ''))

        email_pattern = merge(first, lib.lit('@'), second, lib.lit('.'), third)
        return email_pattern()

    @property
    def url(self):
        """
        The matches include:
         - https://example.net
         - https://mywebsite.dev/user2
         - http://randomSite33.org/blogs/here
        """
        alpha_num = lib.letter() + lib.digit()

        first = lib.may(lib.lit('http') + lib.may(lib.lit('s')) + lib.lit('://'))

        second = lib.in_(alpha_num  + lib.lit('-.'), 1, '') + lib.lit('.') + lib.letter(2,'')

        third = merge(lib.in_(alpha_num + lib.lit('./-')))(0,'')

        url_pattern = merge(first, second, third)
        return url_pattern()


template = Templates()
