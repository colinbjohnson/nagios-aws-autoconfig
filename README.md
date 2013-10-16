# Overview
The nagios-aws-autoconfig tool will automatically create nagios configuration files for all hosts in a given Amazon Web Services region.

# How nagios-aws-autoconfig Works
1. nagios-aws-autoconfig queries AWS for all hosts in a region.
2. nagios-aws-autoconfig examines each host for a tag named "Services"
3. for each ec2 instance found nagios-aws-autoconfig will create host definition file in your nagios config directory
4. for each ec2 instance with a "Services" tag nagios-aws-autoconfig will create a service entry and add the host to it - and nagios-aws-autoconfig will then create a service definition file in your nagios config directory
5. nagios-aws-autoconfig will create "general" host and service configuration files
6. when finished running nagios-aws-autoconfig will have provided you with a complete set of nagios configuration files

# Example Use:
1. create templates in nagios_templates_dir
2. run nagios_aws_autoconfig.py


    nagios_aws_autoconfig.py


# Example Use (with Options):


    nagios_aws_autoconfig.py --nagios-config-dir /my/nagios/configs --region us-west-1