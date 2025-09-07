import textwrap, json, re
from STRling.core import nodes
from STRling.core.compiler import Compiler
from STRling.emitters.pcre2 import emit as emit_pcre2


class Simply:
    """
    Central manager for pattern compilation and emission.
    """
    def __init__(self):
        self.compiler = Compiler()
        
    def build(self, pattern_obj, flags=None):
        """Compile a Pattern object's node to a regex string"""
        ir_root = self.compiler.compile(pattern_obj.node)
        return emit_pcre2(ir_root, flags)


# Global instance for use throughout the library
s = Simply()


class STRlingError(ValueError):
    def __init__(self, message):
        self.message = textwrap.dedent(message).strip().replace('\n', '\n\t')
        super().__init__(self.message)

    def __str__(self):
        return f"\n\nSTRlingError: Invalid Pattern Attempted.\n\n\t{self.message}"

def lit(text):
    # Create a Literal node instead of escaping text
    return Pattern(nodes.Lit(text))

def repeat(min_rep: int = None, max_rep: int = None):
    if min_rep is not None and max_rep is not None:
        if max_rep == 0:
            return f'{{{min_rep},}}'
        if min_rep > max_rep:
            message = """
            Method: Pattern.__call__(min_rep, max_rep)

            The `min_rep` must not be greater than the `max_rep`.

            Ensure the lesser number is on the left and the greater number is on the right.
            """
            raise STRlingError(message)
        return f'{{{min_rep},{max_rep}}}'
    elif min_rep is not None:
        return f'{{{min_rep}}}'
    else:
        return ''

class Pattern:
    """
    A class to construct and compile clean and manageable regex expressions.

    Attributes:
        - node: The AST node representing this pattern piece
        - custom_set (bool): Indicates if the pattern is a custom character set.
        - negated (bool): Indicates if the pattern is a negated custom character set.
        - composite (bool): Indicates if the pattern is a composite pattern.
        - named_groups (list): Indicates the list of named groups within.
        - numbered_group (bool): Indicates if the pattern is a numbered group.
    """
    def __init__(self, node, custom_set: bool = False, negated: bool = False, composite: bool = False, named_groups: list = [], numbered_group: bool = False):
        # Store the AST node instead of a string pattern
        self.node = node
        # Keep compatibility attributes for now
        self.custom_set = custom_set
        self.negated = negated
        self.composite = composite
        self.named_groups = named_groups
        self.numbered_group = numbered_group

    def __call__(self, min_rep: int = None, max_rep: int = None):
        """
        Applies a repetition pattern to the current pattern.

        Parameters: (min_rep/exact_rep, max_rep)
        - min_rep (optional): Specifies the minimum number of characters to match.
        - max_rep (optional): Specifies the maximum number of characters to match, 0 means unlimited, None means match exact count of min_rep.

        Returns:
        - A new Pattern object with the repetition pattern applied.
        """
        # Prevent errors if invoked with no range
        if min_rep is None and max_rep is None:
            return self
            
        # If min_rep or max_rep are specified as non-integers
        if min_rep is not None and not isinstance(min_rep, int) or max_rep is not None and not isinstance(max_rep, int):
            message = """
            Method: Pattern.__call__(min_rep, max_rep)

            The `min_rep` and `max_rep` arguments must be integers (0-9).
            """
            raise STRlingError(message)

        # If min_rep or max_rep are specified out of valid range
        if min_rep is not None and min_rep < 0 or max_rep is not None and max_rep < 0:
            message = """
            Method: Pattern.__call__(min_rep, max_rep)

            The `min_rep` and `max_rep` must be 0 or greater.
            """
            raise STRlingError(message)

        # Named group is unique and not repeatable
        if self.named_groups and min_rep is not None and max_rep is not None:
            message = """
            Method: Pattern.__call__(min_rep, max_rep)

            Named groups cannot be repeated as they must be unique.

            Consider using an unlabeled group (merge) or a numbered group (capture).
            """
            raise STRlingError(message)

        # A group already assigned a specified range cannot be reassigned
        if len(self.pattern) > 1 and self.pattern[-1] == '}' and self.pattern[-2] != '\\':
            message = """
            Method: Pattern.__call__(min_rep, max_rep)

            Cannot re-invoke pattern to specify range that already exists.

            Examples of invalid syntax:
                simply.letter(1, 2)(3, 4) # double invoked range is invalid
                my_pattern = simply.letter(1, 2) # my_pattern was set range (1, 2) # valid
                my_new_pattern = my_pattern(3, 4) # my_pattern was reinvoked (3, 4) # invalid

            Set the range on the first invocation, don't reassign it.

            Examples of valid syntax:
                You can either specify the range now:
                    my_pattern = simply.letter(1, 2)

                Or you can specify the range later:
                    my_pattern = simply.letter() # my_pattern was never assigned a range
                    my_new_pattern = my_pattern(1, 2) # my_pattern was invoked with (1, 2) for the first time.
            """
            raise STRlingError(message)

        # Create Quant node instead of appending a string
        if self.numbered_group:
            if max_rep is not None:
                message = """
                Method: Pattern.__call__(min_rep, max_rep)

                The `max_rep` parameter was specified when capture takes only one parameter, the exact number of copies.

                Consider using an unlabeled group (merge) for a range.
                """
                raise STRlingError(message)
            else:
                # Handle numbered groups differently by duplicating the node
                children = [self.node] * min_rep
                new_node = nodes.Seq(children)
                return self.create_modified_instance(new_node)
        else:
            # Regular case: create a quantifier node
            q_max = float('inf') if max_rep == 0 else max_rep if max_rep is not None else min_rep
            new_node = nodes.Quant(child=self.node, min=min_rep, max=q_max, mode="Greedy")
            return self.create_modified_instance(new_node)

    def __str__(self):
        """
        Returns the compiled regex string.
        """
        return s.build(self)
    
    def exec(self, text_to_search, target="python"):
        # 1. Load the feature matrix
        with open("spec/features.json") as f:
            feature_matrix = json.load(f)

        # 2. Get the full artifact from the compiler
        compiler = Compiler()
        artifact = compiler.compile_with_metadata(self.node)
        features = artifact["metadata"]["features_used"]

        # 3. Check for unsupported features
        unsupported = [
            f for f in features
            if not feature_matrix.get(f, {}).get(target, False)
        ]

        if unsupported:
            # 4. FALLBACK PATH: Use a WASM engine
            print(f"INFO: Using WASM fallback for features: {unsupported}")
            pcre2_regex_str = emit_pcre2(artifact["ir"])
            # return pcre2_wasm_engine.search(pcre2_regex_str, text_to_search)
            # For now, we can just show it would happen:
            return f"WASM_EXEC: '{pcre2_regex_str}' on '{text_to_search}'"
        else:
            # 5. NATIVE PATH: Use Python's `re` module
            # Note: This requires a new emitter for Python's regex syntax.
            # python_regex_str = emit_python_re(artifact["ir"])
            # return re.search(python_regex_str, text_to_search)
            # For now, we can simulate:
            pcre2_simulated_str = emit_pcre2(artifact["ir"])
            return f"NATIVE_EXEC: '{pcre2_simulated_str}' on '{text_to_search}'"


    @classmethod
    def create_modified_instance(cls, new_node, **kwargs):
        """
        Returns a copy of the pattern instance with a new node.
        """
        return cls(new_node, **kwargs)
