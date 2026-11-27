# -*- mode: ruby -*-
# MailLab: an email server and a Thunderbird client on VirtualBox guests.
#
#   vagrant up mail01     # build the server (about 5 minutes)
#   vagrant up client01   # build the desktop client with Thunderbird (GUI window opens)
#
# Both guests sit on the VirtualBox host-only network 192.168.56.0/24.
# Each also has the default NAT adapter (10.0.2.0/24) for package downloads only.

Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/focal64"   # Ubuntu 20.04 LTS, current in 2021

  config.vm.define "mail01", primary: true do |m|
    m.vm.hostname = "mail.maillab.test"
    m.vm.network "private_network", ip: "192.168.56.10"
    m.vm.provider "virtualbox" do |vb|
      vb.name   = "maillab-mail01"
      vb.cpus   = 2
      vb.memory = 2048
    end
    %w[00-common 10-dns 20-tls 30-postfix 40-dovecot 50-users 60-hardening 90-verify].each do |step|
      m.vm.provision step, type: "shell", path: "provision/#{step}.sh",
        env: { "LAB_USERS" => "alice bob carol" }
    end
  end

  config.vm.define "client01", autostart: false do |c|
    c.vm.hostname = "client01.maillab.test"
    c.vm.network "private_network", ip: "192.168.56.20"
    c.vm.provider "virtualbox" do |vb|
      vb.name   = "maillab-client01"
      vb.gui    = true
      vb.cpus   = 2
      vb.memory = 3072
      vb.customize ["modifyvm", :id, "--vram", "64", "--clipboard-mode", "bidirectional"]
    end
    c.vm.provision "client", type: "shell", path: "provision/client.sh"
  end
end
