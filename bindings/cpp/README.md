# STRling - C++ Binding

> Part of the [STRling Project](https://github.com/strling-lang/strling/blob/main/README.md)

<table>
	<tr>
		<td style="padding: 10px;"><img src="https://raw.githubusercontent.com/strling-lang/.github/refs/heads/main/strling_silver_bell.png" alt="STRling Logo" width="100" /></td>
		<td style="padding: 10px;">
			<strong>C++ Implementation.</strong><br>
			Semantic, Object-Oriented regex compilation for modern C++ (C++17+).
		</td>
	</tr>
</table>

## 💿 Installation

### CMake: Local Source Integration

The primary integration path today is source-based CMake consumption from this repository:

```cmake
set(BUILD_TESTS OFF CACHE BOOL "" FORCE)
add_subdirectory(path/to/strling/bindings/cpp)

add_executable(example main.cpp)
target_link_libraries(example PRIVATE strling)
```

The public target name is `strling`, as defined in `bindings/cpp/CMakeLists.txt`. Public headers are exposed from `bindings/cpp/include`.

### CMake: FetchContent

If you prefer to vendor the repository at configure time, point `FetchContent` at the C++ binding subdirectory and still link the same `strling` target:

```cmake
include(FetchContent)

FetchContent_Declare(
		strling_repo
		GIT_REPOSITORY https://github.com/strling-lang/strling.git
		GIT_TAG main
		SOURCE_SUBDIR bindings/cpp
)

FetchContent_MakeAvailable(strling_repo)

add_executable(example main.cpp)
target_link_libraries(example PRIVATE strling)
```

### Conan: Local Recipe Workflow

The repository also ships a local Conan recipe in `bindings/cpp/conanfile.py`:

```bash
conan create bindings/cpp --build=missing
```

Use this path when you want a reproducible local package build around the repository's current CMake project. The binding's install and export rules are still commented out in `bindings/cpp/CMakeLists.txt`, so the most deterministic consumer story today remains source integration via CMake. Treat Conan as a local packaging and validation workflow unless you have already published the recipe to your own remote.

## 📦 Usage

Here is how to match a US Phone number (e.g., `555-0199`) using STRling in **C++**:

```cpp
#include <iostream>
#include "strling/simply.hpp"

using namespace strling::simply;

int main() {
		auto phone = merge({
				start(),
				digit(3).as_capture(),
				any_of("-. ").may(),
				digit(3).as_capture(),
				any_of("-. ").may(),
				digit(4).as_capture(),
				end()
		});

		std::cout << phone.compile() << '\n';
		return 0;
}
```

> **Note:** This compiles to the optimized regex: `^(\d{3})[-. ]?(\d{3})[-. ]?(\d{4})$`

## 🚀 Why STRling?

Regular Expressions are powerful but notorious for being "write-only" code. STRling solves this by treating Regex as **Software**, not a string.

- **🧩 Composability:** Regex strings are hard to merge. STRling lets you build reusable components (e.g., `ip_address`, `email`) and safely compose them into larger patterns without breaking operator precedence or capturing groups.
- **🛡️ Type Safety:** Catch syntax errors, invalid ranges, and incompatible flags at **compile time** inside your IDE, not at runtime when your app crashes.
- **🧠 IntelliSense & Autocomplete:** Stop memorizing cryptic codes like `(?<=...)`. Use fluent, self-documenting methods with full IDE discovery.
- **📖 Readability First:** Code is read far more often than it is written. STRling patterns describe _intent_, making them understandable to junior developers and future maintainers instantly.
- **🌍 Polyglot Engine:** One mental model, 17 languages. Whether you are writing Rust, Python, or TypeScript, the syntax and behavior remain identical.

## 🏗️ Architecture

STRling follows a strict compiler pipeline architecture to ensure consistency across all ecosystems:

1.  **Parse**: `DSL -> AST` (Abstract Syntax Tree) - Converts the human-readable STRling syntax into a structured tree.
2.  **Compile**: `AST -> IR` (Intermediate Representation) - Transforms the AST into a target-agnostic intermediate representation, optimizing structures like literal sequences.
3.  **Emit**: `IR -> Target Regex` - Generates the final, optimized regex string for the specific target engine (e.g., PCRE2, JS, Python `re`).

## 📚 Documentation

- [**API Reference**](./docs/api_reference.md): Detailed documentation for this binding.
- [**Project Hub**](../../README.md): The main STRling repository.
- [**Specification**](../../spec/README.md): The core grammar and semantic specifications.
- [**Ecosystem & Distribution Matrix**](../../docs/OFFICIAL_PUBLICATION_STEPS.md): Release and publication guidance across bindings.

## 🌐 Connect

[![GitHub](https://img.shields.io/badge/GitHub-black?logo=github&logoColor=white)](https://github.com/strling-lang)

## 💖 Support

If you find STRling useful, consider starring the repository and contributing!
