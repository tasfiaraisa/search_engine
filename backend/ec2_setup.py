import boto3
from botocore.exceptions import ClientError
import paramiko
from scp import SCPClient 
import time

# Initialize the EC2 client
ec2 = boto3.client(
    'ec2',
    region_name='us-east-1'
)

def create_key_pair():
    key_pair = ec2.create_key_pair(KeyName='ece326_key')
    with open("ece326_key.pem", "w") as file:
        file.write(key_pair['KeyMaterial'])
    print("Key pair created and saved as ece326_key.pem")

#
#create_key_pair()

def create_security_group():
    try:
        # Try to create the security group
        response = ec2.create_security_group(
            GroupName='ece326-group-19',
            Description='ECE-326 Lab-2 Security Group'
        )
        security_group_id = response['GroupId']
        print("Security Group Created with ID:", security_group_id)

        # Set inbound rules
        ec2.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpPermissions=[
                {'IpProtocol': 'tcp', 'FromPort': 80, 'ToPort': 80, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                {'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                {'IpProtocol': 'tcp', 'FromPort': 8080, 'ToPort': 8080, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
            ]
        )
    except ClientError as e:
        # If the error is because the security group already exists, retrieve its ID
        if 'InvalidGroup.Duplicate' in str(e):
            print("Security group already exists. Retrieving existing group ID.")
            existing_group = ec2.describe_security_groups(
                GroupNames=['ece326-group-19']
            )
            security_group_id = existing_group['SecurityGroups'][0]['GroupId']
        else:
            # Raise any other errors
            raise e

    return security_group_id

security_group_id = create_security_group()

def launch_instance(security_group_id):
    instance = ec2.run_instances(
        ImageId='ami-042e8287309f5df03',  
        InstanceType='t2.micro',
        KeyName='ece326_key',
        MinCount=1,
        MaxCount=1,
        SecurityGroupIds=[security_group_id]
    )['Instances'][0]

    instance_id = instance['InstanceId']
    print("Launching EC2 instance with ID:", instance_id)

    # Wait until the instance is running
    ec2.get_waiter('instance_running').wait(InstanceIds=[instance_id])
    print("Instance is now running")

    # Fetch and display the public IP
    instance_info = ec2.describe_instances(InstanceIds=[instance_id])
    public_ip = instance_info['Reservations'][0]['Instances'][0]['PublicIpAddress']
    print("EC2 Instance Public IP:", public_ip)

    return instance_id, public_ip

def allocate_elastic_ip(instance_id):
    # Allocate a new Elastic IP
    response = ec2.allocate_address(Domain='vpc')
    allocation_id = response['AllocationId']
    public_ip = response['PublicIp']
    print(f"Allocated Elastic IP: {public_ip}")

    # Associate the Elastic IP with the instance
    ec2.associate_address(InstanceId=instance_id, AllocationId=allocation_id)
    print(f"Associated Elastic IP {public_ip} with instance {instance_id}")
    return public_ip

def copy_files_to_instance(ip_address):
    try:
        # Setup SSH connection
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip_address, username='ubuntu', key_filename='ece326_key.pem')

        # Create SCP client
        with SCPClient(ssh.get_transport()) as scp:
            # Copy the entire frontend folder recursively
            scp.put('../frontend', '/home/ubuntu', recursive=True)  # Adjusted path to locate frontend

        print("Frontend folder copied successfully.")
    except Exception as e:
        print("Error during file copy:", e)

# Launch the instance using the security group ID
instance_id, public_ip = launch_instance(security_group_id)
elastic_ip = allocate_elastic_ip(instance_id)
print("Waiting for the instance to initialize...")
time.sleep(30)

copy_files_to_instance(elastic_ip)
print("Instance ID:", instance_id)
print("Public IP:", public_ip)
print("Persistent Public IP:", elastic_ip)



