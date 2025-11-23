use 5.010;
use strict;
use warnings;
use ExtUtils::MakeMaker;

WriteMakefile(
    NAME             => 'STRling',
    AUTHOR           => 'TheCyberLocal',
    VERSION_FROM     => 'lib/STRling.pm',
    ABSTRACT_FROM    => 'lib/STRling.pm',
    LICENSE          => 'perl_5',
    MIN_PERL_VERSION => '5.010',
    CONFIGURE_REQUIRES => {
        'ExtUtils::MakeMaker' => '0',
    },
    TEST_REQUIRES => {
        'Test::More' => '0',
        'JSON::PP'   => '0',
    },
    PREREQ_PM => {
        'Moo'        => '2.005000',
        'Type::Tiny' => '2.000000',
    },
    dist  => { COMPRESS => 'gzip -9f', SUFFIX => 'gz', },
    clean => { FILES => 'STRling-*' },
);
