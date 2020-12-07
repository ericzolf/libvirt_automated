#!/usr/bin/env python3
# usage example:
# LIBVIRT_INV_VAR_PREFIX=myvar_ LIBVIRT_INV_VM_FILTER=.*test.* \
#   ./libvirt_inv.py --list
# (see below for comments and other variables)

import argparse
import json
import libvirt
import pdb
import os
import re


class Inventory(object):

    def __init__(self):
        self.parse_cli_args()
        # filter on the name of the VMs present in libvirt
        self.vm_filter = os.environ.get('LIBVIRT_INV_VM_FILTER', None)
        # prefix for created host variables in the inventory
        self.var_prefix = os.environ.get('LIBVIRT_INV_VAR_PREFIX',
                                         'libvirt_inv_')
        # variable to take the hostname from, either 'name' or 'title'
        self.hostname = os.environ.get('LIBVIRT_INV_HOSTNAME', 'title')

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
                name = dom.name()
                title = dom.metadata(libvirt.VIR_DOMAIN_METADATA_TITLE, None)
                description = dom.metadata(
                    libvirt.VIR_DOMAIN_METADATA_DESCRIPTION, None)
                dev = list(dom.interfaceAddresses(0))[0]
                device_ip = dom.interfaceAddresses(0)[dev]['addrs'][0]['addr']

                # get rid of prefix until last underscore,
                # which is not allowed in DNS hostnames
                if (self.hostname == "title"):
                    host_name = re.sub("^.*_", "", title)
                elif (self.hostname == "name"):
                    host_name = re.sub("^.*_", "", name)

                hosts.append(host_name)
                self.inventory["_meta"]["hostvars"].update({host_name: {
                                   'ansible_host': device_ip,
                                   self.var_prefix + 'name': name,
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
