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
      url:
        description: url to foreman
        default: 'http://localhost:3000'
        env:
            - name: FOREMAN_SERVER
              version_added: "2.8"
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

         # example consuming options from inventory source
         mysession = apilib.session(user=self.get_option('api_user'),
                                    password=self.get_option('api_pass'),
                                    server=self.get_option('api_server')
         )


         # make requests to get data to feed into inventory
         mydata = mysession.getitall()

         #parse data and create inventory objects:
         for colo in mydata:
             for server in mydata[colo]['servers']:
                 self.inventory.add_host(server['name'])
                 self.inventory.set_variable(server['name'], 'ansible_host', server['external_ip'])

class Inventory(object):

    def __init__(self):
        self.parse_cli_args()
        # filter on the name of the VMs present in libvirt
        self.vm_filter = os.environ.get('LIBVIRT_INV_VM_FILTER', None)
        # prefix for created host variables in the inventory
        self.var_prefix = os.environ.get('LIBVIRT_INV_VAR_PREFIX',
                                         'libvirt_inv_')
        # URI to connect to libvirt
        self.connection_uri = os.environ.get('LIBVIRT_INV_URI',
                                             'qemu:///system')

        self.inventory = {"_meta": {"hostvars": {}}}
        self.conn = libvirt.open(self.connection_uri)

        if self.args.list:
            self.handle_list()
        else:
            self.inventory = self.inventory

        print(json.dumps(self.inventory))

    def handle_list(self):
        groups = {}
        hosts = []

        domains = self.conn.listAllDomains()

        for dom in domains:
            if dom.isActive() and (self.vm_filter is None or
                                   re.match(self.vm_filter, dom.name())):
                # get rid of prefix until last underscore,
                # which is not allowed in DNS hostnames
                name = re.sub("^.*_", "", dom.name())
                title = dom.metadata(libvirt.VIR_DOMAIN_METADATA_TITLE, None)
                description = dom.metadata(
                    libvirt.VIR_DOMAIN_METADATA_DESCRIPTION, None)
                dev = list(dom.interfaceAddresses(0))[0]
                device_ip = dom.interfaceAddresses(0)[dev]['addrs'][0]['addr']

                hosts.append(name)
                self.inventory["_meta"]["hostvars"].update({name: {
                                   'ansible_host': device_ip,
                                   self.var_prefix + 'title': title,
                                   self.var_prefix + 'description': description
                                }})

        self.inventory.update({'libvirt': {'hosts': hosts, 'vars': {}}})

    def parse_cli_args(self):
        parser = argparse.ArgumentParser(
                    description='Produce an Ansible Inventory from a file')
        parser.add_argument('--list', action='store_true', help='List Hosts')
        self.args = parser.parse_args()


Inventory()
