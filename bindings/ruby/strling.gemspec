# frozen_string_literal: true

Gem::Specification.new do |spec|
  spec.name        = 'strling'
  spec.version     = '3.0.0.alpha'
  spec.authors     = ['TheCyberLocal']
  spec.email       = []
  spec.summary     = 'Next-gen string pattern DSL & compiler'
  spec.description = 'STRling is a next-generation string pattern DSL and compiler that provides a readable, maintainable alternative to traditional regular expressions.'
  spec.homepage    = 'https://github.com/TheCyberLocal/STRling'
  spec.license     = 'MIT'
  spec.required_ruby_version = '>= 3.0.0'

  spec.metadata['homepage_uri'] = spec.homepage
  spec.metadata['source_code_uri'] = 'https://github.com/TheCyberLocal/STRling'
  spec.metadata['documentation_uri'] = 'https://github.com/TheCyberLocal/STRling/tree/main/docs'
  spec.metadata['bug_tracker_uri'] = 'https://github.com/TheCyberLocal/STRling/issues'

  # Specify which files should be added to the gem when it is released.
  spec.files = Dir.glob([
    'lib/**/*.rb',
    'README.md',
    'LICENSE'
  ])

  spec.require_paths = ['lib']

  # Runtime dependencies
  # (none currently)

  # Development dependencies
  spec.add_development_dependency 'rake', '~> 13.0'
  spec.add_development_dependency 'rspec', '~> 3.13'
end
