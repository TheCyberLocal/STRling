cmake_minimum_required(VERSION 3.20)

project(strling_c_consumer LANGUAGES C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)

find_package(strling-c CONFIG REQUIRED)

add_executable(strling_c_consumer main.c)
target_link_libraries(strling_c_consumer PRIVATE STRling::c)

if(MSVC)
    target_compile_options(strling_c_consumer PRIVATE /W4 /WX)
else()
    target_compile_options(
        strling_c_consumer
        PRIVATE -Wall -Wextra -Wpedantic -Werror
    )
endif()
