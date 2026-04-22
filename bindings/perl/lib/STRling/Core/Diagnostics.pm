package STRling::Core::Diagnostics;

use strict;
use warnings;
use 5.014;

=head1 NAME

STRling::Core::Diagnostics — Phase 3a Safety Guard Types

=head1 DESCRIPTION

Provides the cross-binding diagnostic types raised and surfaced by the
emitter when a pattern would compile to something dangerous (variable
length lookbehind, host-stack-exhausting depth, or catastrophic
backtracking risk). Mirrors the SSOT in C<bindings/typescript/>.

=cut

# Fatal emitter-stage failure raised by an IR safety guard. Carries a
# stable `code` (`VLB_NOT_SUPPORTED`, `MAX_DEPTH`) and the offending
# `engine` so cross-binding parity tests can match on shared substrings
# without coupling to a specific message wording.
package STRling::Core::Diagnostics::STRlingCompilationError {
    use Moo;
    use overload '""' => sub { 'STRlingCompilationError: ' . $_[0]->message }, fallback => 1;

    has 'message' => (is => 'ro', required => 1);
    has 'code'    => (is => 'ro', required => 1);
    has 'engine'  => (is => 'ro', default  => sub { 'pcre2' });
}

# Non-fatal diagnostic. `""` matches the SSOT format
# `STRlingWarning [CODE]: message` so the global pathological fixture's
# `expected_warning` substring compares 1:1 across bindings.
package STRling::Core::Diagnostics::STRlingWarning {
    use Moo;
    use overload '""' => sub {
        'STRlingWarning [' . $_[0]->code . ']: ' . $_[0]->message
    }, fallback => 1;

    has 'code'    => (is => 'ro', required => 1);
    has 'message' => (is => 'ro', required => 1);
}

# Result of an emit pass: produced PCRE2 pattern + non-fatal warnings.
package STRling::Core::Diagnostics::CompileResult {
    use Moo;

    has 'pattern'  => (is => 'ro', required => 1);
    has 'warnings' => (is => 'ro', default  => sub { [] });
}

1;
