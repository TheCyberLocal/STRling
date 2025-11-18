package com.strling.simply;

import com.strling.core.Compiler;
import com.strling.core.Nodes;
import com.strling.core.IR;
import com.strling.emitters.Pcre2Emitter;

/**
 * Central manager for pattern compilation and emission.
 *
 * <p>This internal class handles the compilation pipeline, transforming Pattern
 * objects through the AST -> IR -> emitted regex string stages.</p>
 */
public class Simply {
    private final Compiler compiler;

    /**
     * Creates a new Simply compiler instance.
     */
    public Simply() {
        this.compiler = new Compiler();
    }

    /**
     * Compiles a Pattern object's node to a regex string.
     *
     * @param patternObj The Pattern object to compile
     * @return The compiled regex string in PCRE2 format
     */
    public String build(Pattern patternObj) {
        return build(patternObj, null);
    }

    /**
     * Compiles a Pattern object's node to a regex string.
     *
     * @param patternObj The Pattern object to compile
     * @param flags Optional regex flags to apply
     * @return The compiled regex string in PCRE2 format
     */
    public String build(Pattern patternObj, Nodes.Flags flags) {
        IR.IROp irRoot = compiler.compile(patternObj.getNode());
        return Pcre2Emitter.emit(irRoot, flags);
    }
}
