import time
import paramiko
from utils import get_path
from constants import *
import json


def sftp_upload(sftp_client, file_path, remote_path):
    # Get file paths
    local_file_path = get_path(file_path)

    # Upload the file
    sftp_client.put(local_file_path, remote_path)
    print(f"Successfully uploaded files")
    

def upload_from_bastion_to_private(bastion_ip, private_ip, key_file, type):
    remote_directory = "/home/ubuntu"
    key_path = get_path(key_file)
    private_key = paramiko.RSAKey.from_private_key_file(key_path)

    # Set up SSH connection to Bastion Host
    bastion_client = paramiko.SSHClient()
    bastion_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    bastion_client.connect(bastion_ip, username='ubuntu', pkey=private_key)

    # SSH tunnel to private instance via Bastion
    bastion_transport = bastion_client.get_transport()
    dest_addr = (private_ip, 22)  # Private EC2 instance IP and SSH port
    local_addr = ('0.0.0.0', 0)
    
    # Separate SSH client for the private instance
    private_client = paramiko.SSHClient()
    private_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    timeout = 300
    end_time = time.time() + timeout
    while time.time() < end_time:
        try:
            tunnel = bastion_transport.open_channel('direct-tcpip', dest_addr, local_addr)
            private_client.connect(private_ip, username='ubuntu', pkey=private_key, sock=tunnel)
            print("SSH is available!")
            break
        except (paramiko.SSHException, Exception) as e:
            print(f"SSH not available yet: {e}")
            time.sleep(3)  # Wait before retrying
    
    # Use SFTP to upload the bash script to the private instance
    sftp_client = private_client.open_sftp()
   
    try:
        # Upload necessary files
        print("Uploading files for bootstrapping...")
        remote_directory = "/home/ubuntu/"
        if type == 'worker':
            sftp_upload(
                sftp_client, WORKER_SCRIPT_PATH, remote_directory + "/bootstrap_worker.sh"
            )
            command = "chmod +x bootstrap_worker.sh && ./bootstrap_worker.sh"

        elif type == 'proxy':
            sftp_upload(
                sftp_client, PROXY_SCRIPT_PATH, remote_directory + "/bootstrap_proxy.sh"
            )
            sftp_upload(sftp_client, WORKERS_INFO_PATH, "/home/ubuntu/instance_info_workers.json")
            sftp_upload(sftp_client, "../proxy/main.py", "/home/ubuntu/main.py")
            command = "chmod +x bootstrap_proxy.sh && nohup ./bootstrap_proxy.sh > bootstrap_proxy.log 2>&1 &"

        elif type == 'gatekeeper':
            sftp_upload(
                sftp_client, GATEKEEPER_SCRIPT_PATH, remote_directory + "/bootstrap_gatekeeper.sh"
            )
            sftp_upload(sftp_client, TRUSTEDHOST_INFO_PATH, "/home/ubuntu/instance_info_trustedhost.json")
            sftp_upload(sftp_client, "../gatekeeper/main.py", "/home/ubuntu/main.py")
            command = "chmod +x bootstrap_gatekeeper.sh && nohup ./bootstrap_gatekeeper.sh > bootstrap_gatekeeper.log 2>&1 &"

        elif type == 'trustedhost':
            sftp_upload(
                sftp_client, TRUSTEDHOST_SCRIPT_PATH, remote_directory + "/bootstrap_trustedhost.sh"
            )
            sftp_upload(sftp_client, PROXY_INFO_PATH, "/home/ubuntu/instance_info_proxy.json")
            sftp_upload(sftp_client, "../trustedhost/main.py", "/home/ubuntu/main.py")
            # Get the Gatekeeper IP and Proxy IP for security measures.
            with open(get_path('./configs/instance_info_gatekeeper.json'), 'r') as f:
                gatekeeper_data = json.load(f)
                gatekeeper_ip   = gatekeeper_data[0]['Private IP']
            with open(get_path('./configs/instance_info_proxy.json'), 'r') as f:
                proxy_data = json.load(f)
                proxy_ip   = proxy_data[0]['Private IP']
            command = f"chmod +x bootstrap_trustedhost.sh && nohup ./bootstrap_trustedhost.sh {gatekeeper_ip} {proxy_ip} > bootstrap_trustedhost.log 2>&1 &"
            

        # Execute bootstrap script
        print("Bootstrapping the instance...")
        # private_client.set_combine_stderr(True)
        stdin, stdout, stderr = private_client.exec_command(command)
        # Output ssh
        channel = stdout.channel  # Get the Channel object for monitoring

        # Wait for the command to complete and stream output
        while not channel.exit_status_ready():
            # Use select to check if there's data to read
            if channel.recv_ready():
                print(channel.recv(1024).decode("utf-8"), end="")  # Print command output

    except Exception as e:
        print("Failed to bootstrap instance: {e}")

    # Close SFTP and SSH connection
    sftp_client.close()
    private_client.close()
    bastion_client.close()
    bastion_transport.close()
    tunnel.close()


def bootstrap_instance(key_path, target_address, bastion_ip, type):
    upload_from_bastion_to_private(bastion_ip, target_address, key_path, type)
