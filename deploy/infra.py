import boto3
import utils
import os
from constants import *
import json
import socket


def create_key_pair(key_name: str) -> str:
    ec2 = boto3.client("ec2", config=BOTO3_CONFIG)

    key_pair = ec2.create_key_pair(KeyName=key_name)
    # Save the private key to a .pem file
    file_name = f"{CONFIGS_PATH}/{key_name}.pem"
    utils.write_file(file_name, key_pair["KeyMaterial"])

    print(f"Key pair '{key_name}' created and saved to {file_name}.")


def create_security_group(group_name, description, rules_in):
    ec2 = boto3.client("ec2", config=BOTO3_CONFIG)

    # Create the security group
    response = ec2.create_security_group(
        GroupName=group_name, Description=description
    )
    security_group_id = response["GroupId"]
    print(f"Security Group '{group_name}' created with ID: {security_group_id}")

    # Allow ingress
    ec2.authorize_security_group_ingress(
        GroupId=security_group_id,
        IpPermissions=rules_in
    )
    print(f"Configured Security Group's '{group_name}' authorizations")

    return security_group_id


def create_ec2_instances(
    instance_type: str, count: int, key_name: str, sec_group_id: str, public: bool, subnet_id: str
):
    # Use resource client
    ec2 = boto3.resource("ec2", config=BOTO3_CONFIG)
    
    # Create instances
    instances = ec2.create_instances(
        ImageId="ami-0e86e20dae9224db8",  # Ubuntu AMI
        MinCount=count,
        MaxCount=count,
        InstanceType=instance_type,
        KeyName=key_name,
        NetworkInterfaces = [{
            'AssociatePublicIpAddress': public,  # True or False: Public or Private.
            'DeviceIndex': 0,
            'Groups': [sec_group_id],
            'SubnetId': subnet_id
        }]
    )
    print(f"Created {count} EC2 instances of type {instance_type}")

    # Wait for the instances to be running
    for instance in instances:
        instance.wait_until_running()

    return instances


def get_instance_info(instances):
    instances_info = []

    # Refresh instance details
    for instance in instances:
        instance.reload()
        instances_info.append(
            {
                "Instance ID": instance.id,
                "Public IP": instance.public_ip_address,
                "DNS": instance.public_dns_name,
                "Private IP": instance.private_ip_address,
            }
        )

    return instances_info

def create_nat_gateway(public_subnet_id, elastic_ip_allocation_id, private_subnet_id):
    ec2 = boto3.client('ec2', config=BOTO3_CONFIG)
    response = ec2.create_nat_gateway(
        SubnetId=public_subnet_id,
        AllocationId=elastic_ip_allocation_id
    )
    nat_gateway_id = response['NatGateway']['NatGatewayId']
    print(f"NAT Gateway created: {nat_gateway_id}")
    print("Waiting fot the NAT Gateway to become available...")
    waiter = ec2.get_waiter('nat_gateway_available')
    waiter.wait(NatGatewayIds=[nat_gateway_id])
    print("NAT Gateway is now available !")

    # Get the Route Table ID for the private subnet
    private_subnet_route_table_id = get_route_table_id_for_subnet(private_subnet_id)
    
    # Create a route in the private subnet's route table to route traffic through the NAT Gateway
    ec2.create_route(
        RouteTableId=private_subnet_route_table_id,
        DestinationCidrBlock='0.0.0.0/0',  # Route all traffic to the NAT Gateway
        NatGatewayId=nat_gateway_id
    )
    print(f"Route created in route table {private_subnet_route_table_id} to NAT Gateway {nat_gateway_id}")
    
    # Return the NAT Gateway ID and Route Table ID
    return nat_gateway_id

def find_public_subnet(availability_zone='us-east-1c'):
    ec2 = boto3.client('ec2', config=BOTO3_CONFIG)
    
    # Describe all subnets and filter for public ones in the specified Availability Zone
    response = ec2.describe_subnets(
        Filters=[
            {'Name': 'map-public-ip-on-launch', 'Values': ['true']},  # Public subnets
            {'Name': 'availability-zone', 'Values': [availability_zone]}  # Filter by AZ
        ]
    )
    public_subnet_id = response['Subnets'][0]['SubnetId']               # Take the first one.
    print(f"Public Subnet ID: {public_subnet_id}")
    return public_subnet_id

def allocate_new_elastic_ip():
    ec2 = boto3.client('ec2')
    response = ec2.allocate_address(Domain='vpc')
    print(f"New Elastic IP: {response['PublicIp']}, Allocation ID: {response['AllocationId']}")
    return response['AllocationId']

