
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


import pytest

import os
from os import environ
import sys
import tempfile
from time import sleep
from subprocess import Popen, call, PIPE


""" Component test fixtures.

    This module makes the following assumptions:

    * py.test is invoked from the same directory as this module is located
    * start_outside_service.py is located in the same directory
    * dbus-proxy is found in a build/ directory one level above, i.e. "../build/dbus-proxy"
"""


OUTSIDE_SOCKET = "/tmp/dbus_proxy_outside_socket"
INSIDE_SOCKET = "/tmp/dbus_proxy_inside_socket"


# Setup an environment for the fixtures to share so the bus address is the same for all
environment = environ.copy()
environment["DBUS_SESSION_BUS_ADDRESS"] = "unix:path=" + OUTSIDE_SOCKET


@pytest.fixture(scope="function")
def session_bus(request):
    """ Create a session bus.

        The dbus-deamon will be torn down at the end of the test.
    """
    # TODO: Parametrize the socket path.

    dbus_daemon = None
    # The 'exec' part is a workaround to make the whole process group be killed
    # later when kill() is caled and not just the shell. This is only needed when
    # 'shell' is set to True like in the later Popen() call below.
    start_dbus_daemon_command = [
        "exec",
        " dbus-daemon",
        " --session",
        " --nofork",
        " --address=" + "unix:path=" + OUTSIDE_SOCKET
    ]
    try:
        # For some reason shell needs to be set to True, which is the reason the command
        # is passed as a string instead as an argument list, as recommended in the docs.
        dbus_daemon = Popen(
            "".join(start_dbus_daemon_command),
            env=environment,
            shell=True,
            stdout=sys.stdout)
        # Allow time for the bus daemon to start
        sleep(0.3)
    except OSError as e:
        print "Error starting dbus-daemon: " + str(e)
        sys.exit(1)

    def teardown():
        dbus_daemon.kill()
        os.remove(OUTSIDE_SOCKET)

    request.addfinalizer(teardown)


@pytest.fixture(scope="function")
def service_on_outside(request):
    """ Start the service on the "outside" as seen from the proxy.

        The service is torn down at the end of the test.
    """
    # TODO: Make it more robust w.r.t. where to find the service file.

    outside_service = None
    try:
        outside_service = Popen(
            [
                "python",
                "service_stubs.py"
            ],
            env=environment,
            stdout=sys.stdout)
        # Allow time for the service to show up on the bus before consuming tests
        # can try to use it.
        sleep(0.3)
    except OSError as e:
        print "Error starting service on outside: " + str(e)
        sys.exit(1)

    def teardown():
        outside_service.kill()

    request.addfinalizer(teardown)


@pytest.fixture(scope="function")
def dbus_proxy(request):
    """ Start dbus-proxy.

        The dbus-proxy is torn down at the end of the test.
    """
    # TODO: Make bus type parametrized so we can use the system bus as well.
    # TODO: Make path to dbus-proxy parametrized.

    dbus_proxy = None

    try:
        dbus_proxy = Popen(
            ["../build/dbus-proxy", INSIDE_SOCKET, "session"],
            env=environment,
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE)

    except OSError as e:
        print "Error starting dbus-proxy: " + str(e)
        sys.exit(1)

    def teardown():
        dbus_proxy.stdin.close()
        dbus_proxy.kill()
        os.remove(INSIDE_SOCKET)

    request.addfinalizer(teardown)

    return DBusProxyHelper(dbus_proxy)


class DBusProxyHelper(object):
    """ This helper is used by the tests to interact with dbus-proxy.

        Currently the only thing the tests needs/can do is to pass
        a configuration string to dbus-proxy.
    """

    def __init__(self, proxy_process):
        self.__proxy = proxy_process
        # Tests should get the socket paths from here
        self.INSIDE_SOCKET = "unix:path=" + INSIDE_SOCKET
        self.OUTSIDE_SOCKET = "unix:path=" + OUTSIDE_SOCKET

    def set_config(self, config):
        """ Write json config to dbus-proxy
        """
        # The way dbus-proxy expects data means that we can't have any newlines
        # in the config at any place except last, it has to be one non line broken
        # string ending in one newline.
        stripped_config = config.replace("\n", " ")
        self.__proxy.stdin.write(stripped_config + "\n")

        # Allow some time for the proxy to be setup before tests start using the
        # "inside" socket.
        sleep(0.3)
