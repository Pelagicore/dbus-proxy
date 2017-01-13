
# Copyright (C) 2013-2016 Pelagicore AB  <joakim.gross@pelagicore.com>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
# Boston, MA  02110-1301, USA.
#
# For further information see LICENSE


cmake_minimum_required(VERSION 2.6)

set(PACKAGE dbus-proxy)
project(${PACKAGE})

find_package(PkgConfig REQUIRED)

pkg_check_modules(DEPENDENCIES REQUIRED dbus-1 dbus-glib-1 jansson)
add_definitions(${DEPENDENCIES_CFLAGS_OTHER})
include_directories(${DEPENDENCIES_INCLUDE_DIRS})

set(${PROJECT_NAME}_MAJOR_VERSION 1)
set(${PROJECT_NAME}_MINOR_VERSION 0)
set(${PROJECT_NAME}_PATCH_LEVEL 0)
set(VERSION ${${PROJECT_NAME}_MAJOR_VERSION}.${${PROJECT_NAME}_MINOR_VERSION}.${${PROJECT_NAME}_PATCH_LEVEL})
add_definitions(-DPACKAGE_VERSION="${VERSION}")

add_executable(dbus-proxy
	src/proxy.c
)

target_link_libraries(dbus-proxy
	${DEPENDENCIES_LIBRARIES}
)

install(TARGETS dbus-proxy RUNTIME DESTINATION bin)

