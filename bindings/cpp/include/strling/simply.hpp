// simply.hpp — a small, fluent, memory-safe builder for common patterns
#ifndef STRLING_SIMPLY_HPP
#define STRLING_SIMPLY_HPP

#include <memory>
#include <string>
#include <vector>

namespace strling::simply {

// Internal implementation forward declaration (PIMPL)
struct Impl;

// Forward declaration of public Pattern class
class Pattern;

// Factories
Pattern digit(int n = 1);
Pattern literal(std::string_view s);
Pattern any_of(std::string_view chars);
Pattern start();
Pattern end();
Pattern sequence(const std::vector<Pattern>& parts);
// Convenience overload to allow braced-init lists such as sequence({a, b, c})
Pattern sequence(std::initializer_list<Pattern> parts);

// Pattern class — immutable (returns new Pattern from combinators)
class Pattern {
    std::shared_ptr<Impl> impl;
public:
    Pattern();
    explicit Pattern(std::shared_ptr<Impl> impl);

    // Fluent combinators
    Pattern optional() const;      // like ?
    Pattern as_capture() const;    // make this a capturing group

#ifdef STRLING_INTERNAL
    // Internal access for implementation code and tests (only available when
    // building STRling itself or tests; hidden from public API consumers)
    std::shared_ptr<Impl> impl_ptr() const { return impl; }
#endif

    // Compile / stringify the pattern into a regex
    // Uses the binding-local emitter to produce a standard regex string
    std::string compile() const;

    // For tests / internal use: get a readable representation
    std::string debug_str() const;
};

} // namespace strling::simply

#endif // STRLING_SIMPLY_HPP
