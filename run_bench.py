import argparse
import json

from stacks.chromium import Chromium
from stacks.msquic import Msquic
from stacks.mvfst import Mvfst
from stacks.quiche import Quiche
from stacks.tcp import Tcp


def get_prog_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stacks_conf", "-s", help="path to stacks configuration", type=str, 
        default="./config/stacks_conf_default.json")
    parser.add_argument("--general_conf", "-k", help="path to general configuration", type=str,
        default="./config/general_conf_default.json")
    parser.add_argument("--exp_conf", "-e", help="path to experiment configuration", type=str)
    return parser.parse_args()


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


def main():
    args = get_prog_args()
    with open(args.stacks_conf) as f:
        stacks_conf = json.load(f)
    with open(args.general_conf) as f:
        general_conf = json.load(f)        

    stacks = init_stacks(stacks_conf, general_conf["server_ip"], general_conf["server_hostname"])


if __name__ == "__main__":
    main()
