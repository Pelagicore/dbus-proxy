
vagrant_private_key_file="vagrant_key"

ram = 4 #GB
cpus = 3

Vagrant.configure(2) do |config|
    config.vm.box = "debian/contrib-jessie64"
    config.vm.provider "virtualbox" do |vb|
        vb.customize [ "guestproperty", "set", :id, "/VirtualBox/GuestAdd/VBoxService/--timesync-set-threshold", 200 ]
    end

    # Deploy a private key used to clone gits from pelagicore.net
    config.vm.provision "file", source: vagrant_private_key_file, destination: "/home/vagrant/.ssh/id_rsa"

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
    config.vm.provision "shell", privileged: false, path: "vagrant-cookbook/system-config/pelagicore-ssh-conf.sh"

    # Install dependencies for py.test and D-Bus testing
    config.vm.provision "shell", path: "vagrant-cookbook/deps/pytest-and-dbus-testing-dependencies.sh"

    # Build and install project
    config.vm.provision "shell", privileged: false,
        args: ["dbus-proxy", "git@git.pelagicore.net:application-management/dbus-proxy.git"],
        path: "vagrant-cookbook/build/cmake-git-builder.sh"

    config.vm.provision "shell", privileged: false, inline: <<-SHELL
        sudo pip install pytest
        cd dbus-proxy/component-test
        py.test -v --junitxml=component-test-results.xml
    SHELL

end

