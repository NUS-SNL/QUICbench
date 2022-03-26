import os
import sys
import argparse
import json
import subprocess

from stacks.chromium import Chromium
from stacks.msquic import Msquic
from stacks.mvfst import Mvfst
from stacks.quiche import Quiche
from stacks.tcp import Tcp
from utils.remote_cmd import get_remote_cmd, get_remote_cmd_sudo


def get_prog_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stacks_conf", "-s", help="path to stacks configuration", type=str, 
        default="./config/stacks_conf_default.json")
    parser.add_argument("--general_conf", "-k", help="path to general configuration", type=str,
        default="./config/general_conf_default.json")
    parser.add_argument("--exp_conf", "-e", help="path to experiment configuration", type=str)
    return parser.parse_args()


def check_sudo_privileges(server_hostname, server_pw_path):
    subprocess.run("sudo echo 'Got sudo privileges for local machine.'", shell=True, check=True)
    try:
        subprocess.run(get_remote_cmd_sudo(server_hostname, server_pw_path, "sudo echo 'Got sudo privileges for server machine.'"),
            shell=True, check=True, timeout=1)
    except subprocess.TimeoutExpired:
        sys.exit("exiting... server password is incorrect.")


def init_stacks(stacks_conf, server_ip, server_hostname):
    chromium_stack = Chromium(server_ip, server_hostname, **stacks_conf[Chromium.NAME])
    msquic_stack = Msquic(server_ip, server_hostname, **stacks_conf[Msquic.NAME])
    mvfst_stack = Mvfst(server_ip, server_hostname, **stacks_conf[Mvfst.NAME])
    quiche_stack = Quiche(server_ip, server_hostname, **stacks_conf[Quiche.NAME])
    tcp_stack = Tcp(server_ip, server_hostname)
    return {
        Chromium.NAME: chromium_stack,
        Msquic.NAME: msquic_stack,
        Mvfst.NAME: mvfst_stack,
        Quiche.NAME: quiche_stack,
        Tcp.NAME: tcp_stack
    }


def set_kernel_params(kernel_params, server_hostname, server_pw_path):
    print("Setting kernel parameters:")
    for param, value in kernel_params.items():
        subprocess.run("sudo sysctl -w {}=\"{}\"".format(param, value), shell=True, check=True)
        subprocess.run(get_remote_cmd_sudo(server_hostname, server_pw_path, "sudo sysctl -w {}=\\\"{}\\\"".format(param, value)), 
            shell=True, check=True)


def main():
    args = get_prog_args()
    with open(args.stacks_conf) as f:
        stacks_conf = json.load(f)
    with open(args.general_conf) as f:
        general_conf = json.load(f)
    
    server_ip, server_hostname, interface = general_conf["server_ip"], general_conf["server_hostname"], general_conf["interface"]
    server_pw_path = general_conf["server_pw_path"]    
    check_sudo_privileges(server_hostname, server_pw_path)
    
    stacks = init_stacks(stacks_conf, general_conf["server_ip"], general_conf["server_hostname"])
    set_kernel_params(general_conf["kernel_params"], server_hostname, server_pw_path)


if __name__ == "__main__":
    main()
