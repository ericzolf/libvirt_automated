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
        - The name of the domain will be used as hostname after having being stripped of any non valid prefix like one ending with an underscore.
        - "Description fields looking like YAML/JSON, i.e. enclosed with '---'/'...' resp. '{'/'}' will be interpreted as YAML (JSON being a subset of it), and the found key/value pairs loaded as variables."
        - "If the interpretation as YAML fails, the error will be ignored and the description loaded as variable."
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
      dom_filter:
        description: filter on acceptable VMs' (aka domain) name, in form of a Python regex
        env:
            - name: LIBVIRT_INV_DOM_FILTER
      var_prefix:
        description: prefix for the variables created by this inventory plug-in
        default: 'libvirt_'
        env:
            - name: LIBVIRT_INV_VAR_PREFIX
      prefix_desc_vars:
        description: shall the variables discovered in the description field interpreted as YAML be prefixed
        default: false
        env:
            - name: LIBVIRT_INV_PREFIX_DESC_VARS
      take_ip:
        description: take the first IP address as ansible_host variable
        default: true
        env:
            - name: LIBVIRT_INV_TAKE_IP
'''

# TODO add the following line before options in documentation if adding cache support
#    extends_documentation_fragment:
#        - inventory_cache

import libvirt
import re
import yaml

from ansible.plugins.inventory import BaseInventoryPlugin


def _libvirt_callback(userdata, err):
    pass


class InventoryModule(BaseInventoryPlugin):

    NAME = 'ericzolf.libvirt_automated.libvirt_inv'  # used internally by Ansible, it should match the file name

    dns_invalid_pattern = re.compile(".*[^a-zA-Z0-9.-]")   # everything before the first invalid character

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

        # grab a few options
        dom_filter = self.get_option('dom_filter')
        var_prefix = self.get_option('var_prefix')
        prefix_desc_vars = self.get_option('prefix_desc_vars')
        take_ip = self.get_option('take_ip')

        # open the connection to libvirt and get all domains/VMs
        conn = libvirt.open(self.get_option('uri'))
        # TODO inactive VMs are more difficult to handle so we'll improve later
        domains = conn.listAllDomains(libvirt.VIR_CONNECT_LIST_DOMAINS_ACTIVE)

        # workaround because libvirt outputs its own error messages
        libvirt.registerErrorHandler(f=_libvirt_callback, ctx=None)

        #parse data and create inventory objects:
        for dom in domains:
            if (not dom_filter) or re.search(dom_filter, dom.name()):
                host_name = self.dns_invalid_pattern.sub('', dom.name())
                self.inventory.add_host(host_name)
                # metadata fails if the requested metadata doesn't exist
                try:
                    self.inventory.set_variable(host_name, var_prefix + 'title',
                                                dom.metadata(libvirt.VIR_DOMAIN_METADATA_TITLE, None))
                except libvirt.libvirtError:
                    pass
                # we try to interpret the description as a YAML/JSON field if it looks like one
                try:
                    dom_description = dom.metadata(libvirt.VIR_DOMAIN_METADATA_DESCRIPTION, None)
                    if ((dom_description.startswith('---') and dom_description.endswith('...'))
                            or (dom_description.startswith('{') and dom_description.endswith('}'))):
                        try:
                            for var, value in yaml.safe_load(dom_description).items():
                                if prefix_desc_vars:
                                    var = var_prefix + var
                                self.inventory.set_variable(host_name, var, value)
                        except yaml.parser.ParserError:
                            self.inventory.set_variable(host_name, var_prefix + 'description', dom_description)
                    else:
                        self.inventory.set_variable(host_name, var_prefix + 'description', dom_description)
                except libvirt.libvirtError:
                    pass
                if take_ip and dom.interfaceAddresses(0):  # 0 is the source
                    dev = list(dom.interfaceAddresses(0))[0]  # take the first device
                    device_ip = dom.interfaceAddresses(0)[dev]['addrs'][0]['addr']  # take the first address
                    self.inventory.set_variable(host_name, 'ansible_host', str(device_ip))
