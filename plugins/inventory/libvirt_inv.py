#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = '''
    name: ericzolf.libvirt_automated.libvirt_inv
    plugin_type: inventory
    short_description: libvirt inventory source
    version_added: "2.9"
    requirements:
        - requests >= 1.1
    description:
        - Get inventory hosts from the libvirtd service.
        - "Uses a configuration file as an inventory source, it must end in ``libvirt_inv.yml``, ``libvirt_inv.yaml``, ``libvirt.yml`` or ``libvirt.yaml`` and has a ``plugin: ericzolf.libvirt_automated.libvirt_inv`` entry."
    options:
      plugin:
        description: the name of this plugin, it should always be set to 'ericzolf.libvirt_automated.libvirt_inv' for this plugin to recognize it as it's own.
        required: True
        choices: ['ericzolf.libvirt_automated.libvirt_inv']
      uri:
        description: URI to libvirt end-point
        default: 'qemu:///system'
        env:
            - name: LIBVIRT_INV_URI
      filter:
        description: filter on acceptable VMs' name, in form of a Python regex
        alias: vm_filter
        env:
            - name: LIBVIRT_INV_VM_FILTER
      prefix:
        description: prefix for the variables created by this inventory plug-in
        default: 'libvirt_'
        alias: var_prefix
        env:
            - name: LIBVIRT_INV_VAR_PREFIX
      take_ip:
        description: take the first IP address as ansible_host variable
        default: true
        env:
            - name: LIBVIRT_INV_TAKE_IP
'''

# TODO add the following line before options in documentation if adding cache support
#    extends_documentation_fragment:
#        - inventory_cache

import argparse
import json
import libvirt
import pdb
import os
import re

from ansible.plugins.inventory import BaseInventoryPlugin

class InventoryModule(BaseInventoryPlugin):

    NAME = 'ericzolf.libvirt_automated.libvirt_inv'  # used internally by Ansible, it should match the file name

    dns_invalid_pattern = re.compile("[^a-zA-Z0-9.-].*")   # everything after the first invalid character

    def verify_file(self, path):
        ''' return true/false if this is possibly a valid file for this plugin to consume '''
        valid = False
        if super(InventoryModule, self).verify_file(path):
            # base class verifies that file exists and is readable by current user
            if path.endswith(('libvirt_inv.yaml', 'libvirt_inv.yml', 'libvirt.yaml', 'libvirt.yml')):
                valid = True
        return valid

    def parse(self, inventory, loader, path, cache=True):

        # call base method to ensure properties are available for use with other helper methods
        super(InventoryModule, self).parse(inventory, loader, path, cache)

        # this method will parse 'common format' inventory sources and
        # update any options declared in DOCUMENTATION as needed
        config = self._read_config_data(path)

        # if NOT using _read_config_data you should call set_options directly,
        # to process any defined configuration for this plugin,
        # if you don't define any options you can skip
        #self.set_options()
        vm_filter = self.get_option('filter')
        var_prefix = self.get_option('prefix')
        take_ip = self.get_option('take_ip')

        conn = libvirt.open(self.get_option('uri'))
        domains = conn.listAllDomains()

        #parse data and create inventory objects:
        for dom in domains:
            if dom.isActive() and (vm_filter is None
                                   or re.search(vm_filter, dom.name())):
                host_name = self.dns_invalid_pattern.sub("", dom.name())
                self.inventory.add_host(host_name)
                self.inventory.set_variable(host_name, var_prefix + 'title',
                                            dom.metadata(libvirt.VIR_DOMAIN_METADATA_TITLE, None))
                self.inventory.set_variable(host_name, var_prefix + 'description',
                                            dom.metadata(libvirt.VIR_DOMAIN_METADATA_DESCRIPTION, None))
                if take_ip and dom.interfaceAddresses(0):  # 0 is the source
                    dev = dom.interfaceAddresses(0).keys()[0]  # take the first device
                    device_ip = dom.interfaceAddresses(0)[dev]['addrs'][0]['addr']
                    self.inventory.set_variable(host_name, 'ansible_host', str(device_ip))
