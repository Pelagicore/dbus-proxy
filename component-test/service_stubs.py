#!/usr/bin/env python

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


import gobject
import dbus
import dbus.service
import os

import conftest

from dbus.mainloop.glib import DBusGMainLoop
# Initialize a GLib main context used by the mainloop
DBusGMainLoop(set_as_default=True)


"""
    This is an example service that connects to the
    D-Bus session bus running on the system. It is used
    for testing purposes and represents a service running
    outside of a container.

    There are two objects exported on the same well-known bus name.
    The two objects are on separate object paths.
    There are two interfaces on each object path.
    The interfaces are built up in three parts in order to verify subsets.
    There are two methods on each interface.

    On the bus it all looks like this:

    /Object1
        com.service.TestInterface1._1
            Method1
        com.service.TestInterface1._1._2
            Method2
    /Object2
        com.service.TestInterface2._1
            Method1
        com.service.TestInterface2._1._2
            Method2
"""

DEBUG = False

# The test fixtures should set up the bus connection in normal cases
# and the exact path is kept there.
CONNECTION = "unix:path=" + conftest.OUTSIDE_SOCKET

# For development convenience this module can be run with
# the environments session bus if 'TESTMODE' is set. If run
# this way the debug printouts will be enabled as well.
if os.environ.get("TESTMODE") is not None:
    CONNECTION = os.environ.get("DBUS_SESSION_BUS_ADDRESS")
    DEBUG = True

# Define various strings that are used throughout tests and helpers
# to define the interfaces used etc. They are defined here to minimise
# ripple effects of changes in the stub service.
BUS_NAME = "com.service.TestService"

OPATH_1 = "/Object1"
OPATH_2 = "/Object2"

IFACE_1 = "com.service.TestInterface1"
IFACE_2 = "com.service.TestInterface2"

EXT_1 = "_1"
EXT_2 = "_2"

METHOD_1 = "Method1"
METHOD_2 = "Method2"


class TestService1(dbus.service.Object):
    """This D-Bus service exposes multiple interfaces on one
       object path.
    """
    def __init__(self, bus):
        self.__bus = bus
        name = dbus.service.BusName(BUS_NAME, bus=self.__bus)
        dbus.service.Object.__init__(self, name, OPATH_1)

    @dbus.service.method(IFACE_1 + "." + EXT_1,
                         in_signature="s", out_signature="s")
    def Method1(self, message):
        debug(IFACE_1 + "." + EXT_1 + ".Method1 " +
              "was called with message: \"" + message + "\"")
        return "Test said: \"" + message + "\""

    @dbus.service.method(IFACE_1 + "." + EXT_1 + "." + EXT_2,
                         in_signature="s", out_signature="s")
    def Method2(self, message):
        debug(IFACE_1 + "." + EXT_1 + "." + EXT_2 + ".Method2 " +
              "was called with message: \"" + message + "\"")
        return "Test said: \"" + message + "\""


class TestService2(dbus.service.Object):
    """This D-Bus service exposes multiple interfaces on one
       object path.
    """
    def __init__(self, bus):
        self.__bus = bus
        name = dbus.service.BusName(BUS_NAME, bus=self.__bus)
        dbus.service.Object.__init__(self, name, OPATH_2)

    @dbus.service.method(IFACE_2 + "." + EXT_1,
                         in_signature="s", out_signature="s")
    def Method1(self, message):
        debug(IFACE_2 + "." + EXT_1 + ".Method1 " +
              "was called with message: \"" + message + "\"")
        return "Test said: \"" + message + "\""

    @dbus.service.method(IFACE_2 + "." + EXT_1 + "." + EXT_2,
                         in_signature="s", out_signature="s")
    def Method2(self, message):
        debug(IFACE_2 + "." + EXT_1 + "." + EXT_2 + ".Method2 " +
              "was called with message: \"" + message + "\"")
        return "Test said: \"" + message + "\""


def debug(message):
    if DEBUG is True:
        print message


if __name__ == '__main__':
    bus = dbus.bus.BusConnection(CONNECTION)
    loop = gobject.MainLoop()
    service_1 = TestService1(bus)
    service_2 = TestService2(bus)
    loop.run()
