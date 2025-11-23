package = "strling"
version = "3.0.0-alpha-1"
source = {
   url = "git+https://github.com/TheCyberLocal/STRling.git"
}
description = {
   summary = "A next-generation regex DSL compiler",
   detailed = [[
      STRling is a next-generation regex DSL compiler.
   ]],
   homepage = "https://github.com/TheCyberLocal/STRling",
   license = "MIT"
}
dependencies = {
   "lua >= 5.1"
}
build = {
   type = "builtin",
   modules = {
      strling = "src/strling.lua"
   }
}
