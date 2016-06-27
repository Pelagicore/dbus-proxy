
""" Copyright (c) 2016 Pelagicore AB """


import pytest

from os import environ
from subprocess import Popen, PIPE
from time import sleep

import service_stubs as stubs


"""
    Tests various aspects of the D-Bus proxy. Depending on the test case, the
    test may act as a service running outside of the container or an app
    running on the inside.

    The tests in this module requries that the D-Bus proxy is started with a
    permit all configuration for the session bus.

    dbus-proxy configurations used for testing are defined as strings. The pattern
    is to use format strings and substitute exact details about e.g. interface names
    by using imported definitions from the setup/helper modules.
"""


CONF_RESTRICT_ALL = """
{
    "some-ignored-attribute": "this-is-ignored",
    "dbus-gateway-config-session": [],
    "dbus-gateway-config-system": []
}
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

CONF_ALLOW_ALL_OUTGOING_METHODS_ON_IFACE = """
{{
    "dbus-gateway-config-session": [{{
        "direction": "outgoing",
        "interface": "{iface}.{extension_1}",
        "object-path": "*",
        "method": "*"
    }}],
    "dbus-gateway-config-system": []
}}
""".format(**{
    "iface": stubs.IFACE_1,
    "extension_1": stubs.EXT_1
})


""" Allowed interfaces are set to two different values
    where one is more permissive than the first.

    The rules below says:

    * Allow com.service.TestInterface1.*
          (which matches:)
        * com.service.TestInterface1._1
        * com.service.TestInterface1._1._2

    * Allow com.service.TestInterface1._1

    The last rule alone would not allow "com.service.TestInterface1._1._2".
"""
CONF_CONTRADICTING_RULES = """
{{
    "dbus-gateway-config-session": [{{
        "direction": "outgoing",
        "interface": "{iface}.*",
        "object-path": "*",
        "method": "*"
    }},
    {{
        "direction": "outgoing",
        "interface": "{iface}.{extension_1}",
        "object-path": "*",
        "method": "*"
    }}],
    "dbus-gateway-config-system": []
}}
""".format(**{
    "iface": stubs.IFACE_1,
    "extension_1": stubs.EXT_1
})


""" Same as CONF_CONTRADICTING_RULES but a different order of the rules.
    This is used to verify that the ordering of rules does not affect the
    behavior.
