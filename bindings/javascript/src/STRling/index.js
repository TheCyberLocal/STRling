/**
 * STRling JavaScript Binding - Main Entry Point
 *
 * This is the root module for the STRling JavaScript binding. It re-exports
 * the Simply API namespace, providing access to all public pattern construction
 * and manipulation functions.
 *
 * The Simply API is the recommended way to use STRling in JavaScript, offering
 * a fluent, chainable interface for building regex patterns without dealing
 * with cryptic regex syntax.
 */

export * as simply from "./simply/index.js";
