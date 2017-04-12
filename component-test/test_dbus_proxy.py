
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


class TestWhitelisting(object):

    CONF_WHITELIST_DIRECTIONS = """
    {{
        "dbus-gateway-config-session": [{{
            "direction": "*",
            "interface": "*",
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

    CONF_WHITELIST_DIRECTIONS_REVERSE = """
    {{
        "dbus-gateway-config-session": [{{
            "direction": "outgoing",
            "interface": "{iface}.{extension_1}",
            "object-path": "*",
            "method": "*"
        }},
        {{
            "direction": "*",
            "interface": "*",
            "object-path": "*",
            "method": "*"
        }}],
        "dbus-gateway-config-system": []
    }}
    """.format(**{
        "iface": stubs.IFACE_1,
        "extension_1": stubs.EXT_1
    })

    CONF_WHITELIST_PATH = """
    {{
        "dbus-gateway-config-session": [{{
            "direction": "*",
            "interface": "*",
            "object-path": "*",
            "method": "*"
        }},
        {{
            "direction": "incoming",
            "interface": "{iface}.{extension_1}",
            "object-path": "/a/path/to/unavailable/directory/",
            "method": "*"
        }}],
        "dbus-gateway-config-system": []
    }}
    """.format(**{
        "iface": stubs.IFACE_1,
        "extension_1": stubs.EXT_1
    })

    CONF_WHITELIST_PATH_REVERSE = """
    {{
        "dbus-gateway-config-session": [{{
            "direction": "incoming",
            "interface": "{iface}.{extension_1}",
            "object-path": "/a/path/to/unavailable/directory/",
            "method": "*"
        }},
        {{
            "direction": "*",
            "interface": "*",
            "object-path": "*",
            "method": "*"
        }}],
        "dbus-gateway-config-system": []
    }}
    """.format(**{
        "iface": stubs.IFACE_1,
        "extension_1": stubs.EXT_1
    })

    CONF_WHITELIST_METHOD = """
    {{
        "dbus-gateway-config-session": [{{
            "direction": "*",
            "interface": "*",
            "object-path": "*",
            "method": "*"
        }},
        {{
            "direction": "incoming",
            "interface": "{iface}.{extension_1}",
            "object-path": "/a/path/to/unavailable/directory/",
            "method": "UnavailableMethod"
        }}],
        "dbus-gateway-config-system": []
    }}
    """.format(**{
        "iface": stubs.IFACE_1,
        "extension_1": stubs.EXT_1
    })

    CONF_WHITELIST_METHOD_REVERSE = """
    {{
        "dbus-gateway-config-session": [{{
            "direction": "incoming",
            "interface": "{iface}.{extension_1}",
            "object-path": "/a/path/to/unavailable/directory/",
            "method": "UnavailableMethod"
        }},
        {{
            "direction": "*",
            "interface": "*",
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
    CONF_WHITELIST_INTERFACE = """
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
    CONF_WHITELIST_INTERFACE_REVERSE = """
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

    @pytest.mark.parametrize("config", [
        CONF_WHITELIST_DIRECTIONS,
        CONF_WHITELIST_DIRECTIONS_REVERSE,
        CONF_WHITELIST_PATH,
        CONF_WHITELIST_PATH_REVERSE,
        CONF_WHITELIST_METHOD,
        CONF_WHITELIST_METHOD_REVERSE,
        CONF_WHITELIST_INTERFACE,
        CONF_WHITELIST_INTERFACE_REVERSE
    ])
    def test_whitelist(self, session_bus, service_on_outside, dbus_proxy, config):
        """ Assert that a configuration that has two rules for realted argument are applied
            according to white-listing policy which mandates the system to apply the
            most permissive directory rule.

            NOTE : Only applicable configuration chains will be considered and unapplicable
                   rules will be ignored. For instance while testing incoming queries,
                   the rule chains which have anything other than "incoming" or "*" for
                   directory will be ignored.
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


class TestProxyRobustness(object):

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

    CONF_RESTRICT_ALL = """
    {
        "some-ignored-attribute": "this-is-ignored",
        "dbus-gateway-config-session": [],
        "dbus-gateway-config-system": []
    }
    """

    def test_reconfiguration(self, session_bus, service_on_outside, dbus_proxy):
        """ Assert dbus-proxy can read configs more than once.

            The test sets a config more than once and asserts the configs
            have the expected effect, i.e. they are both applied.
        """
        environment = environ.copy()

        dbus_send_command = [
            "dbus-send",
            "--address=" + dbus_proxy.INSIDE_SOCKET,
            "--print-reply",
            "--dest=" + stubs.BUS_NAME,
            stubs.OPATH_1,
            stubs.IFACE_1 + "." + stubs.EXT_1 + "." + stubs.METHOD_1,
            'string:"My unique key"']

        # Configure with a restrictive config, try to call a method and assert
        # it fails.
        dbus_proxy.set_config(TestProxyRobustness.CONF_RESTRICT_ALL)

        sleep(0.3)

        dbus_send_process = Popen(dbus_send_command,
                                  env=environment,
                                  stdout=PIPE)
        captured_stdout = dbus_send_process.communicate()[0]
        assert "My unique key" not in captured_stdout

        # Re-configure with a permissive config, try to call a method and assert
        # it works.
        dbus_proxy.set_config(TestProxyRobustness.CONF_ALLOW_ALL)

        sleep(0.3)

        dbus_send_process = Popen(dbus_send_command,
                                  env=environment,
                                  stdout=PIPE)
        captured_stdout = dbus_send_process.communicate()[0]
        assert "My unique key" in captured_stdout

    @pytest.mark.parametrize("config", [CONF_ALLOW_ALL])
    def test_proxy_handles_many_calls(self, session_bus, service_on_outside, dbus_proxy, config):
        """ Assert dbus-proxy doesn't crash due to fd and zombie process leaks.

            The history behind this test is that there was a bug reported that
            dbus-proxy always crashed after 544 calls on D-Bus.

            Test steps:
              * Configure dbus-proxy.
              * Call a method on D-Bus from "inside".
              * Assert the method call can be performed 1024 times, i.e.
                dbus-proxy didn't crash.

        """
        dbus_proxy.set_config(config)

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

    @pytest.mark.parametrize("config", [CONF_RESTRICT_ALL])
    def test_proxy_does_not_stop_external_messages_on_eavesdrop(self,
                                                                session_bus,
                                                                service_on_outside,
                                                                dbus_proxy,
                                                                config):
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
        dbus_proxy.set_config(config)

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

    @pytest.mark.parametrize("config", [CONF_RESTRICT_ALL])
    @pytest.mark.skipif(1, reason="See comment")
    def test_proxy_incoming_message(self, session_bus, service_on_outside, dbus_proxy, config):
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
        dbus_proxy.set_config(config)

        bus = dbus.bus.BusConnection(dbus_proxy.INSIDE_SOCKET)
        inside_object = DBusRemoteObjectHelper(bus, stubs.BUS_NAME)
        inside_object.call_hello_world()
        assert "My unique key" in inside_object.get_response()[0]


class TestProxyFiltersInterface(object):
    """ TODO: Parametrize the tests for testing allowed/disallowed?
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

    @pytest.mark.parametrize("config", [
        CONF_ALLOW_ALL_OUTGOING_METHODS_ON_IFACE
    ])
    def test_allowed_iface_is_accessible(self,
                                         session_bus,
                                         service_on_outside,
                                         dbus_proxy,
                                         config):
        """ Assert that a call to a method on an allowed interface is allowed.
        """
        dbus_proxy.set_config(config)

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

    @pytest.mark.parametrize("config", [
        CONF_ALLOW_ALL_OUTGOING_METHODS_ON_IFACE
    ])
    def test_disallowed_iface_is_not_accessible(self,
                                                session_bus,
                                                service_on_outside,
                                                dbus_proxy,
                                                config):
        """ Assert that a configuration that allows one interface disallows
            calls to other interfaces. The called interface and method exist
            on the bus, i.e. the call would be valid without the proxy running.

            NOTE: This test will "pass" if there is nothing on the bus as well,
                  i.e. if no service is running.
        """
        dbus_proxy.set_config(config)

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


class TestProxyMethods(object):
    """ This class tests method configurations. There are two ways of setting methods
        a string or an array of string representing methods.
    """

    CONF_SINGLE_METHOD = """
    {
        "dbus-gateway-config-session": [{
            "direction": "*",
            "interface": "*",
            "object-path": "*",
            "method": "Method2"
        }],
        "dbus-gateway-config-system": []
    }
    """

    CONF_ALL_METHODS = """
    {
        "dbus-gateway-config-session": [{
            "direction": "*",
            "interface": "*",
            "object-path": "*",
            "method": "*"
        }],
        "dbus-gateway-config-system": []
    }
    """

    CONF_FOUR_METHODS = """
    {
        "dbus-gateway-config-session": [{
            "direction": "*",
            "interface": "*",
            "object-path": "*",
            "method": ["Method1", "Method3", "Method4", "Method2"]
        }],
        "dbus-gateway-config-system": []
    }
    """

    @pytest.mark.parametrize("config", [
        CONF_SINGLE_METHOD,
        CONF_ALL_METHODS,
        CONF_FOUR_METHODS
    ])
    def test_methods(self, session_bus, service_on_outside, dbus_proxy, config):
        """ This method is stands for testing process of method argument in configuration
            to be ensure whether code can filter the method on following occasions :
            * when one exact method name is provided (i.e CONF_SINGLE_METHOD)
            * when wildcard character is used (i.e. CONF_ALL_METHODS)
            * when an array of methods is provided (i.e CONF_FOUR_METHODS)
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

    METHOD_ON_TOP = """
    {
        "dbus-gateway-config-session": [{
            "direction": "*",
            "interface": "*",
            "object-path": "*",
            "method": ["Method2", "Method3", "Method1", "Method4"]
        }],
        "dbus-gateway-config-system": []
    }
    """

    METHOD_ON_BOTTOM = """
    {
        "dbus-gateway-config-session": [{
            "direction": "*",
            "interface": "*",
            "object-path": "*",
            "method": ["Method4", "Method3", "Method1", "Method2"]
        }],
        "dbus-gateway-config-system": []
    }
    """

    METHOD_IN_THE_MIDDLE = """
    {
        "dbus-gateway-config-session": [{
            "direction": "*",
            "interface": "*",
            "object-path": "*",
            "method": ["Method4", "Method2", "Method1", "Method3"]
        }],
        "dbus-gateway-config-system": []
    }
    """

    @pytest.mark.parametrize("config", [
        METHOD_ON_TOP,
        METHOD_ON_BOTTOM,
        METHOD_IN_THE_MIDDLE
    ])
    def test_method_order(self, session_bus, service_on_outside, dbus_proxy, config):
        """ This method is for testing order of the method in a list form
            It is ecpected that the order of the method in the list does not matter
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

    CONF_AVAILABLE_METHODS = """
    {
        "dbus-gateway-config-session": [{
            "direction": "*",
            "interface": "*",
            "object-path": "*",
            "method": ["Method1", "Method2"]
        }],
        "dbus-gateway-config-system": []
    }
    """

    @pytest.mark.parametrize("config", [CONF_AVAILABLE_METHODS])
    def test_all_available_methods(self, session_bus, service_on_outside, dbus_proxy, config):
        """ This method is for testing all available methods in a list form
        """

        dbus_proxy.set_config(config)

        def dbus_process(interface, message):
            dbus_send_command = [
                "dbus-send",
                "--address=" + dbus_proxy.INSIDE_SOCKET,
                "--print-reply",
                "--dest=" + stubs.BUS_NAME,
                stubs.OPATH_1,
                interface,
                message]

            environment = environ.copy()
            dbus_send_process = Popen(dbus_send_command,
                                      env=environment,
                                      stdout=PIPE)
            captured_stdout = dbus_send_process.communicate()[0]
            return captured_stdout

        assert "My unique key 2" in dbus_process(stubs.IFACE_1 + "." + stubs.EXT_1 + "." + stubs.EXT_2 + "." + stubs.METHOD_2,
                                                 'string:"My unique key 2"')

        assert "My unique key 1" in dbus_process(stubs.IFACE_1 + "." + stubs.EXT_1 + "." + stubs.METHOD_1,
                                                 'string:"My unique key 1"')


class TestProxyFiltersOpath(object):
    """ some comment here
    """

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

    @pytest.mark.parametrize("config, opath, iface, expected", [(CONF_ALLOW_ALL_ON_SPECIFIC_OPATH,
                                                                stubs.OPATH_1,
                                                                stubs.IFACE_1,
                                                                True),
                                                                (CONF_ALLOW_ALL_ON_SPECIFIC_OPATH,
                                                                stubs.OPATH_2,
                                                                stubs.IFACE_2,
                                                                False)])
    def test_diallowed_opath_accessibilty(self,
                                          session_bus,
                                          service_on_outside,
                                          dbus_proxy,
                                          config,
                                          opath,
                                          iface,
                                          expected):
        """ Assert calls on disallowed object path are not accepted.
        """

        dbus_proxy.set_config(config)

        dbus_send_command = [
            "dbus-send",
            "--address=" + dbus_proxy.INSIDE_SOCKET,
            "--print-reply",
            "--dest=" + stubs.BUS_NAME,
            opath,
            iface + "." + stubs.EXT_1 + "." + stubs.METHOD_1,
            'string:"My unique key"']

        environment = environ.copy()
        dbus_send_process = Popen(dbus_send_command,
                                  env=environment,
                                  stdout=PIPE)
        captured_stdout = dbus_send_process.communicate()[0]
        assert ("My unique key" in captured_stdout) == expected


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
