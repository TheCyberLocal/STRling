package = "strling"
version = "VERSION-1" -- The CD will inject the version here
source = {
   url = "git+https://github.com/strling-lang/strling.git",
   tag = "vVERSION"
}
description = {
   summary = "Next-generation production-grade syntax for regular expressions",
   detailed = [[ STRling provides an object-oriented approach to pattern matching with a focus on instructional error handling. ]],
   homepage = "https://github.com/strling-lang/strling",
   license = "Apache-2.0"
}
dependencies = {
   "lua >= 5.1",
   "lua-cjson"
}
build = {
   type = "builtin",
   modules = {
      strling = "src/strling.lua",
      ["strling.simply"] = "src/simply.lua"
   }
}
