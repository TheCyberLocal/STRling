use strling::parse;
use strling::core::compiler::Compiler;
use strling::emitters::pcre2::PCRE2Emitter;

fn main() {
    println!("=== STRling Rust Binding Demo ===\n");
    
    // Test 1: Simple literal
    println!("Test 1: Simple literal");
    let (flags, ast) = parse("hello").unwrap();
    let mut compiler = Compiler::new();
    let result = compiler.compile_with_metadata(&ast);
    let emitter = PCRE2Emitter::new(flags);
    println!("  Input:  'hello'");
    println!("  Output: '{}'", emitter.emit(&result.ir));
    println!("  Features: {:?}\n", result.metadata.features_used);
    
    // Test 2: Anchors and quantifier
    println!("Test 2: Anchors and quantifier");
    let (flags, ast) = parse("^test.*$").unwrap();
    let mut compiler = Compiler::new();
    let result = compiler.compile_with_metadata(&ast);
    let emitter = PCRE2Emitter::new(flags);
    println!("  Input:  '^test.*$'");
    println!("  Output: '{}'", emitter.emit(&result.ir));
    println!("  Features: {:?}\n", result.metadata.features_used);
    
    // Test 3: Alternation
    println!("Test 3: Alternation");
    let (flags, ast) = parse("cat|dog|bird").unwrap();
    let mut compiler = Compiler::new();
    let result = compiler.compile_with_metadata(&ast);
    let emitter = PCRE2Emitter::new(flags);
    println!("  Input:  'cat|dog|bird'");
    println!("  Output: '{}'", emitter.emit(&result.ir));
    println!("  Features: {:?}\n", result.metadata.features_used);
    
    // Test 4: Groups and quantifiers
    println!("Test 4: Capturing group with quantifier");
    let (flags, ast) = parse("(ab)+").unwrap();
    let mut compiler = Compiler::new();
    let result = compiler.compile_with_metadata(&ast);
    let emitter = PCRE2Emitter::new(flags);
    println!("  Input:  '(ab)+'");
    println!("  Output: '{}'", emitter.emit(&result.ir));
    println!("  Features: {:?}\n", result.metadata.features_used);
    
    // Test 5: Named group
    println!("Test 5: Named group");
    let (flags, ast) = parse("(?<word>\\w+)").unwrap();
    let mut compiler = Compiler::new();
    let result = compiler.compile_with_metadata(&ast);
    let emitter = PCRE2Emitter::new(flags);
    println!("  Input:  '(?<word>\\\\w+)'");
    println!("  Output: '{}'", emitter.emit(&result.ir));
    println!("  Features: {:?}\n", result.metadata.features_used);
    
    // Test 6: Lookahead
    println!("Test 6: Positive lookahead");
    let (flags, ast) = parse("test(?=123)").unwrap();
    let mut compiler = Compiler::new();
    let result = compiler.compile_with_metadata(&ast);
    let emitter = PCRE2Emitter::new(flags);
    println!("  Input:  'test(?=123)'");
    println!("  Output: '{}'", emitter.emit(&result.ir));
    println!("  Features: {:?}\n", result.metadata.features_used);
}
