# Ansible Collection - ericzolf.libvirt_automated

This collection will allow you to:

- setup and configure libvirt
- create and remove domains
- also address storage and network
- perhaps even modify some of the above objects

It is very early work done mostly to learn how to handle collections
but the collection already has:

- 1 role to basically setup a libvirt host
- roles to create and wipe domains (aka VMs)

So that using a proper inventory, you can create (and remove) as many
VMs on as many hosts as you want, using a proper inventory.
An example is available under the [playbooks directory](playbooks/).
