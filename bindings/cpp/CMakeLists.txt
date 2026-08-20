cmake_minimum_required(VERSION 3.20)

project(strling_cpp VERSION 3.0.0 LANGUAGES CXX)

include(CTest)
include(GNUInstallDirs)
include(CMakePackageConfigHelpers)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(STRLING_CPP_WARNINGS_AS_ERRORS "Treat C++ adapter warnings as errors" ON)
option(STRLING_CPP_ENABLE_SANITIZERS "Enable supported address/UB sanitizers" OFF)

get_filename_component(STRLING_REPOSITORY_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../.." ABSOLUTE)

if(NOT TARGET STRling::c)
    add_subdirectory(
        "${CMAKE_CURRENT_SOURCE_DIR}/../c"
        "${CMAKE_CURRENT_BINARY_DIR}/native-c"
    )
endif()

add_library(
    strling_cpp
    STATIC
    src/strling.cpp
    src/simply.cpp
    src/essential.cpp
)
add_library(STRling::cpp ALIAS strling_cpp)
set_target_properties(strling_cpp PROPERTIES EXPORT_NAME cpp)
target_include_directories(
    strling_cpp
    PUBLIC
        "$<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>"
        "$<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>"
)
target_link_libraries(
    strling_cpp
    PUBLIC STRling::c
)

function(strling_cpp_strict target)
    if(MSVC)
        target_compile_options(${target} PRIVATE /W4 /WX /permissive- /EHsc)
    else()
        target_compile_options(${target} PRIVATE -Wall -Wextra -Wpedantic -Werror)
    endif()
endfunction()

strling_cpp_strict(strling_cpp)

if(STRLING_CPP_ENABLE_SANITIZERS AND NOT MSVC)
    target_compile_options(
        strling_cpp
        PRIVATE -fsanitize=address,undefined -fno-omit-frame-pointer
    )
    target_link_options(strling_cpp PUBLIC -fsanitize=address,undefined)
endif()

if(BUILD_TESTING)
    add_executable(strling_cpp_adapter_tests tests/adapter_test.cpp)
    target_link_libraries(strling_cpp_adapter_tests PRIVATE STRling::cpp)
    strling_cpp_strict(strling_cpp_adapter_tests)
    add_test(NAME strling_cpp_adapter COMMAND strling_cpp_adapter_tests)
    set_tests_properties(
        strling_cpp_adapter
        PROPERTIES WORKING_DIRECTORY "${STRLING_REPOSITORY_ROOT}"
    )

    add_executable(strling_cpp_thread_tests tests/thread_test.cpp)
    target_link_libraries(strling_cpp_thread_tests PRIVATE STRling::cpp)
    strling_cpp_strict(strling_cpp_thread_tests)
    add_test(NAME strling_cpp_threads COMMAND strling_cpp_thread_tests)
    set_tests_properties(
        strling_cpp_threads
        PROPERTIES WORKING_DIRECTORY "${STRLING_REPOSITORY_ROOT}"
    )

    add_executable(strling_cpp_certification tests/certification_runner.cpp)
    target_link_libraries(strling_cpp_certification PRIVATE STRling::cpp)
    strling_cpp_strict(strling_cpp_certification)
endif()

install(
    TARGETS strling_cpp
    ARCHIVE DESTINATION "${CMAKE_INSTALL_LIBDIR}"
)
install(
    FILES
        include/strling/strling.hpp
        include/strling/native.hpp
        include/strling/simply.hpp
        include/strling/essential.hpp
    DESTINATION "${CMAKE_INSTALL_INCLUDEDIR}/strling"
)
set(STRLING_CPP_ARCHIVE_NAME
    "${CMAKE_STATIC_LIBRARY_PREFIX}strling_cpp${CMAKE_STATIC_LIBRARY_SUFFIX}"
)
configure_package_config_file(
    cmake/strling-cpp-config.cmake.in
    "${CMAKE_CURRENT_BINARY_DIR}/strling-cpp-config.cmake"
    INSTALL_DESTINATION "${CMAKE_INSTALL_LIBDIR}/cmake/strling-cpp"
)
write_basic_package_version_file(
    "${CMAKE_CURRENT_BINARY_DIR}/strling-cpp-config-version.cmake"
    VERSION "${PROJECT_VERSION}"
    COMPATIBILITY SameMajorVersion
)
install(
    FILES
        "${CMAKE_CURRENT_BINARY_DIR}/strling-cpp-config.cmake"
        "${CMAKE_CURRENT_BINARY_DIR}/strling-cpp-config-version.cmake"
    DESTINATION "${CMAKE_INSTALL_LIBDIR}/cmake/strling-cpp"
)
