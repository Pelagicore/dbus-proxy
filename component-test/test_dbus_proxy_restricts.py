import pytest
import dbus

OUTSIDE_CONNECTION_NAME = "com.dbusproxyoutsideservice.SampleService"
INSIDE_CONNECTION_NAME = "com.dbusproxyinsideservice.SampleService"
DBUS_OBJECT_PATH = "/SomeObject"
OUTSIDE_SOCKET = "unix:path=/tmp/dbus_proxy_outside_socket"
INSIDE_SOCKET = "unix:path=/tmp/dbus_proxy_inside_socket"

"""
    Tests various aspects of the D-Bus proxy. Depending on the test case, the
    test may act as a service running outside of the container or an app
    running on the inside.

    The tests in this module requries that the D-Bus proxy is started with a
    restrict all configuration for the session bus. E.g.:

    {
        "some-ignored-attribute": "this-is-ignored",
        "dbus-gateway-config-session": [],
        "dbus-gateway-config-system": []
    }

"""


class TestDBusProxyRestricts(object):
    """
        When configured for allowing eavesdropping, eavesdropping D-Bus
        connections such as the dbus-monitor interrupts the messages passed
        between outside services (i.e. servers and clients both residing
        outside of the container).

        The expected outcome of this test case is that the message sent from
        the dbus-send command should result in a proper reply even though the
        D-Bus proxy is set to restrict all (because the D-Bus proxy should not
        intercept messages sent between clients and servers both running
        outside of the container.

        The problem only exists when D-Bus is started with eavesdropping
        allowed. If the system is not configured for allowing eavesdropping,
        the test will result in a false pass.
    """
    def test_proxy_hogs_external_messages_when_monitor_is_running(self):
        from os import environ
        from subprocess import Popen, PIPE
        from time import sleep

        DBUS_MONITOR_CMD = ["dbus-monitor",
                            "--address",
                            INSIDE_SOCKET]

        DBUS_SEND_CMD = ["dbus-send",
                         "--session",
                         "--print-reply",
                         '--dest=' + OUTSIDE_CONNECTION_NAME,
                         DBUS_OBJECT_PATH,
                         "com.dbusproxyoutsideservice.SampleInterface.HelloWorld",
                         'string:"Test says hello"']

        # Prepare environment for dbus-monitor and start it
        dbus_monitor_environment = environ.copy()
        dbus_monitor_environment["DBUS_SESSION_BUS_ADDRESS"] = INSIDE_SOCKET
        dbus_monitor_process = Popen(DBUS_MONITOR_CMD,
                                     env=dbus_monitor_environment,
                                     stdout=PIPE)
        sleep(1)

        # Prepare environment for dbus-send and send the message
        dbus_send_environment = environ.copy()
        dbus_send_environment["DBUS_SESSION_BUS_ADDRESS"] = OUTSIDE_SOCKET
        dbus_send_process = Popen(DBUS_SEND_CMD,
                                  env=dbus_send_environment,
                                  stdout=PIPE)
        captured_stdout = dbus_send_process.communicate()[0]

        # Kill the dbus-monitor
        sleep(1)
        dbus_monitor_process.kill()

        assert "Hello" in captured_stdout

    """
        This test does not behave as it should. The proxy rejects the
        introspection message but lets the HelloWorld-call through. The
        problem seems to be present only when using the python D-Bus lib.
        Introspect is called before any methods are actually called.

        The DBusRemoteObjectHelper created represents an app running on the
        inside, calling a method on a session bus service running on the
        outside. Expected behavior is that the HelloWorld message is rejected
        by the proxy.
    """
    @pytest.mark.skipif(1, reason="See comment")
    def test_proxy_incoming_message(self):
        bus = dbus.bus.BusConnection(INSIDE_SOCKET)
        inside_object = DBusRemoteObjectHelper(bus,
                                               OUTSIDE_CONNECTION_NAME)
        inside_object.call_hello_world()
        assert inside_object.get_response()[0] == "Hello"


class DBusRemoteObjectHelper(object):
    def __init__(self, bus, connection_name):
        self.__bus = bus
        self.__connection_name = connection_name
        self.__remote_object = self.__bus.get_object(self.__connection_name,
                                                     DBUS_OBJECT_PATH)

    def call_hello_world(self):
        self.__response = self.__remote_object.HelloWorld("Test says hello")

    def get_response(self):
        return self.__response
