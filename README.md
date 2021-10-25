# ec2 provisioner

Script to provision EC2 instances, using a yaml config file

## Prerequisites

You will need to have python3 and boto3 installed, you will also need to have an AWS access key, and secret, either in the ~/.aws/credentials file, or passed through the cli

## How to Run

To run first clone the repository,

```bash
git clone https://github.com/emalinowski/ec2Provisioner.git
```

Next you will want to create a yaml file with the following information

```yaml
---
  # This YAML configuration specifies a server with two volumes and two users
  server:
    instance_type: t2.micro
    ami_type: amzn2
    architecture: x86_64
    root_device_type: ebs
    virtualization_type: hvm
    min_count: 1
    max_count: 1
    volumes:
      - device: /dev/xvda
        size_gb: 10
        type: ext4
        mount: /
      - device: /dev/xvdf
        size_gb: 100
        type: xfs
        mount: /data
    users:
      - login: user1
        ssh_key: --user1 ssh public key goes here-- user1@localhost
      - login: user2
        ssh_key: --user2 ssh public key goes here-- user2@localhost

```

Next you will want to run the following to trigger the script

```bash
python3 ec2_provisioner/bin/ec2_provisioner.py provision_ec2 --config-path=(config path) ...optional --region=(region) --aws-key(aws_access_key_id) --aws-secret(aws_secret_access_key)
```

After it is run it should return a public IP address. Use the ssh key tied to the public ssh key supplied in the yaml file to ssh to the user described in the yaml file
