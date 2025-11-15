"""
STRling Simply API - Main Entry Point

This module provides the complete public API for the STRling Simply interface,
which allows developers to build regex patterns using a fluent, chainable API.
It re-exports all constructors, lookarounds, character sets, static patterns,
and compilation utilities from their respective modules.

The Simply API is designed to be intuitive and self-documenting, replacing
cryptic regex syntax with readable function calls and method chains.
"""

from STRling.simply.pattern import Pattern, lit, STRlingError
from STRling.simply.constructors import *
from STRling.simply.lookarounds import *
from STRling.simply.sets import *
from STRling.simply.static import *
