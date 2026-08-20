cmake_minimum_required(VERSION 3.20)

project(strling_cpp_consumer LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(strling-cpp CONFIG REQUIRED)

add_executable(strling_cpp_consumer main.cpp)
target_link_libraries(strling_cpp_consumer PRIVATE STRling::cpp)

if(MSVC)
    target_compile_options(strling_cpp_consumer PRIVATE /W4 /WX /permissive-)
else()
    target_compile_options(
        strling_cpp_consumer
        PRIVATE -Wall -Wextra -Wpedantic -Werror
    )
endif()
