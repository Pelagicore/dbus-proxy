
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

1. A D-Bus session bus exists on `/tmp/dbus_proxy_outside_socket` Launch with e.g:

    dbus-daemon --session --nofork --address=unix:path=/tmp/dbus_proxy_outside_socket --print-pid --print-address

2. The outside service is running

    cd component-test && ./start_outside_service.py

Running the tests
=================

The two pytest test modules (test_dbus_proxy_permits.py and test_dbus_proxy_restricts.py) needs to be run with
different D-Bus proxy configurations. Hence, they need to be executed individually with the D-Bus proxy restarted
between each execution.

To run test_dbus_proxy_permits.py:

    cd component-test

    DBUS_SESSION_BUS_ADDRESS="unix:path=/tmp/dbus_proxy_outside_socket" <build-dir>/dbus-proxy /tmp/dbus_proxy_inside_socket session < conf_allow_all.json

    cd component-test && py.test -vvv test_dbus_proxy_permits.py

To run test_dbus_proxy_restricts.py:

    cd component-test

    DBUS_SESSION_BUS_ADDRESS="unix:path=/tmp/dbus_proxy_outside_socket" <build-dir>/dbus-proxy /tmp/dbus_proxy_inside_socket session < conf_restrict_all.json

    cd component-test && py.test -vvv test_dbus_proxy_restricts.py
