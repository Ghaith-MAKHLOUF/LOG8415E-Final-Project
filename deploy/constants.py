from botocore.config import Config
import os

# Configurations
CONFIGS_PATH = "configs"
KEY_PAIR_NAME = "FinalProject"
BASTION_SG_NAME = "bastion_group"
GATEKEEPER_SG_NAME = "gatekeeper_group"
TRUSTEDHOST_SG_NAME = "trustedhost_group"
PROXY_SG_NAME = "proxy_group"
WORKERS_SG_NAME = "workers_group"
WORKERS_INFO_PATH = CONFIGS_PATH + "/instance_info_workers.json"
PROXY_INFO_PATH = CONFIGS_PATH + "/instance_info_proxy.json"
GATEKEEPER_INFO_PATH = CONFIGS_PATH + "/instance_info_gatekeeper.json"
TRUSTEDHOST_INFO_PATH = CONFIGS_PATH + "/instance_info_trustedhost.json"
NAT_GATEWAY_ID_PATH = CONFIGS_PATH + "/nat_gateway_id.txt"
PRIVATE_SUBNET_ID_PATH = CONFIGS_PATH + "/private_subnet_id.txt"
ELASTIC_IP_ALLOC_ID_PATH = CONFIGS_PATH + "/elastic_ip_aloc_id.txt"
BASTION_INFO_PATH = CONFIGS_PATH + "/instance_info_bastion.json"

# Scripts
SCRIPTS = "scripts"
WORKER_SCRIPT_PATH = SCRIPTS + "/bootstrap_worker.sh"
PROXY_SCRIPT_PATH = SCRIPTS + "/bootstrap_proxy.sh"
GATEKEEPER_SCRIPT_PATH = SCRIPTS + "/bootstrap_gatekeeper.sh"
TRUSTEDHOST_SCRIPT_PATH = SCRIPTS + "/bootstrap_trustedhost.sh"

# BOTO3 Configs
REGION = "us-east-1"
BOTO3_CONFIG = Config(region_name=REGION)