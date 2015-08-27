import pytest

"""
    Tests various aspects of the D-Bus proxy. Depending on the test case, the
    test may act as a service running outside of the container or an app
    running on the inside.

    The tests in this module requries that the D-Bus proxy is started with a
    permit all configuration for the session bus. E.g.:

    {
        "some-ignored-attribute": "this-is-ignored",
        "dbus-gateway-config-session": [
                 {
                    "direction": "*",
                    "interface": "*",
                    "object-path": "*",
                    "method": "*"
                 }],
        "dbus-gateway-config-system": []
    }
"""


class TestDBusProxyPermits(object):
    """
        According to https://atlassian.pelagicore.net/jira/browse/TAC-58, the
        D-Bus proxy had fd leaks and zombie processes making it crash after 544
        calls. Using dbus-send command, this test attempts to call a D-Bus
        service running outside the container. The test represents an app
        running on the inside.
        The test will send 1024 messages to a D-Bus proxy test service.

        Configuration to use: conf_allow_all.json
    """
    def test_dbus_send_command(self):
        from os import environ
        from subprocess import Popen, PIPE

        DBUS_SEND_CMD = ["dbus-send",
                         "--address=unix:path=/tmp/dbus_proxy_inside_socket",
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
