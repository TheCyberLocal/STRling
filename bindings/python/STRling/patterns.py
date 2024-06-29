from STRling import simply as s

class Patterns:
    @property
    def phone_number_US(self):
        """
        Returns a pattern for matching US phone numbers.

        Primary match examples:
        - (123) 456-7890
        - 123-456-7890
        - 123 456 7890
        - 123.456.7890

        Edge-cases to consider:
        - (123-456.7890
        - 123).456 7890
        - (123 456-7890

        Named groups:
        - 'first': The first set of 3 digits.
        - 'second': The second set of 3 digits.
        - 'third': The last set of 4 digits.

        Returns:
        - Pattern: A Pattern object for matching US phone numbers.
        """
        first = s.group('first', s.digit(3))
        second = s.group('second', s.digit(3))
        third = s.group('third', s.digit(4))
        first_sect = s.merge(s.may('('), first, s.may(')'))
        sep = s.in_chars('-. ')
        phone_number = s.merge(first_sect, sep, second, sep, third)
        phone_number_pattern = s.merge(s.not_behind(s.digit()), phone_number, s.not_ahead(s.digit()))
        return phone_number_pattern

    @property
    def ipv4(self):
        """
        Returns a pattern for matching IPv4 addresses.

        Primary match examples:
        - 192.168.1.1
        - 10.0.0.1
        - 172.16.254.1
        - 255.255.255.255
        - 0.0.0.0

        Edge-cases to consider:
        - 999.999.999.999
        - 256.256.256.256
        - 192.168.1.256

        Captured groups:
        - Numbered 1 to 4 for each octet.

        Returns:
        - Pattern: A Pattern object for matching IPv4 addresses.
        """
        ipv4_pattern = s.capture(
            s.digit(1, 3), '.',
            s.digit(1, 3), '.',
            s.digit(1, 3), '.',
            s.digit(1, 3)
        )
        return ipv4_pattern

patterns = Patterns()