"""
CONF_CONTRADICTING_RULES_DIFFERENT_ORDER = """
{{
    "dbus-gateway-config-session": [{{
        "direction": "outgoing",
        "interface": "{iface}.{extension_1}",
        "object-path": "*",
        "method": "*"
    }},
    {{
        "direction": "outgoing",
        "interface": "{iface}.*",
        "object-path": "*",
        "method": "*"
    }}],
    "dbus-gateway-config-system": []
}}
""".format(**{
    "iface": stubs.IFACE_1,
    "extension_1": stubs.EXT_1
})


CONF_ALLOW_ALL_ON_SPECIFIC_OPATH = """
{{
    "dbus-gateway-config-session": [{{
        "direction": "*",
        "interface": "*",
        "object-path": "{opath_1}",
        "method": "*"
    }}],
    "dbus-gateway-config-system": []
}}
""".format(**{
    "opath_1": stubs.OPATH_1
})


class TestProxyRobustness(object):

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

        dbus_send_command = [
            "dbus-send",
            "--address=" + dbus_proxy.INSIDE_SOCKET,
            "--print-reply",
            "--dest=" + stubs.BUS_NAME,
            stubs.OPATH_1,
            stubs.IFACE_1 + "." + stubs.EXT_1 + "." + stubs.METHOD_1,
            'string:"My unique key"']

        environment = environ.copy()
        for _x in range(0, 1024):
            dbus_send_process = Popen(dbus_send_command,
                                      env=environment,
                                      stdout=PIPE)
            captured_stdout = dbus_send_process.communicate()[0]
            assert "My unique key" in captured_stdout


    def test_proxy_does_not_stop_external_messages_on_eavesdrop(self,
                                                                session_bus,
                                                                service_on_outside,
                                                                dbus_proxy):
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
        dbus_proxy.set_config(CONF_RESTRICT_ALL)

        DBUS_MONITOR_CMD = ["dbus-monitor",
                            "--address",
                            dbus_proxy.INSIDE_SOCKET]

        DBUS_SEND_CMD = ["dbus-send",
                         "--session",
                         "--print-reply",
                         '--dest=' + stubs.BUS_NAME,
                         stubs.OPATH_1,
                         stubs.IFACE_1 + "." + stubs.EXT_1 + "." + stubs.METHOD_1,
                         'string:"My unique key"']

        # Prepare environment for dbus-monitor and start it
        dbus_monitor_environment = environ.copy()
        dbus_monitor_environment["DBUS_SESSION_BUS_ADDRESS"] = dbus_proxy.INSIDE_SOCKET
        dbus_monitor_process = Popen(DBUS_MONITOR_CMD,
                                     env=dbus_monitor_environment,
                                     stdout=PIPE)
        sleep(0.3)

        # Prepare environment for dbus-send and send the message
        dbus_send_environment = environ.copy()
        dbus_send_environment["DBUS_SESSION_BUS_ADDRESS"] = dbus_proxy.OUTSIDE_SOCKET
        dbus_send_process = Popen(DBUS_SEND_CMD,
                                  env=dbus_send_environment,
                                  stdout=PIPE)
        captured_stdout = dbus_send_process.communicate()[0]

        # Kill the dbus-monitor
        sleep(0.3)
        dbus_monitor_process.kill()

        assert "My unique key" in captured_stdout

    @pytest.mark.skipif(1, reason="See comment")
    def test_proxy_incoming_message(self, session_bus, service_on_outside, dbus_proxy):
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
        dbus_proxy.set_config(CONF_RESTRICT_ALL)

        bus = dbus.bus.BusConnection(dbus_proxy.INSIDE_SOCKET)
        inside_object = DBusRemoteObjectHelper(bus, stubs.BUS_NAME)
        inside_object.call_hello_world()
        assert "My unique key" in inside_object.get_response()[0]


class TestProxyFiltersInterface(object):
    """ TODO: Parametrize the tests for testing allowed/disallowed?
    """

    def test_allowed_iface_is_accessible(self, session_bus, service_on_outside, dbus_proxy):
        """ Assert that a call to a method on an allowed interface is allowed.
        """
        dbus_proxy.set_config(CONF_ALLOW_ALL_OUTGOING_METHODS_ON_IFACE)

        dbus_send_command = [
            "dbus-send",
            "--address=" + dbus_proxy.INSIDE_SOCKET,
            "--print-reply",
            "--dest=" + stubs.BUS_NAME,
            stubs.OPATH_1,
            stubs.IFACE_1 + "." + stubs.EXT_1 + "." + stubs.METHOD_1,
            'string:"My unique key"']

        environment = environ.copy()
        dbus_send_process = Popen(dbus_send_command,
                                  env=environment,
                                  stdout=PIPE)
        captured_stdout = dbus_send_process.communicate()[0]
        assert "My unique key" in captured_stdout

    def test_disallowed_iface_is_not_accessible(self, session_bus, service_on_outside, dbus_proxy):
        """ Assert that a configuration that allows one interface disallows
            calls to other interfaces. The called interface and method exist
            on the bus, i.e. the call would be valid without the proxy running.

            NOTE: This test will "pass" if there is nothing on the bus as well,
                  i.e. if no service is running.
        """
        dbus_proxy.set_config(CONF_ALLOW_ALL_OUTGOING_METHODS_ON_IFACE)

        dbus_send_command = [
            "dbus-send",
            "--address=" + dbus_proxy.INSIDE_SOCKET,
            "--print-reply",
            "--dest=" + stubs.BUS_NAME,
            stubs.OPATH_1,
            stubs.IFACE_1 + "." + stubs.EXT_2 + "." + stubs.METHOD_2,
            'string:"My unique key"']

        environment = environ.copy()
        dbus_send_process = Popen(dbus_send_command,
                                  env=environment,
                                  stdout=PIPE)
        captured_stdout = dbus_send_process.communicate()[0]
        assert "My unique key" not in captured_stdout

    @pytest.mark.parametrize("config", [
        CONF_CONTRADICTING_RULES,
        CONF_CONTRADICTING_RULES_DIFFERENT_ORDER
    ])
    def test_contradicting_iface_rules(self, session_bus, service_on_outside, dbus_proxy, config):
        """ Assert that a configuration that has two contradicting rules for
            interfaces works as expected. One rule is more permissive than the
            other.

            This test also asserts that the order of rules does not affect the behavior,
            i.e. the results are the same even if the more restrictive rule comes first or last
            in the configuration passed to the proxy.

            NOTE: The proxy behavior here is perhaps not correct. The most permissive rule
                  will always trump any less permissive rules. The jury is out on
                  what the exact desired behavior is.
        """
        dbus_proxy.set_config(config)

        dbus_send_command = [
            "dbus-send",
            "--address=" + dbus_proxy.INSIDE_SOCKET,
            "--print-reply",
            "--dest=" + stubs.BUS_NAME,
            stubs.OPATH_1,
            stubs.IFACE_1 + "." + stubs.EXT_1 + "." + stubs.EXT_2 + "." + stubs.METHOD_2,
            'string:"My unique key"']

        environment = environ.copy()
        dbus_send_process = Popen(dbus_send_command,
                                  env=environment,
                                  stdout=PIPE)
        captured_stdout = dbus_send_process.communicate()[0]
        assert "My unique key" in captured_stdout


class TestProxyFiltersOpath(object):
    """
    """

    def test_allowed_opath_is_accessible(self, session_bus, service_on_outside, dbus_proxy):
        """ Assert calls on allowed object path are accepted.
        """
        dbus_proxy.set_config(CONF_ALLOW_ALL_ON_SPECIFIC_OPATH)

        dbus_send_command = [
            "dbus-send",
            "--address=" + dbus_proxy.INSIDE_SOCKET,
            "--print-reply",
            "--dest=" + stubs.BUS_NAME,
            stubs.OPATH_1,
            stubs.IFACE_1 + "." + stubs.EXT_1 + "." + stubs.METHOD_1,
            'string:"My unique key"']

        environment = environ.copy()
        dbus_send_process = Popen(dbus_send_command,
                                  env=environment,
                                  stdout=PIPE)
        captured_stdout = dbus_send_process.communicate()[0]
        assert "My unique key" in captured_stdout

    def test_diallowed_opath_is_not_accessible(self, session_bus, service_on_outside, dbus_proxy):
        """ Assert calls on disallowed object path are not accepted.
        """
        dbus_proxy.set_config(CONF_ALLOW_ALL_ON_SPECIFIC_OPATH)

        dbus_send_command = [
            "dbus-send",
            "--address=" + dbus_proxy.INSIDE_SOCKET,
            "--print-reply",
            "--dest=" + stubs.BUS_NAME,
            stubs.OPATH_2,
            stubs.IFACE_2 + "." + stubs.EXT_1 + "." + stubs.METHOD_1,
            'string:"My unique key"']

        environment = environ.copy()
        dbus_send_process = Popen(dbus_send_command,
                                  env=environment,
                                  stdout=PIPE)
        captured_stdout = dbus_send_process.communicate()[0]
        assert "My unique key" not in captured_stdout


class DBusRemoteObjectHelper(object):
    """ Helper class representing an app running on the inside of the proxy.
    """

    def __init__(self, bus, connection_name):
        self.__bus = bus
        self.__connection_name = connection_name
        self.__remote_object = self.__bus.get_object(self.__connection_name,
                                                     stubs.OPATH_1)

    def call_hello_world(self):
        self.__response = self.__remote_object.HelloWorld("My unique key")

    def get_response(self):
        return self.__response
