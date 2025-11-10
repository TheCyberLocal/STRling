/**
 * STRling Simply API - Main Entry Point
 *
 * This module provides the complete public API for the STRling Simply interface,
 * which allows developers to build regex patterns using a fluent, chainable API.
 * It re-exports all constructors, lookarounds, character sets, static patterns,
 * and compilation utilities from their respective modules.
 *
 * The Simply API is designed to be intuitive and self-documenting, replacing
 * cryptic regex syntax with readable function calls and method chains.
 */

export { Pattern, lit } from "./pattern.js";
export * from "./constructors.js";
export * from "./lookarounds.js";
export * from "./sets.js";
export * from "./static.js";
export * from "../compiler.js";
