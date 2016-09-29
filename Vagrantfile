
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


ram = 4 #GB
cpus = 3

Vagrant.configure(2) do |config|
    config.vm.box = "debian/contrib-jessie64"
    config.vm.provider "virtualbox" do |vb|
        vb.customize [ "guestproperty", "set", :id, "/VirtualBox/GuestAdd/VBoxService/--timesync-set-threshold", 200 ]
    end

    # Sync the repo root with this path in the VM
    config.vm.synced_folder "./", "/home/vagrant/dbus-proxy", create: true

    # Workaround for some bad network stacks
    config.vm.provision "shell", privileged: false, path: "vagrant-cookbook/utils/keepalive.sh"

    # Use apt-cacher on main server
    config.vm.provision "shell",
        args: ['10.8.36.16'],
        path: "vagrant-cookbook/system-config/apt-cacher.sh"

    # Upgrade machine to testing distro & install build dependencies
    config.vm.provision "shell", path: "vagrant-cookbook/deps/testing-upgrade.sh"
    config.vm.provision "shell", path: "vagrant-cookbook/deps/common-build-dependencies.sh"
    config.vm.provision "shell", path: "vagrant-cookbook/deps/common-run-dependencies.sh"
    config.vm.provision "shell", path: "vagrant-cookbook/deps/sphinx-dependencies.sh"

    # Add known hosts
    config.vm.provision "shell", privileged: false, path: "vagrant-cookbook/system-config/ssh-keyscan-conf.sh"

    # Install dependencies for py.test and D-Bus testing
    config.vm.provision "shell", path: "vagrant-cookbook/deps/pytest-and-dbus-testing-dependencies.sh"

    # Build and install project
    config.vm.provision "shell", privileged: false,
        args: ["dbus-proxy"],
        path: "vagrant-cookbook/build/cmake-builder.sh"

    config.vm.provision "shell", privileged: false, inline: <<-SHELL
        cd dbus-proxy/component-test
        py.test -v --junitxml=component-test-results.xml
    SHELL

end

