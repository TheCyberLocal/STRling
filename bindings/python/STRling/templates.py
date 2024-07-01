from STRling import simply as s

class Templates:
    @property
    def phone_number_US(self):
        """
        Returns a pattern for matching US phone numbers.

        Primary match examples:
        - (123) 456-7890
        - 123-456-7890
        - 123 456 7890
        - 123.456.7890

        Matched edge-cases to consider:
        - (123-456.7890
        - 123).456 7890
        - (123 456-7890

        Named groups: first, second, third.
        - <first>.<second>.<third>

        Returns:
        - Pattern: A Pattern object for matching US phone numbers.
        """

        first = s.group('first', s.digit(3))
        second = s.group('second', s.digit(3))
        third = s.group('third', s.digit(4))

        first_sect = s.merge(s.may('('), first, s.may(')'))

        sep = s.in_chars('-. ')

        phone_number_pattern = s.merge(first_sect, sep, second, sep, third)
        return phone_number_pattern

    @property
    def email(self):
        """
        Returns a pattern for matching email addresses.

        Primary match examples:
        - user@example.com
        - user.name+tag+sorting@example.com
        - user@sub.example.co.uk

        Matched edge-cases to consider:
        - user@user.user
        - 1@2.3
        - !@!.!

        Named groups: local, domain, tld.
        - <local>@<domain>.<tld>

        Returns:
        - Pattern: A Pattern object for matching email addresses.
        """
        email_chars = s.in_chars(s.letter(), s.digit(), '.!#$%&\'*+/=?^_`{|}~-')
        local = s.group('local', email_chars(1, 0))
        domain = s.group('domain', email_chars(1, 0))
        tld = s.group('tld', email_chars(1, 0))
        email_pattern = s.merge(local, '@', domain, '.', tld)
        return email_pattern

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

        Matched edge-cases to consider:
        - 999.999.999.999
        - 100.200.300.400
        - 00.00.00.00

        Captured groups:
        - Numbered 1 to 4 for each octet.

        Returns:
        - Pattern: A Pattern object for matching IPv4 addresses.
        """
        ipv4_pattern = s.merge(
            s.capture(s.digit(1, 3)), '.',
            s.capture(s.digit(1, 3)), '.',
            s.capture(s.digit(1, 3)), '.',
            s.capture(s.digit(1, 3))
        )
        return ipv4_pattern

    @property
    def ipv6(self):
        """
        Returns a pattern for matching IPv6 addresses.

        Primary match examples:
        - 2001:0db8:85a3:0000:0000:8a2e:0370:7334
        - 20:b8:85a3:0:0:9:a:b

        Matched edge-cases to consider:
        - A:b:C:d:e:F:0:aAbB

        Captured groups:
        - Numbered 1 to 4 for each hextet.

        Returns:
        - Pattern: A Pattern object for matching IPv6 addresses.
        """
        hex_segment = s.hex_digit(1, 4)
        ipv6_pattern = s.merge(
            s.capture(hex_segment), ':',
            s.capture(hex_segment), ':',
            s.capture(hex_segment), ':',
            s.capture(hex_segment), ':',
            s.capture(hex_segment), ':',
            s.capture(hex_segment), ':',
            s.capture(hex_segment)
        )
        return ipv6_pattern

    @property
    def date_yyyy_mm_dd(self):
        """
        Returns a pattern for matching dates in the format YYYY-MM-DD.

        Primary match examples:
        - 2024-06-30
        - 1999/12/31
        - 1999.12.31

        Matched edge-cases to consider:
        - 2024/06.30
        - 2024.06-30
        - 99.12/31

        Named groups: year, month, day.
        - <year>-<month>-<day>

        Returns:
        - Pattern: A Pattern object for matching dates in the format YYYY-MM-DD.
        """
        sep = s.in_chars('-./')
        date_pattern = s.merge(
            s.group('year', s.digit(4)), sep,
            s.group('month', s.digit(2)), sep,
            s.group('day', s.digit(2))
        )
        return date_pattern

    @property
    def time_hh_mm(self):
        """
        Returns a pattern for matching times in the format HH:MM(am or pm).

        Primary match examples:
        - 2:00pm
        - 11:59am

        Matched edge-cases to consider:
        - 24:00pm
        - 99:99am
        - 00:00pm

        Captured groups: hour, minute, and meridiem.
        - <hour>:<minute><meridiem>

        Returns:
        - Pattern: A Pattern object for matching times in the format HH:MM(am or pm).
        """

        time_pattern = s.group('time',
            s.group('hour', s.digit(1, 2)), ':',
            s.group('minute', s.digit(2)),
            s.group('meridiem', s.any_of('am', 'pm'))
        )
        return time_pattern

    @property
    def timestamp_mm_dd_yyyy_hh_mm(self):
        """
        Returns a pattern for matching dates in the format MM/DD/YYYY HH:MM(am or pm).

        Primary match examples:
        - 06/30/2024 2:00pm
        - 12/31/1999 11:59am

        Matched edge-cases to consider:
        - 06-30-2024 2:00pm
        - 06.30.2024 2:00pm
        - 06/30/24 2:00pm

        Named groups: date, time, month, day, year, hour, minute, meridiem.
        - <date> <time>
        - <month>/<day>/<year> <hour>:<minute><meridiem>

        Returns:
        - Pattern: A Pattern object for matching dates in the format MM/DD/YYYY HH:MM(am or pm).
        """
        sep = s.in_chars('-./')
        date_pattern = s.group('date',
            s.group('month', s.digit(2)), sep,
            s.group('day', s.digit(2)), sep,
            s.group('year', s.digit(4))
        )

        time_pattern = s.group('time',
            s.group('hour', s.digit(1, 2)), ':',
            s.group('minute', s.digit(2)),
            s.group('meridiem', s.any_of('am', 'pm'))
        )

        date_time_pattern = s.merge(date_pattern, ' ', time_pattern)
        return date_time_pattern

    @property
    def credit_card_number(self):
        """
        Returns a pattern for matching credit card numbers.

        Primary match examples:
        - 1234-5678-9012-3456
        - 1234.5678.9012.3456
        - 1234 5678 9012 3456

        Matched edge-cases to consider:
        - 1234-5678.9012 3450
        - 1234.5678 9012-3456

        Captured groups:
        - Numbered 1 to 4 for digit set.

        Returns:
        - Pattern: A Pattern object for matching credit card numbers.
        """
        sep = s.in_chars('-. ')
        cc_pattern = s.merge(
            s.capture(s.digit(4)), sep,
            s.capture(s.digit(4)), sep,
            s.capture(s.digit(4)), sep,
            s.capture(s.digit(4))
        )
        return cc_pattern

    @property
    def ssn(self):
        """
        Returns a pattern for matching US Social Security Numbers (SSNs).

        Primary match examples:
        - 123-45-6789
        - 000-00-0000

        Matched edge-cases to consider:
        - 123-45-6789

        Returns:
        - Pattern: A Pattern object for matching US Social Security Numbers (SSNs).
        """
        ssn_pattern = s.merge(
            s.digit(3), '-',
            s.digit(2), '-',
            s.digit(4)
        )
        return ssn_pattern

    @property
    def mac_address(self):
        """
        Returns a pattern for matching MAC addresses.

        Primary match examples:
        - 00:1A:2B:3C:4D:5E
        - 00-1A-2B-3C-4D-5E
        - 001A.2B3C.4D5E

        Matched edge-cases to consider:
        - 00:1A:2B:3C:4D
        - 00:1A:2B:3C:4D:5E:6F

        Captured groups:
        - Each pair of hex digits.

        Returns:
        - Pattern: A Pattern object for matching MAC addresses.
        """
        mac_pattern = s.capture(
            s.hex_digit(2), ':', s.hex_digit(2), ':', s.hex_digit(2), ':',
            s.hex_digit(2), ':', s.hex_digit(2), ':', s.hex_digit(2)
        )
        return mac_pattern

    @property
    def password(self):
        """
        Returns a pattern for matching passwords with complexity requirements.

        Primary match examples:
        - P@ssw0rd!
        - StrongPass123!
        - My_P@ss123

        Matched edge-cases to consider:
        - password
        - 123456

        Returns:
        - Pattern: A Pattern object for matching passwords.
        """
        is_digit = s.merge(s.not_whitespace(0, 0), s.digit())
        is_lower = s.merge(s.not_whitespace(0, 0), s.lower())
        is_upper = s.merge(s.not_whitespace(0, 0), s.upper())
        is_special_char = s.merge(s.not_whitespace(0, 0), s.special_char())
        password_pattern = s.merge(
            s.ahead(is_digit),
            s.ahead(is_lower),
            s.ahead(is_upper),
            s.ahead(is_special_char),
            s.not_whitespace(6, 0)
        )
        return password_pattern

templates = Templates()
