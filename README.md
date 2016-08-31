
dbus-proxy
------------------------------------------
`dbus-proxy` acts as a proxy for the D-Bus connection for a client.
It can be configured to filter what is accessible for the client on the
connection.


Dependencies
============
`dbus-proxy` depends on GLib D-Bus development libraries and jansson for JSON parsing.

E.g. for Ubuntu, you will need the libdbus-glib-1-dev and libjansson-dev package installed


Configuring and building
=========================
In the root of the project, run:

```
$ cmake -H. -Bbuild
$ cd build
$ make
$ make install
```

Running
=======
`dbus-proxy` is invoked like so:

    ./dbus-proxy /tmp/my_proxy_socket bus-type < example-configs/example_conf.json

Where:

* `/tmp/my_proxy_socket` is the socket to create for communication, i.e. "the bus".
* `bus-type` should be set to either `session` or `system`.
* `example-configs/example_conf.json` is the configuration file to use.

You can then interact with the socket via, for instance D-Feet or dbus-send.


Configuration files
===================
`dbus-proxy` is configured using JSON files.

The content of the JSON file can vary as long as the "dbus-gateway-config-<bustype>"
attribute holds a JSON array of JSON objects with certain name/value pairs,
`example-configs/example_conf.json` shows an example of how the JSON configuration files should be
structured.

A note on 'direction' in the configuration:
The values used for direction is 'outgoing' and 'incoming'. One way to picture it
is to consider anything connecting to the bus specified when starting dbus-proxy
as being on the 'inside' and thus any interaction with the bus specified when
starting dbus-proxy is 'outgoing'.


A word on eavesdropping connections
===================================
In `dbus-proxy`, eavesdropping connections such as the dbus-monitor will be
ignored. That is, if an eavesdropping connection receives a message, the proxy
will not consider the message to have been handled yet.

Allowing eavesdropping is considered a system configuration and is done in the
D-Bus configuration files, usually located in either /etc/dbus-1/session.conf
or in configuration include files in /etc/dbus-1/session.d/.


Testing
=======
Component tests are found in `component-test`, please see README.md in that directory
for further details


Copyright and license
=====================
* Copyright (C) 2013-2016, Pelagicore AB  <joakim.gross@pelagicore.com>
* Copyright (C) 2011, Stéphane Graber (Arkose project modifications)  <stgraber@stgraber.org>
* Copyright (C) 2010, Alban Crequy (Initial single threaded proxy)  <alban.crequy@collabora.co.uk>

The source code in this repository is subject to the terms of the LGPL-2.1 licence
