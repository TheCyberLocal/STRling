Gem::Specification.new do |s|
  s.name        = 'strling'
  s.version     = '0.0.0.dev' # Do NOT change this to a number
  s.summary     = "Next-generation production-grade syntax for regex."
  s.description = "STRling provides an object-oriented approach to pattern matching with a focus on instructional error handling."
  s.authors     = ["STRling Team"]
  s.email       = 'dev@strling.io'
  s.files       = Dir["lib/**/*.rb", "LICENSE", "README.md"]
  s.homepage    = 'https://github.com/strling-lang/strling'
  s.license     = 'MIT'
  s.metadata    = {
    "source_code_uri" => "https://github.com/strling-lang/strling",
    "bug_tracker_uri" => "https://github.com/strling-lang/strling/issues"
  }
  s.required_ruby_version = '>= 3.0'
end