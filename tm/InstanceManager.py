import os
import boto3
import paramiko
import time
import atexit
import botocore.exceptions


class InstanceManager:
    def __init__(self, key_name, key_file, environment_configuration=False, instance_num=1, instance_type='c5.large', image_id='ami-0a47106e391391252',
                 username='ubuntu', home_directory='home/ubuntu/', security_group_ids=None):
        self.instances = []
        self.ssh_clients = {}
        self.environment_configuration = environment_configuration
        if environment_configuration:
            self.ec2 = boto3.resource('ec2', aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'], aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'], region_name=os.environ['AWS_DEFAULT_REGION'])
        else:
            self.ec2 = boto3.resource('ec2')
        self.key_name = key_name
        self.key_file = key_file
        self.security_group_ids = security_group_ids
        self.instance_num = instance_num
        self.instance_type = instance_type
        self.image_id = image_id
        self.username = username
        self.home_directory = home_directory
        self.security_group_ids = security_group_ids
        self.security_group_created = False
        atexit.register(self.cleanup)

    def cleanup(self):
        self.terminate_instances(wait_until_terminated=self.security_group_created)

        if self.security_group_created:
            self.delete_security_group()

    def __parse_instances(self, instances):
        if instances is None:
            return self.instances

        try:
            iter(instances)
        except TypeError:
            instances = [instances]

        for instance in instances:
            if instance not in self.instances:
                print('TypeError: Instances provided in parameters do not exist in InstanceManager object')
                raise TypeError

        return instances

    def create_security_group(self):
        try:
            security_group = self.ec2.create_security_group(GroupName='IMPAQ_HPC_TM',
                                                            Description='Used for HPC topic modeling')

            security_group.authorize_ingress(
                IpPermissions=[
                    {'IpProtocol': 'tcp',
                     'FromPort': 80,
                     'ToPort': 80,
                     'IpRanges': [{'CidrIp': '0.0.0.0/0'}],
                     'Ipv6Ranges': [{'CidrIpv6': '::/0'}]},
                    {'IpProtocol': 'tcp',
                     'FromPort': 22,
                     'ToPort': 22,
                     'IpRanges': [{'CidrIp': '0.0.0.0/0'}],
                     'Ipv6Ranges': [{'CidrIpv6': '::/0'}]}
                ])

            self.security_group_ids = [security_group.id]
            self.security_group_created = True
        except botocore.exceptions.ClientError as e:
            print('Security group already created')
            if 'InvalidGroup.Duplicate' in str(e):
                response = boto3.client('ec2').describe_security_groups(GroupNames=['IMPAQ_HPC_TM'])
                self.security_group_ids = [response['SecurityGroups'][0]['GroupId']]
            else:
                raise

    def delete_security_group(self):
        for security_group_id in self. security_group_ids:
            try:
                if self.environment_configuration:
                    boto3.client('ec2', aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'], aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'], region_name=os.environ['AWS_DEFAULT_REGION']).delete_security_group(GroupId=security_group_id)
                else:
                    boto3.client('ec2').delete_security_group(GroupId=security_group_id)
                print('Security group {} deleted'.format(security_group_id))
            except botocore.exceptions.ClientError as e:
                print(e)

    def create_instances(self, wait_for_running=True):
        if self.security_group_ids is None:
            self.create_security_group()

        self.instances = self.ec2.create_instances(
            ImageId=self.image_id,
            InstanceType=self.instance_type,
            MaxCount=self.instance_num,
            MinCount=self.instance_num,
            SecurityGroupIds=self.security_group_ids,
            KeyName=self.key_name
        )

        if wait_for_running:
            self.load_instances()

        return self.instances

    def load_instances(self):
        for instance in self.instances:
            instance.wait_until_running()
            instance.load()

    def connect_to_instances(self, instances=None, max_attempts=10):
        instances = self.__parse_instances(instances)

        for instance in instances:
            for connection_attempts in range(1, max_attempts + 1):
                try:
                    client = paramiko.SSHClient()
                    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    key = paramiko.RSAKey.from_private_key_file(self.key_file)
                    client.connect(hostname=instance.public_ip_address, username=self.username, pkey=key)

                    if instance.id in self.ssh_clients:
                        self.ssh_clients[instance.id].close()
                    self.ssh_clients[instance.id] = client
                    break
                except TimeoutError:
                    if connection_attempts == max_attempts:
                        raise

                    print('Connection attempt #{} for IP address {} timed out. Trying again...'
                          .format(connection_attempts, instance.public_ip_address))
                    time.sleep(10)
                except paramiko.ssh_exception.NoValidConnectionsError:
                    if connection_attempts == max_attempts:
                        raise

                    print('Connection attempt #{} for IP address {} failed. Trying again...'
                          .format(connection_attempts, instance.public_ip_address))
                    time.sleep(10)

    def terminate_instances(self, instances=None, wait_until_terminated=False):
        instances = self.__parse_instances(instances)

        for instance in instances:
            print('Terminating instance', instance.id)
            instance.terminate()

        if wait_until_terminated:
            for instance in instances:
                instance.wait_until_terminated()
                print('Instance', instance.id, 'terminated')

        self.close_instance_connections(instances, suppress_warning=True)

    def start_instances(self, instances=None, wait_until_running=True):
        instances = self.__parse_instances(instances)

        for instance in instances:
            print('Starting instance', instance.id)
            instance.start()

        if wait_until_running:
            for instance in instances:
                instance.wait_until_running()
                print('Instance', instance.id, 'running')

    def stop_instances(self, instances=None, wait_until_stopped=False):
        instances = self.__parse_instances(instances)

        for instance in instances:
            print('Terminating instance', instance.id)
            instance.stop()

        if wait_until_stopped:
            for instance in instances:
                instance.wait_until_stopped()
                print('Instance', instance.id, 'stopped')

        self.close_instance_connections(instances, suppress_warning=True)

    def close_instance_connections(self, instances=None, suppress_warning=False):
        instances = self.__parse_instances(instances)

        for instance in instances:
            try:
                self.ssh_clients[instance.id].close()
            except KeyError:
                if not suppress_warning:
                    print('Instance {} does not have an open SSH connection'.format(instance.id))

    def upload_file_to_instance(self, source_file, destination_file, instances=None):
        instances = self.__parse_instances(instances)

        for instance in instances:
            client = self.ssh_clients[instance.id]
            sftp = client.open_sftp()
            sftp.put(source_file, os.path.join(self.home_directory, destination_file))
            sftp.close()

    def download_file_from_instance(self, source_file, destination_file, instance):
        try:
            client = self.ssh_clients[instance.id]
            sftp = client.open_sftp()
            sftp.get(source_file, destination_file)
            sftp.close()
        except KeyError:
            print('KeyError: That instance does not have an open connection')
            raise

    def execute_command(self, command, instances=None):
        print('Executing:', command)
        instances = self.__parse_instances(instances)

        for instance in instances:
            client = self.ssh_clients[instance.id]
            stdin, stdout, stderr = client.exec_command(command)
            exit_status = stdout.channel.recv_exit_status()
            if exit_status == 0:
                for line in stdout.readlines():
                    print(line, end='')
            else:
                for line in stderr.readlines():
                    print(line, end='')

    def download_file_from_url(self, url, instances=None):
        command = 'wget {}'.format(url)
        self.execute_command(command, instances)
