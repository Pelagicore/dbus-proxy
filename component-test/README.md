
Component tests
===============

These tests are executed with `dbus-proxy` running as a separate process. The tests are
run and driven using `py.test`.


Installing pytest
=================

    sudo apt-get install pip
    sudo pip install pytest


Test setup
==========

The tests requires that:

 * A D-Bus session bus socket exists on a specific location.
 * A stubbed service is running on the "outside" of dbus-proxy, as seen from dbus-proxy.

All of the above prerequisites are setup by the test helpers.


Running the tests
=================

Tests are executed with `py.test`, e.g. like this:

    py.test -v -s
