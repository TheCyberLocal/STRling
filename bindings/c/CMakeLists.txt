cmake_minimum_required(VERSION 3.20)

project(strling_c VERSION 3.0.0 LANGUAGES C)

include(CTest)
include(GNUInstallDirs)
include(CMakePackageConfigHelpers)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)

option(STRLING_C_WARNINGS_AS_ERRORS "Treat C adapter warnings as errors" ON)

find_program(
    STRLING_CARGO_EXECUTABLE
    NAMES cargo
    HINTS "$ENV{USERPROFILE}/.cargo/bin" "$ENV{HOME}/.cargo/bin"
    REQUIRED
)

get_filename_component(STRLING_REPOSITORY_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../.." ABSOLUTE)
set(STRLING_INTEROP_MANIFEST "${STRLING_REPOSITORY_ROOT}/bindings/interop/Cargo.toml")
set(STRLING_INTEROP_TARGET_DIR "${CMAKE_CURRENT_BINARY_DIR}/interop-target")

if(WIN32)
    set(STRLING_INTEROP_STATIC_LIBRARY
        "${STRLING_INTEROP_TARGET_DIR}/release/strling_interop.lib"
    )
else()
    set(STRLING_INTEROP_STATIC_LIBRARY
        "${STRLING_INTEROP_TARGET_DIR}/release/libstrling_interop.a"
    )
endif()

file(
    GLOB_RECURSE
    STRLING_INTEROP_INPUTS
    CONFIGURE_DEPENDS
    "${STRLING_REPOSITORY_ROOT}/bindings/interop/src/*.rs"
    "${STRLING_REPOSITORY_ROOT}/bindings/interop/Cargo.toml"
    "${STRLING_REPOSITORY_ROOT}/bindings/interop/Cargo.lock"
    "${STRLING_REPOSITORY_ROOT}/core/src/*.rs"
    "${STRLING_REPOSITORY_ROOT}/core/Cargo.toml"
    "${STRLING_REPOSITORY_ROOT}/spec/interop/1.0/*.json"
)

add_custom_command(
    OUTPUT "${STRLING_INTEROP_STATIC_LIBRARY}"
    COMMAND
        "${STRLING_CARGO_EXECUTABLE}" build
        --manifest-path "${STRLING_INTEROP_MANIFEST}"
        --release
        --locked
        --target-dir "${STRLING_INTEROP_TARGET_DIR}"
    DEPENDS ${STRLING_INTEROP_INPUTS}
    WORKING_DIRECTORY "${STRLING_REPOSITORY_ROOT}"
    COMMENT "Building canonical strling-interop static library"
    VERBATIM
)

add_custom_target(
    strling_interop_build
    DEPENDS "${STRLING_INTEROP_STATIC_LIBRARY}"
)

add_library(strling_interop_native STATIC IMPORTED GLOBAL)
set_target_properties(
    strling_interop_native
    PROPERTIES IMPORTED_LOCATION "${STRLING_INTEROP_STATIC_LIBRARY}"
)

add_library(
    strling
    STATIC
    src/strling.c
    src/strling_essential.c
    src/strling_simply.c
)
add_dependencies(strling strling_interop_build)
target_include_directories(
    strling
    PUBLIC
        "$<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>"
        "$<BUILD_INTERFACE:${STRLING_REPOSITORY_ROOT}/bindings/interop/include>"
        "$<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>"
)
target_link_libraries(strling PUBLIC strling_interop_native)

if(MSVC)
    target_compile_options(strling PRIVATE /W4)
    if(STRLING_C_WARNINGS_AS_ERRORS)
        target_compile_options(strling PRIVATE /WX)
    endif()
    target_link_libraries(strling PUBLIC advapi32 bcrypt ntdll userenv ws2_32)
else()
    find_package(Threads REQUIRED)
    target_compile_options(strling PRIVATE -Wall -Wextra -Wpedantic)
    if(STRLING_C_WARNINGS_AS_ERRORS)
        target_compile_options(strling PRIVATE -Werror)
    endif()
    target_link_libraries(strling PUBLIC Threads::Threads ${CMAKE_DL_LIBS} m)
endif()

if(APPLE)
    target_link_libraries(strling PUBLIC "-framework CoreFoundation" "-framework Security")
endif()

if(BUILD_TESTING)
    add_executable(strling_c_adapter_tests tests/adapter_test.c)
    target_link_libraries(strling_c_adapter_tests PRIVATE strling)
    add_test(NAME strling_c_adapter COMMAND strling_c_adapter_tests)
    set_tests_properties(
        strling_c_adapter
        PROPERTIES WORKING_DIRECTORY "${STRLING_REPOSITORY_ROOT}"
    )

    add_executable(strling_c_thread_tests tests/thread_test.c)
    target_link_libraries(strling_c_thread_tests PRIVATE strling)
    add_test(NAME strling_c_threads COMMAND strling_c_thread_tests)
    set_tests_properties(
        strling_c_threads
        PROPERTIES WORKING_DIRECTORY "${STRLING_REPOSITORY_ROOT}"
    )
endif()

install(
    TARGETS strling
    ARCHIVE DESTINATION "${CMAKE_INSTALL_LIBDIR}"
)
install(
    FILES
        include/strling.h
        include/strling_essential.h
        include/strling_simply.h
        "${STRLING_REPOSITORY_ROOT}/bindings/interop/include/strling_interop.h"
    DESTINATION "${CMAKE_INSTALL_INCLUDEDIR}"
)
install(
    FILES "${STRLING_INTEROP_STATIC_LIBRARY}"
    DESTINATION "${CMAKE_INSTALL_LIBDIR}"
)

set(STRLING_C_ARCHIVE_NAME
    "${CMAKE_STATIC_LIBRARY_PREFIX}strling${CMAKE_STATIC_LIBRARY_SUFFIX}"
)
if(WIN32)
    set(STRLING_INTEROP_ARCHIVE_NAME "strling_interop.lib")
else()
    set(STRLING_INTEROP_ARCHIVE_NAME "libstrling_interop.a")
endif()
configure_package_config_file(
    cmake/strling-c-config.cmake.in
    "${CMAKE_CURRENT_BINARY_DIR}/strling-c-config.cmake"
    INSTALL_DESTINATION "${CMAKE_INSTALL_LIBDIR}/cmake/strling-c"
)
write_basic_package_version_file(
    "${CMAKE_CURRENT_BINARY_DIR}/strling-c-config-version.cmake"
    VERSION "${PROJECT_VERSION}"
    COMPATIBILITY SameMajorVersion
)
install(
    FILES
        "${CMAKE_CURRENT_BINARY_DIR}/strling-c-config.cmake"
        "${CMAKE_CURRENT_BINARY_DIR}/strling-c-config-version.cmake"
    DESTINATION "${CMAKE_INSTALL_LIBDIR}/cmake/strling-c"
)
