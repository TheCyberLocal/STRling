Gem::Specification.new do |s|
  s.name        = 'strling'
  s.version     = '0.0.0.dev' # Do NOT change this to a number
  s.summary     = "Thin Ruby adapter for the canonical STRling compiler."
  s.description = "STRling projects canonical request and result data through a caller-selected strling.c-abi v1 library."
  s.authors     = ["STRling Team"]
  s.email       = 'dev@strling.io'
  s.files       = Dir["lib/**/*.rb", "LICENSE", "README.md"]
  s.homepage    = 'https://github.com/strling-lang/strling'
  s.license     = 'Apache-2.0'
  s.metadata    = {
    "source_code_uri" => "https://github.com/strling-lang/strling",
    "bug_tracker_uri" => "https://github.com/strling-lang/strling/issues"
  }
  s.required_ruby_version = Gem::Requirement.new('>= 3.0', '< 4.0')
end
