
Component tests
===============

These tests are executed with `dbus-proxy` running as a separate process. The tests are
run and driven using `py.test`.


Installing pytest
=================

    sudo apt-get install python-pip
    sudo pip install pytest


Test setup
==========

The tests assume the `dbus-proxy` binary is located in a directory named `build`
one level above the `component-test` directory.

The tests requires that:

 * A D-Bus session bus socket exists on a specific location.
 * A stubbed service is running on the "outside" of dbus-proxy, as seen from dbus-proxy.

All of the above prerequisites are setup by the test helpers.


Structure of the tests
======================

Most of the setup, teardown and helpers that are shared by tests are found in `conftest.py`, and
are implemented as pytest fixtures. The fixtures are consumed, i.e. used, by the tests by taking
them as an argument in the test method. These fixtures creates and tear down the bus session on
the system using `dbus-daemon`, the service running on the outside of the proxy, and the
`dbus-proxy` itself. The `conftest.py` module is automatically picked up and used by `py.test`.

The `service_stubs.py` module implements the D-Bus service(s) that are needed by the proxy tests to
represent something running on the outside of the proxy. The test fixtures sets this up.

One design guideline is that the tests imports specific details about e.g. interface names, D-Bus socket
paths, etc., from the helper modules. Therefore the test module(s) should avoid duplicating details like that.
This is to reduce any ripple effects created when changing the setup/helper code.


Running the tests
=================

Tests are executed with `py.test`, e.g. like this:

    py.test -v -s
