
""" Copyright (c) 2016 Pelagicore AB """


import pytest

from os import environ
from subprocess import Popen, PIPE


"""
    Tests various aspects of the D-Bus proxy. Depending on the test case, the
    test may act as a service running outside of the container or an app
    running on the inside.

    The tests in this module requries that the D-Bus proxy is started with a
    permit all configuration for the session bus.
"""


CONF_ALLOW_ALL = """
{
    "some-ignored-attribute": "this-is-ignored",
    "dbus-gateway-config-session": [{
        "direction": "*",
        "interface": "*",
        "object-path": "*",
        "method": "*"
    }],
    "dbus-gateway-config-system": []
}
"""


class TestDBusProxyPermits(object):

    def test_proxy_handles_many_calls(self, session_bus, service_on_outside, dbus_proxy):
        """ Assert dbus-proxy doesn't crash due to fd and zombie process leaks.

            The history behind this test is that there was a bug reported that
            dbus-proxy always crashed after 544 calls on D-Bus.

            Test steps:
              * Configure dbus-proxy.
              * Call a method on D-Bus from "inside".
              * Assert the method call can be performed 1024 times, i.e.
                dbus-proxy didn't crash.

        """
        dbus_proxy.set_config(CONF_ALLOW_ALL)

        DBUS_SEND_CMD = ["dbus-send",
                         "--address=" + dbus_proxy.INSIDE_SOCKET,
                         "--print-reply",
                         '--dest=com.dbusproxyoutsideservice.SampleService',
                         "/SomeObject",
                         "com.dbusproxyoutsideservice.SampleInterface.HelloWorld",
                         'string:"Test says hello"']

        environment = environ.copy()
        for _x in range(0, 1024):
            dbus_send_process = Popen(DBUS_SEND_CMD,
                                      env=environment,
                                      stdout=PIPE)
            captured_stdout = dbus_send_process.communicate()[0]
            assert "Hello" in captured_stdout
