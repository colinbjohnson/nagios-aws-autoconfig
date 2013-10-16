#!/usr/bin/env python

import argparse
import logging
import os


import boto.ec2
from jinja2 import Environment
from jinja2 import FileSystemLoader


class Service:
    def __init__(self, service_name, host_names, check_command):
        self.service_name = service_name
        self.host_names = host_names
        self.check_command = check_command


def populate_instance_dictionary(conn, instance_dictionary):
    '''accepts an ec2 interface and instance_dictionary variable - populates
    the instance_dictionary variable'''
    reservation_list = conn.get_all_instances()
    for current_reservation in reservation_list:
        for instance in current_reservation.instances:
        #only want running instances
            if instance.state == "running":
                logging.info('Instance {instance!s} will be added to the instance dictionary.'.format(instance=instance))
                instance_dictionary[instance.id] = instance


def populate_nrpe(instance_dictionary, service_dictionary):
    instance_dictionary_csv = ''
    for instance in instance_dictionary:
        if 'Name' in instance_dictionary[instance].tags:
            instance_dictionary_csv += instance_dictionary[instance].tags.get('Name').encode('utf-8') + ','
            instance_dictionary_csv_trim = instance_dictionary_csv[:-1]
            service_dictionary['nrpe_disk_space'] = Service('nrpe_disk_space',
                instance_dictionary_csv_trim, 'check_nrpe!check_disk_space!10%20% /')
            service_dictionary['nrpe_disk_inode'] = Service('nrpe_disk_inode',
                instance_dictionary_csv_trim, 'check_nrpe!check_disk_inode!10%20% /')
            service_dictionary['nrpe_cpu_load'] = Service('nrpe_cpu_load',
                instance_dictionary_csv_trim, 'check_nrpe!check_cpu_load!30,25,2015,10,5')
            service_dictionary['nrpe_mem_swap'] = Service('nrpe_mem_swap',
                instance_dictionary_csv_trim, 'check_nrpe!check_mem_swap!80%90%')


def populate_service_dictionary(instance_dictionary, service_dictionary):
    for instance in instance_dictionary:
        if 'Name' in instance_dictionary[instance].tags:
        # encoding from unicode object type to string object type - would like
        # to research more when time available
            name_tag = instance_dictionary[instance].tags.get("Name").encode('utf-8')
        else:
            name_tag = "None"
        # if instance has a tag named "Services"
        if 'Services' in instance_dictionary[instance].tags:
            # then break the services up into an array
            instance_services = instance_dictionary[instance].tags.get("Services").split(",")
            # for each service in the array
            for instance_service in instance_services:
                # if the instance_service already exists in the array then
                # append the instance's name to the service dictionary
                if instance_service in service_dictionary.keys():
                    service_dictionary[instance_service].host_names += ',' + name_tag
                else:
                    logging.info('Service {instance_service!s} has been added to the service dictionary.'.format
                        (instance_service=instance_service))
                    # else if the service is not in the service dictionary, append the
                    # service name and list the instance as a provider of that service
                    new_service = Service(instance_service, name_tag, "check_" + instance_service)
                    service_dictionary[instance_service.encode('utf-8')] = new_service


def write_host_configs(instance_dictionary, nagios_config_file_dir, host_template):
    '''writes host configs'''
    logging.info('write_host_configs called')
    for instance in instance_dictionary:
        if instance_dictionary[instance].tags.has_key("Name"):
            host_file_content = host_template.render(host_name=instance_dictionary[instance].tags.get("Name"),
                check_command='check-host-alive', private_ip_address=instance_dictionary[instance].private_ip_address)
            host_file_path = str('{nagios_config_file_dir!s}/hosts/{host!s}.cfg'.format
                (nagios_config_file_dir=nagios_config_file_dir, host=instance_dictionary[instance].tags.get("Name")))
            host_file_handle = open(host_file_path, 'w')
            host_file_handle.write(host_file_content)
            host_file_handle.close()


def write_service_configs(service_dictionary, nagios_config_file_dir, service_template):
    '''write service configs'''
    logging.info('write_service_configs called')
    for service in service_dictionary:
        logging.info('service template for {service!s} will be rendered'.format(service=service))
        service_file_content = service_template.render(host_list=service_dictionary[service].host_names,
            service_description=service_dictionary[service].service_name, check_command=service_dictionary[service].check_command)
        service_file_path = str('{nagios_config_file_dir!s}/services/{service!s}.cfg'.format(nagios_config_file_dir=nagios_config_file_dir, service=service))
        service_file_handle = open(service_file_path, 'w')
        service_file_handle.write(service_file_content)
        service_file_handle.close()


def write_host_common(nagios_config_file_dir):
    '''needs to write a common host file'''
    pass


def write_service_common(nagios_config_file_dir):
    '''needs to write a common service file'''
    pass


parser = argparse.ArgumentParser()
parser.add_argument('--region', help='region for which nagios_aws_autodiscover should be run. Default is us-east-1.', default='us-east-1')
parser.add_argument('--nagios-config-path', dest='nagiosconfigpath', help='configuration path for Nagios files', default='./nagios_config_dir')
args = parser.parse_args()

region = args.region
nagios_config_file_dir = args.nagiosconfigpath

env = Environment(loader=FileSystemLoader('nagios_templates_dir'))
host_template = env.get_template('host.template')
service_template = env.get_template('service.template')

log_level = 'INFO'
logging.basicConfig(level=log_level)

try:
    conn = boto.ec2.connect_to_region(region)
except boto.exception.EC2ResponseError(401, 'AuthFailure'):
    logging.critical('An error occured. Authorization failed when connecting to AWS.')

instance_dictionary = {}
service_dictionary = {}

populate_instance_dictionary(conn, instance_dictionary)
populate_service_dictionary(instance_dictionary, service_dictionary)
# adds nrpe services to service_dictionary
populate_nrpe(instance_dictionary, service_dictionary)

# clears configuration data from the hosts directory
for file in os.listdir(nagios_config_file_dir + '/hosts/'):
    os.remove(nagios_config_file_dir + '/hosts/' + file)

write_host_configs(instance_dictionary, nagios_config_file_dir, host_template)

# clears configuration data from the services directory
for file in os.listdir(nagios_config_file_dir + '/services/'):
    os.remove(nagios_config_file_dir + '/services/' + file)

write_service_configs(service_dictionary, nagios_config_file_dir, service_template)

write_host_common(nagios_config_file_dir)
write_service_common(nagios_config_file_dir)

print 'Summary:'
print 'Count of instances in the Instance List: {instance_count!s}'.format(instance_count=(len(instance_dictionary)))
print 'Count of services in Service Dictionary: {service_count!s}'.format(service_count=len(service_dictionary.keys()))
print 'List of Services Found in Service Dictionary: {services!s}'.format(services=service_dictionary.keys())
