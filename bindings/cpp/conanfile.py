from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import copy


class STRlingConan(ConanFile):
    """
    Conan recipe for STRling C++ binding.
    
    STRling is a next-generation production-grade syntax designed as a user
    interface for writing powerful regular expressions with an object-oriented
    approach and instructional error handling.
    """
    
    name = "strling"
    version = "0.1.0"
    license = "MIT"
    author = "TheCyberLocal"
    url = "https://github.com/TheCyberLocal/STRling"
    description = "Next-generation production-grade syntax for regular expressions"
    topics = ("regex", "pattern-matching", "dsl", "parsing")
    
    # Binary configuration
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "build_tests": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "build_tests": False,
    }
    
    # Sources are located in the same repository
    exports_sources = "CMakeLists.txt", "src/*", "include/*", "test/*", "cmake/*"
    
    def config_options(self):
        """Remove fPIC option on Windows."""
        if self.settings.os == "Windows":
            del self.options.fPIC
    
    def configure(self):
        """Configure shared library settings."""
        if self.options.shared:
            self.options.rm_safe("fPIC")
    
    def requirements(self):
        """Declare package dependencies."""
        # Core library has no external dependencies
        pass
    
    def build_requirements(self):
        """Declare build-time dependencies."""
        if self.options.build_tests:
            self.test_requires("gtest/1.14.0")
    
    def layout(self):
        """Define the project layout."""
        cmake_layout(self)
    
    def generate(self):
        """Generate CMake configuration files."""
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTS"] = self.options.build_tests
        tc.generate()
        
        deps = CMakeDeps(self)
        deps.generate()
    
    def build(self):
        """Build the project using CMake."""
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
    
    def package(self):
        """Package the built library and headers."""
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE*", src=self.source_folder, dst=self.package_folder)
    
    def package_info(self):
        """Define package information for consumers."""
        self.cpp_info.libs = ["strling"]
        self.cpp_info.includedirs = ["include"]
