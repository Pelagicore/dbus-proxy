
cmake_minimum_required(VERSION 2.6)

set(PACKAGE dbus-proxy)
project(${PACKAGE})

find_package(PkgConfig REQUIRED)

pkg_check_modules(DEPENDENCIES REQUIRED dbus-1 dbus-glib-1 jansson)
add_definitions(${DEPENDENCIES_CFLAGS_OTHER})
include_directories(${DEPENDENCIES_INCLUDE_DIRS})

add_executable(dbus-proxy
	src/proxy.c
)

target_link_libraries(dbus-proxy
	${DEPENDENCIES_LIBRARIES}
)

install(TARGETS dbus-proxy RUNTIME DESTINATION bin)

