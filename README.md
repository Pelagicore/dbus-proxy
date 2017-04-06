
dbus-proxy
==========
`dbus-proxy` acts as a proxy for the D-Bus connection for a client.
It can be configured to filter what is accessible for the client on the
connection.

Maintained at: https://github.com/Pelagicore/dbus-proxy


Dependencies
------------
`dbus-proxy` depends on GLib D-Bus development libraries and jansson for JSON parsing.

E.g. for Ubuntu, you will need the libdbus-glib-1-dev and libjansson-dev package installed


Configuring and building
------------------------
In the root of the project, run:

```
$ cmake -H. -Bbuild
$ cd build
$ make
$ make install
```

The following cmake options are available:

* `ENABLE_LOG_TO_FILE` - makes `dbus-proxy` log to "/tmp/dbus-proxy.log"
* `ENABLE_LOG_TO_STDOUT` - makes `dbus-proxy` log to stdout/stderr

Both options will default to OFF, and logging to stdout will take precedence
over logging to file if both are enabled.

Please note that the `ENABLE_LOG_TO_*` options should not be used in other
contexts than troubleshooting and debugging. It's not suitable for production
builds and the component tests are not expected to work when built with these
options.

### Building in Vagrant
For some purposes it is convenient to build in a virtual machine, e.g. in order to
have a consistent environment, integration into CI systems etc. `dbus-proxy` comes
prepared for this, see __Testing__ for details.


Running
-------
`dbus-proxy` is invoked like so:

    ./dbus-proxy /tmp/my_proxy_socket bus-type < example-configs/example_conf.json

Where:

* `/tmp/my_proxy_socket` is the socket to create for communication, i.e. "the bus".
* `bus-type` should be set to either `session` or `system`.
* `example-configs/example_conf.json` is the configuration file to use.

You can then interact with the socket via, for instance D-Feet or dbus-send.


Configuration files
-------------------
Please note that the below description is for when running `dbus-proxy` manually,
when it might be convenient to redirect a file with the config. Generally `dbus-proxy`
is meant to be spawned by another process that writes to stdin of `dbus-proxy`. When
a file is redirected, the content must be one line with no newline characters apart
from the last character which needs to be a newline.

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

A note on 'method' in the configuration:
Method can be either a string or list of strings. This behavior is useful when user wants from proxy
to use many methods but not all of them.

When a D-Bus message is sent, the `dbus-proxy` compares message's direction, interface, path and method
with configuration list. if a matching rule is found, the message is allowed to forward and otherwise it
is dropped.


A word on eavesdropping connections
-----------------------------------
In `dbus-proxy`, eavesdropping connections such as the dbus-monitor will be
ignored. That is, if an eavesdropping connection receives a message, the proxy
will not consider the message to have been handled yet.

Allowing eavesdropping is considered a system configuration and is done in the
D-Bus configuration files, usually located in either /etc/dbus-1/session.conf
or in configuration include files in /etc/dbus-1/session.d/.


Testing
-------
Component tests are found in `component-test`, please see README.md in that directory
for further details about the tests structure etc.

### Running tests in virtual machine
For convenience (under some circumstances) there is support for running the component tests
in a virtual machine using Vagrant:

```
git submodule init
git submodule update

sudo apt-get install virtualbox
sudo apt-get install vagrant

vagrant up
```

Test results should be found in `component-test/component-test-results.xml`. The format is
junit xml.

Resolving dependencies and making virtualbox work on your system varies in how it's done
of course. Some systems need to disable safe boot for example.

Versioning
----------
We use [semantic versioning](http://semver.org).


Copyright and license
---------------------
* Copyright (C) 2013-2016, Pelagicore AB  <joakim.gross@pelagicore.com>
* Copyright (C) 2011, Stéphane Graber (Arkose project modifications)  <stgraber@stgraber.org>
* Copyright (C) 2010, Alban Crequy (Initial single threaded proxy)  <alban.crequy@collabora.co.uk>

The source code in this repository is subject to the terms of the LGPL-2.1 licence
