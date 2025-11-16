package STRling;

# ABSTRACT: Next-gen string pattern DSL & compiler for Perl

use strict;
use warnings;

our $VERSION = '3.0.0-alpha';

=head1 NAME

STRling - Next-gen string pattern DSL & compiler for Perl

=head1 SYNOPSIS

    use STRling;
    
    # STRling provides a modern, readable alternative to traditional regex syntax
    # This module serves as the main entry point for the STRling Perl binding

=head1 DESCRIPTION

STRling is a next-generation string pattern Domain-Specific Language (DSL)
and compiler that compiles to standard regular expressions. It provides
a readable, beginner-friendly syntax for pattern matching while maintaining
the full power of regex.

This is the Perl binding for STRling. It provides:

=over 4

=item * Core AST node definitions for parsed patterns

=item * Intermediate Representation (IR) for optimized patterns

=item * Error handling with instructional diagnostics

=item * Pattern compilation to PCRE2-compatible regex

=back

=head1 SEE ALSO

L<STRling::Core::Nodes>, L<STRling::Core::IR>, L<STRling::Core::Errors>

=head1 AUTHOR

TheCyberLocal

=head1 LICENSE

This library is free software; you can redistribute it and/or modify
it under the same terms as Perl itself.

=cut

1;