def create_private_subnet(cidr_block = '172.31.96.0/20', availability_zone = "us-east-1c"):       #  172.31.96.0/20 is not yet assigned, and it is part of the 172.31.x.x range of the VPC
    ec2 = boto3.client('ec2')

    # Step 1: Find the VPC ID
    vpcs = ec2.describe_vpcs()
    vpc_id = vpcs['Vpcs'][0]['VpcId']

    print(f"Using VPC ID: {vpc_id}")

    # Step 2: Create the Subnet
    subnet_response = ec2.create_subnet(
        VpcId=vpc_id,
        CidrBlock=cidr_block,
        AvailabilityZone=availability_zone
    )
    subnet_id = subnet_response['Subnet']['SubnetId']
    print(f"Created private subnet with ID: {subnet_id}")

    # Step 3: Disable Auto-assign Public IPs
    ec2.modify_subnet_attribute(
        SubnetId=subnet_id,
        MapPublicIpOnLaunch={'Value': False}
    )
    print(f"Disabled auto-assign public IP for subnet: {subnet_id}")

    return subnet_id

def get_vpc_id_from_subnet(subnet_id):
    ec2 = boto3.client('ec2', config=BOTO3_CONFIG)
    response = ec2.describe_subnets(SubnetIds=[subnet_id])
    vpc_id = response['Subnets'][0]['VpcId']
    return vpc_id

def get_route_table_id_for_subnet(subnet_id):
    ec2 = boto3.client('ec2', config=BOTO3_CONFIG)
    
    # Describe the route tables and filter by subnet ID
    response = ec2.describe_route_tables(
        Filters=[
            {
                'Name': 'association.subnet-id',
                'Values': [subnet_id]
            }
        ]
    )
    
    # If a route table is associated with the subnet, return the Route Table ID
    if response['RouteTables']:
        route_table_id = response['RouteTables'][0]['RouteTableId']
        return route_table_id
    else:
        # If no route table is found, create a new one and associate it with the subnet
        print(f"No route table found for subnet {subnet_id}, creating a new route table.")

        vpc_id = get_vpc_id_from_subnet(subnet_id)   # Extract VPC ID from subnet_id
        route_table_response = ec2.create_route_table(
            VpcId=vpc_id  
        )
        new_route_table_id = route_table_response['RouteTable']['RouteTableId']
        
        # Associate the new route table with the subnet
        ec2.associate_route_table(
            RouteTableId=new_route_table_id,
            SubnetId=subnet_id
        )
        print(f"Created and associated route table {new_route_table_id} with subnet {subnet_id}")
        return new_route_table_id

