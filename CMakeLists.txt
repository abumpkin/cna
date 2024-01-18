cmake_minimum_required(VERSION 3.22)

project(winif LANGUAGES C)

aux_source_directory(winif sources)
aux_source_directory(cjson sources)
aux_source_directory(base64 sources)
message("${sources}")
add_library(winif SHARED ${sources})
target_link_libraries(winif IPHLPAPI.lib Ntdll.lib Ws2_32.lib)
target_include_directories(winif PUBLIC "cjson" "base64")



