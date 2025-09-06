# ADR-001: Iron Law of Emitters and Bindings

**Status:** Proposed  
**Date:** 2025-09-06  
**Context:** STRling v3 requires a hard boundary between compilation (emitters) and runtime (bindings).  
**Decision:** Emitters are pure IR → TargetArtifact functions; bindings are runtime adapters that execute TargetArtifacts and handle capability negotiation/fallbacks.  
**Consequences:** +Portability, +Testability, +Safety; −Slight complexity increase.
