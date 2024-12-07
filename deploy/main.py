import infra
import remote
import cleanup
import sys
from constants import *
from utils import get_path

if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "cleanup":
        with open(get_path('configs/nat_gateway_id.txt'), 'r') as f:
            nat_gateway_id = f.read().strip()
        with open(get_path('configs/private_subnet_id.txt'), 'r') as f:
            private_subnet_id = f.read().strip()
        with open(get_path('configs/elastic_ip_aloc_id.txt'), 'r') as f:
            elastic_ip_alloc_id = f.read().split()
        key_names = [WORKERS_SG_NAME, PROXY_SG_NAME, TRUSTEDHOST_SG_NAME, GATEKEEPER_SG_NAME, BASTION_SG_NAME]           # Should be deleted in this order.
        cleanup.cleanup(key_names, nat_gateway_id, private_subnet_id, elastic_ip_alloc_id)

    elif not args:

        bastion_info, workers_info, proxy_info, gatekeeper_info, trustedhost_info = infra.deploy()
        
        remote.bootstrap_instance(f"{CONFIGS_PATH}/{KEY_PAIR_NAME}.pem", gatekeeper_info[0]["Private IP"], bastion_info[0]["DNS"], "gatekeeper")
        remote.bootstrap_instance(f"{CONFIGS_PATH}/{KEY_PAIR_NAME}.pem", proxy_info[0]["Private IP"], bastion_info[0]["DNS"], "proxy")
        remote.bootstrap_instance(f"{CONFIGS_PATH}/{KEY_PAIR_NAME}.pem", trustedhost_info[0]["Private IP"], bastion_info[0]["DNS"], "trustedhost")
        for worker in workers_info:                                                                                                
            remote.bootstrap_instance(f"{CONFIGS_PATH}/{KEY_PAIR_NAME}.pem", worker["Private IP"],  bastion_info[0]["DNS"], "worker")
        