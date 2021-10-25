import argparse
import sys
import settings
from ec2_provisioner.ec2_provisioner.main import EC2Provisioner


def parse_arguments():
  args = parse_arguments()

  # get database information
  sys.path.append(args.path)


def parse_arguments():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(title="action", dest="action")

    ec2_provisioner_cmd = subparsers.add_parser("provision_ec2")
    ec2_provisioner_cmd.add_argument(
        "--config-path", required=True, help="Path to configuration YAML file"
    )
    ec2_provisioner_cmd.add_argument(
        "--aws-key", required=False, help="The name of s3 job queue"
    )
    ec2_provisioner_cmd.add_argument(
        "--aws-secret", required=False, help="The name of the job definition"
    )
    ec2_provisioner_cmd.add_argument(
        "--region", required=False, help="The name of the job definition"
    )     
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()
    if args.action == "provision_ec2":
        provisioner  = EC2Provisioner(
            config_path=args.config_path,
            default_region = args.region,
            aws_access_key_id = args.aws_key,
            aws_secret_access_key = args.aws_secret,
        )
        provisioner.provision_vms()
    elif args.action is None:
        print("Please use by runing python3 ec2_provisioner/bin/ec2_provisioner.py provision_ec2")