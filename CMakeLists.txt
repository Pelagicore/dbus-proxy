
cmake_minimum_required(VERSION 2.6)

set(PACKAGE dbus-proxy)
project(${PACKAGE})

find_package(PkgConfig REQUIRED)

pkg_check_modules(DEPENDENCIES REQUIRED dbus-1 dbus-glib-1 jansson)
add_definitions(${DEPENDENCIES_CFLAGS_OTHER})
include_directories(${DEPENDENCIES_INCLUDE_DIRS})

add_executable( dbus-proxy 
	proxy.c
)

TARGET_LINK_LIBRARIES( dbus-proxy 
	${DEPENDENCIES_LIBRARIES}
)

INSTALL(TARGETS dbus-proxy RUNTIME DESTINATION bin)

