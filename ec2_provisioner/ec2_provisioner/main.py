import boto3
import yaml
import logging
import os
import time

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)


class EC2Provisioner:
  def __init__(self, aws_access_key_id='', aws_secret_access_key='', default_region='us-east-1', config_path=''):
      log.info(f"Using region {default_region}")
      if aws_access_key_id and aws_secret_access_key:
        log.info("Using AWS access key/secret from args.")
        self.ec2_client = boto3.client(
          "ec2",
          aws_access_key_id=aws_access_key_id,
          aws_secret_access_key=aws_secret_access_key,
          region = default_region
        )
        self.ec2_resource = boto3.resource(
          "ec2",
          aws_access_key_id=aws_access_key_id,
          aws_secret_access_key=aws_secret_access_key,
          region = default_region
        )
      else:
          log.info("AWS creds not set through args, trying to get creds through default methods")
          self.ec2_client = boto3.client("ec2", default_region)
          self.ec2_resource = boto3.resource("ec2", default_region)
      
      with open(config_path) as config_file:
        log.info(f"Using config file at {config_path}")
        try:
          self.config = yaml.load(config_file, Loader=yaml.FullLoader)["server"]
        except yaml.YAMLError as err:
          log.error(f"Error while reading YAML file {config_path}")
          raise err

  def _get_latest_ami_id(self):
      log.info("Looking for latest ami id's")
      amis = self.ec2_client.describe_images(
        Filters=[
          {
            "Name": "architecture",
            "Values": [self.config["architecture"]],
          },
          {
            "Name": "root-device-type",
            "Values": [self.config["root_device_type"]],
          },
          {
            "Name": "virtualization-type",
            "Values": [self.config["virtualization_type"]],
          },
          {"Name": "owner-id", "Values": ["137112412989"]},
          {
            "Name": "name",
            "Values": ["*" + self.config["ami_type"] + "*"],
          },
        ]
      ).get("Images")

      if amis is None:
        raise Exception(f"Could not an AMI with ami type {self.config['ami_type']}.")
      else:  
        log.debug(f"Found AMI's {amis}")
      sorted_amis = sorted(amis, key=lambda x: x['CreationDate'], reverse=True)
      log.info(f"Using ami with id {sorted_amis[0]['ImageId']}")
      return sorted_amis[0]["ImageId"]

  def _create_security_groups(self):
    log.info("Getting security group for ssh access")
    default_vpc = self._get_default_vpc()
    if "ec2SshSecurityGroup" not in [value for elem in self.ec2_client.describe_security_groups()["SecurityGroups"] for value in elem.values()]:
      log.info("Security group not setup. Creating new security group now.")
      try:
        security_group = self.ec2_client.create_security_group(
          GroupName="ec2SshSecurityGroup",
          Description="Security group to allow ssh traffic",
          VpcId=default_vpc,
        )
        self.ec2_client.authorize_security_group_ingress(
          GroupId=security_group["GroupId"],
          IpPermissions=[
            {
              "IpProtocol": "tcp",
              "FromPort": 22,
              "ToPort": 22,
              "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
            }
          ],
        )
        log.info("Created security group")
        return security_group["GroupId"]
      except self.botocore.exceptions.ClientError as e:
          raise Exception("Security group could not be created.")
    else:
      for security_group in self.ec2_client.describe_security_groups()["SecurityGroups"]:
        if security_group["GroupName"] == "ec2SshSecurityGroup":
          log.info(f"Found security group with ID {security_group['GroupId']}")
          return security_group["GroupId"]

  def _get_default_vpc(self):
    vpcs = self.ec2_client.describe_vpcs(Filters=[{"Name": "instance-tenancy", "Values": ["default"]}])
    log.debug(f"Looking for the default VPC {vpcs}")
    if len(vpcs["Vpcs"]) > 0:
        default_vpc = vpcs["Vpcs"][0]["VpcId"]
    else:
        raise Exception(
            "Could not find a valid VPC."
        )
    return default_vpc

  def _create_user_data(self, user_data):
    log.info("Working on EC2 user data script")
    user_data = self._add_users(user_data)
    block_device_mappings, user_data = self._add_storage(user_data)
    return block_device_mappings, user_data

  def _add_users(self, user_data):
    log.debug("Adding user creation info to user data script")
    for user in self.config["users"]:
      login = user["login"]
      sshkey = user["ssh_key"]
      user_data.append(f"sudo useradd -m {login}")
      user_data.append(f"sudo mkdir /home/{login}/.ssh")
      user_data.append(f"sudo echo \"{sshkey}\" > /home/{login}/.ssh/authorized_keys")
    return user_data

  def _add_storage(self, user_data):
    log.debug("Adding mount creation to user data and setting up disk info")
    block_device_mappings= []
    for disk in self.config["volumes"]:
      mount = {
        "DeviceName": disk["device"],
        "Ebs": {
          "VolumeSize": disk["size_gb"],
          "VolumeType": "gp2",
          "DeleteOnTermination": True
        },
      }
      user_data.append(f"sudo mkfs -t {disk['type']} {disk['device']}")
      user_data.append(f"sudo mkdir {disk['mount']}")
      user_data.append(f"sudo mount {disk['device']} {disk['mount']}")
      block_device_mappings.append(mount)
    return block_device_mappings, user_data

  def provision_vms(self):
      ami = self._get_latest_ami_id()
      user_data = ["#!/bin/bash"]
      block_device_mappings, user_data = self._create_user_data(user_data)
      security_group = self._create_security_groups()
      instance = self.ec2_resource.create_instances(ImageId=ami, BlockDeviceMappings=block_device_mappings, UserData="\n".join(user_data), SecurityGroupIds=[security_group], MinCount=1, MaxCount=1, InstanceType=self.config["instance_type"])
      log.info("Waiting 20 seconds for EC2 to startup")
      time.sleep(20)
      ip = self.ec2_client.describe_instances(InstanceIds=[instance[0].instance_id])['Reservations'][0]['Instances'][0]['PublicIpAddress']
      print(f"EC2 instance created, IP is {ip}")
      print("Please give the instance a few minutes to add setup your users and finish the volume mounts.")
