#!/usr/bin/env python

import dbus
import dbus.service

"""
    This is an example service that connects to the
    D-Bus session bus running on the system. It is used
    for testing purposes and represents a service running
    outside of a container.
"""


class SomeObject(dbus.service.Object):
    def __init__(self):
        # Connect to the D-Bus session bus running outside the container
        self.__bus = dbus.bus.BusConnection('unix:path=/tmp/dbus_proxy_outside_socket')
        name = dbus.service.BusName("com.dbusproxyoutsideservice.SampleService",
                                    bus=self.__bus)
        dbus.service.Object.__init__(self, name, '/SomeObject')

    @dbus.service.method("com.dbusproxyoutsideservice.SampleInterface",
                         in_signature='s', out_signature='as')
    def HelloWorld(self, hello_message):
        return ["Hello", "from unique name", self.__bus.get_unique_name()]

    @dbus.service.method("com.dbusproxyoutsideservice.SampleInterface",
                         in_signature='', out_signature='')
    def Exit(self):
        mainloop.quit()

if __name__ == '__main__':
    # using glib
    import dbus.mainloop.glib
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    import gobject
    loop = gobject.MainLoop()
    object = SomeObject()
    loop.run()
