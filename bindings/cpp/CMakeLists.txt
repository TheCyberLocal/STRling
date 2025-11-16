cmake_minimum_required(VERSION 3.15)

project(STRling
    VERSION 0.1.0
    DESCRIPTION "STRling C++ Binding - Next-generation production-grade syntax for regular expressions"
    LANGUAGES CXX
)

# Set C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Include directories
include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

# Collect source files
file(GLOB_RECURSE STRLING_SOURCES
    ${CMAKE_CURRENT_SOURCE_DIR}/src/core/*.cpp
)

# Collect header files
file(GLOB_RECURSE STRLING_HEADERS
    ${CMAKE_CURRENT_SOURCE_DIR}/include/strling/*.hpp
)

# Create the STRling library
add_library(strling STATIC
    ${STRLING_SOURCES}
    ${STRLING_HEADERS}
)

# Set include directories for the library
target_include_directories(strling
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)

# Enable warnings
if(MSVC)
    target_compile_options(strling PRIVATE /W4)
else()
    target_compile_options(strling PRIVATE -Wall -Wextra -Wpedantic)
endif()

# Installation rules
install(TARGETS strling
    EXPORT STRlingTargets
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
    RUNTIME DESTINATION bin
    INCLUDES DESTINATION include
)

install(DIRECTORY include/strling
    DESTINATION include
)

# Export targets
install(EXPORT STRlingTargets
    FILE STRlingTargets.cmake
    NAMESPACE STRling::
    DESTINATION lib/cmake/STRling
)

# Create config file
include(CMakePackageConfigHelpers)
write_basic_package_version_file(
    "${CMAKE_CURRENT_BINARY_DIR}/STRlingConfigVersion.cmake"
    VERSION ${PROJECT_VERSION}
    COMPATIBILITY AnyNewerVersion
)

configure_package_config_file(
    "${CMAKE_CURRENT_SOURCE_DIR}/cmake/STRlingConfig.cmake.in"
    "${CMAKE_CURRENT_BINARY_DIR}/STRlingConfig.cmake"
    INSTALL_DESTINATION lib/cmake/STRling
)

# Option to build tests
option(BUILD_TESTS "Build test suite" OFF)

if(BUILD_TESTS)
    enable_testing()
    add_subdirectory(test)
endif()
