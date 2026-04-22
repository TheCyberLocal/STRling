use strict;
use warnings;
use Test::More;
use FindBin;
use File::Spec;
use JSON::PP;

use lib File::Spec->catdir($FindBin::Bin, '..', 'lib');
use STRling::Essential;

sub find_spec {
    my $dir = $FindBin::Bin;
    for (1..10) {
        my $candidate = File::Spec->catfile($dir, 'spec', 'stdlib', 'essential_5.json');
        return $candidate if -f $candidate;
        $dir = File::Spec->catdir($dir, '..');
    }
    die "essential_5.json not found";
}

my $spec_path = find_spec();
open my $fh, '<', $spec_path or die "Cannot open $spec_path: $!";
local $/;
my $spec = decode_json(scalar <$fh>);
close $fh;

sub fixtures { return $spec->{patterns}{$_[0]}{fixtures}{$_[1]}; }

sub re_of {
    my $pat = shift;
    my $body = $pat->compile();
    return qr/^(?:$body)$/;
}

sub assert_match_all {
    my ($name, $re, $samples) = @_;
    for my $s (@$samples) {
        ok($s =~ $re, "$name: matches '$s'");
    }
}

sub assert_match_none {
    my ($name, $re, $samples) = @_;
    for my $s (@$samples) {
        ok($s !~ $re, "$name: rejects '$s'");
    }
}

# email
{ my $r = re_of(STRling::Essential::email());
  assert_match_all('email valid',   $r, fixtures('email', 'valid'));
  assert_match_none('email invalid',$r, fixtures('email', 'invalid'));
}
# url
{ my $r = re_of(STRling::Essential::url());
  assert_match_all('url valid',   $r, fixtures('url', 'valid'));
  assert_match_none('url invalid',$r, fixtures('url', 'invalid'));
}
# uuid default
{ my $r = re_of(STRling::Essential::uuid());
  assert_match_all('uuid default valid',   $r, fixtures('uuid', 'valid_default'));
  assert_match_none('uuid default invalid',$r, fixtures('uuid', 'invalid_default'));
}
# uuid v4
{ my $r = re_of(STRling::Essential::uuid(4));
  assert_match_all('uuid v4 valid',   $r, fixtures('uuid', 'valid_v4'));
  assert_match_none('uuid v4 invalid',$r, fixtures('uuid', 'invalid_v4'));
}
# ip v4
{ my $r = re_of(STRling::Essential::ip(4));
  assert_match_all('ip v4 valid',   $r, fixtures('ip', 'valid_v4'));
  assert_match_none('ip v4 invalid',$r, fixtures('ip', 'invalid_v4'));
}
# ip v6
{ my $r = re_of(STRling::Essential::ip(6));
  assert_match_all('ip v6 valid',   $r, fixtures('ip', 'valid_v6'));
  assert_match_none('ip v6 invalid',$r, fixtures('ip', 'invalid_v6'));
}
# ip any
{ my $r = re_of(STRling::Essential::ip());
  assert_match_all('ip any v4', $r, fixtures('ip', 'valid_v4'));
  assert_match_all('ip any v6', $r, fixtures('ip', 'valid_v6'));
}
# date_time
{ my $r = re_of(STRling::Essential::date_time());
  assert_match_all('dateTime valid',   $r, fixtures('dateTime', 'valid'));
  assert_match_none('dateTime invalid',$r, fixtures('dateTime', 'invalid'));
}

done_testing();