def deploy():
    # Create configs directory
    os.makedirs(utils.get_path(CONFIGS_PATH), exist_ok=True)

    # Create Key/Pair for the EC2 instances
    create_key_pair(KEY_PAIR_NAME)
    
    # Create Security Groups
    trusted_ip = '172.31.0.0/16'    # VPC IP

    bastion_rules = [
        {
        "IpProtocol": "tcp",
        "FromPort": 22,
        "ToPort": 22,
        "IpRanges": [{"CidrIp": '0.0.0.0/0', "Description": "Allow SSH to serve its role."}],
        },
    ]
    bastion_grp_id = create_security_group(BASTION_SG_NAME, "Bastion Host Security Group", bastion_rules)

    gatekeeper_rules = [
        {   
        "IpProtocol": "tcp",
        "FromPort": 80,
        "ToPort": 80,
        "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "Allow HTTP from outside: Internet facing."}],
        },
        {
        "IpProtocol": "tcp",
        "FromPort": 22,
        "ToPort": 22,
        "IpRanges": [{"CidrIp": '0.0.0.0/0', "Description": "Allow SSH for bootstrap."}],
        },
    ]
    gatekeeper_grp_id  = create_security_group(GATEKEEPER_SG_NAME, "Gatekeeper Security Group", gatekeeper_rules)

    trustedhost_rules = [
        {
        "IpProtocol": "tcp",
        "FromPort": 80,
        "ToPort": 80,
        "UserIdGroupPairs": [{"GroupId": f"{gatekeeper_grp_id}", "Description": "Allow communications only with the Gatekeeper."}] 
        },
        {
        "IpProtocol": "tcp",
        "FromPort": 22,
        "ToPort": 22,
        "IpRanges": [{"CidrIp": f'{trusted_ip}', "Description": "Allow SSH from trusted IP for bootstrap."}]
        }
    ]
    trustedhost_grp_id = create_security_group(TRUSTEDHOST_SG_NAME, "Trusted Host Security Group", trustedhost_rules)

    rules_proxy = [
        {
            "IpProtocol": "tcp",
            "FromPort": 80,
            "ToPort": 80,
            "UserIdGroupPairs": [{"GroupId": f"{trustedhost_grp_id}", "Description": "Allow communication only with the Trusted Host."}], 
        },
        {
            "IpProtocol": "tcp",
            "FromPort": 22,
            "ToPort": 22,
            "IpRanges": [{"CidrIp": f'{trusted_ip}', "Description": "Allow SSH from trusted IP for bootstrap."}],
        },
    ]
    proxy_grp_id = create_security_group(PROXY_SG_NAME, "Proxy Security Group", rules_proxy)

    rules_workers = [
        {
            "IpProtocol": "tcp",
            "FromPort": 3306,
            "ToPort": 3306,
            "UserIdGroupPairs": [{"GroupId": f"{proxy_grp_id}", "Description": "Allow communications only with the Proxy."}],
        },
        {
            "IpProtocol": "icmp",
            "FromPort": -1,
            "ToPort": -1,
            'IpRanges': [{"CidrIp": '0.0.0.0/0', "Description": "Allow ping within the same Security Group."}], 
        },
        {
            "IpProtocol": "tcp",
            "FromPort": 22,
            "ToPort": 22,
            "IpRanges": [{"CidrIp": f'{trusted_ip}', "Description": "Allow SSH from trusted IP for bootstrap"}],
        },
    ]
    workers_grp_id = create_security_group(WORKERS_SG_NAME, "Workers Security Group", rules_workers)



    # Find a public subnet where the NAT Gateway will be placed
    public_subnet_id = find_public_subnet()

    # Create a new Elastic IP
    elastic_ip_allocation_id = allocate_new_elastic_ip()

    # Create a private subnet where instances should be placed.
    private_subnet_id = create_private_subnet()

    # Create the NAT Gateway
    nat_gateway_id = create_nat_gateway(public_subnet_id, elastic_ip_allocation_id, private_subnet_id)

    # Create instances
    instance_bastion      = create_ec2_instances("t2.micro", 1, KEY_PAIR_NAME, bastion_grp_id, public = True, subnet_id = public_subnet_id)         # Bastion Host
    instances_workers     = create_ec2_instances("t2.micro", 3, KEY_PAIR_NAME, workers_grp_id, public = False, subnet_id = private_subnet_id)       # Manager / Slaves
    instance_proxy        = create_ec2_instances("t2.large", 1, KEY_PAIR_NAME, proxy_grp_id, public = False, subnet_id = private_subnet_id)         # Proxy
    instance_gatekeeper   = create_ec2_instances("t2.large", 1, KEY_PAIR_NAME, gatekeeper_grp_id, public = True,  subnet_id  = public_subnet_id)    # Gatekeeper
    instance_trustedhost  = create_ec2_instances("t2.large", 1, KEY_PAIR_NAME, trustedhost_grp_id, public = False, subnet_id = private_subnet_id)   # Trusted Host

    # Extract instances' information
    instances_info_workers       = get_instance_info(instances_workers)
    instance_info_proxy          = get_instance_info(instance_proxy)
    instance_info_gatekeeper     = get_instance_info(instance_gatekeeper)
    instance_info_trustedhost    = get_instance_info(instance_trustedhost)
    instance_info_bastion        = get_instance_info(instance_bastion)

    utils.write_file(WORKERS_INFO_PATH, json.dumps(instances_info_workers))
    utils.write_file(PROXY_INFO_PATH, json.dumps(instance_info_proxy))
    utils.write_file(GATEKEEPER_INFO_PATH, json.dumps(instance_info_gatekeeper))
    utils.write_file(TRUSTEDHOST_INFO_PATH, json.dumps(instance_info_trustedhost))
    utils.write_file(NAT_GATEWAY_ID_PATH, nat_gateway_id)
    utils.write_file(PRIVATE_SUBNET_ID_PATH, private_subnet_id)
    utils.write_file(ELASTIC_IP_ALLOC_ID_PATH, elastic_ip_allocation_id)
    utils.write_file(BASTION_INFO_PATH, json.dumps(instance_info_bastion))

    return instance_info_bastion, instances_info_workers, instance_info_proxy, instance_info_gatekeeper, instance_info_trustedhost