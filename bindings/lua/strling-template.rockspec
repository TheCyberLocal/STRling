package = "strling"
version = "VERSION-1" -- The CD will inject the version here
source = {
   url = "git+https://github.com/strling-lang/strling.git",
   tag = "vVERSION"
}
description = {
   summary = "Thin Lua adapter for the canonical STRling compiler",
   detailed = [[ STRling projects canonical request and result data through a caller-selected strling.c-abi v1 library. ]],
   homepage = "https://github.com/strling-lang/strling",
   license = "Apache-2.0"
}
dependencies = {
   "lua >= 5.1, < 5.5",
   "lua-cjson >= 2.1.0, < 3.0.0"
}
build = {
   type = "builtin",
   modules = {
      strling = "src/adapter.lua",
      ["strling.stdlib_generated"] = "src/stdlib_generated.lua",
      strling_native = {
         sources = { "src/strling_native.c" },
         libraries = { "dl" }
      }
   }
}
