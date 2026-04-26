cmake_minimum_required(VERSION 3.10)
project(TestDLL LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)

add_library(test_dll SHARED main.cpp)

set_target_properties(test_dll PROPERTIES 
    PREFIX ""
    OUTPUT_NAME "test_dll"
)
