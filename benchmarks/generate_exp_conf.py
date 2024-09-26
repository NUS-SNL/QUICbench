'''
helper script to generate experiments config for either:
1. Performance envelope experiments (2-flows exps with a test QUIC flow against a reference TCP flow)
2. Throughput ratios experiments (2-flows exps)
'''

import argparse
import os
import sys

sys.path.insert(1, os.path.join(sys.path[0], '..')) # allow importing from parent dir (repo)

from utils.files import read_json_as_dict, dump_dict_as_json
from stacks import *
from stacks.stack import Stack
from stacks.chromium import Chromium
from stacks.msquic import Msquic
from stacks.mvfst import Mvfst
from stacks.quiche import Quiche
from stacks.tcp import Tcp
from stacks.lsquic import Lsquic
from stacks.quicgo import QuicGo
from stacks.quicly import Quicly
from stacks.quinn import Quinn
from stacks.s2nquic import S2nQuic
from stacks.xquic import Xquic
from stacks.modified_stacks import *

# Define constants:
DEFAULT_PE_STACKS = [
    Chromium.NAME, Msquic.NAME, Mvfst.NAME, Quiche.NAME, ChromiumN1.NAME, MvfstPR100.NAME, ChromiumAF2.NAME, MvfstAF2.NAME, Tcp.NAME
]
DEFAULT_TPRATIOS_STACKS = [
    Chromium.NAME, Msquic.NAME, Mvfst.NAME, Quiche.NAME, Tcp.NAME
]
NEW_TPRATIOS_STACKS = [
    Lsquic.NAME, QuicGo.NAME, Quicly.NAME, Quinn.NAME, S2nQuic.NAME, Xquic.NAME
]

def get_subclasses(kls):
    for subclass in kls.__subclasses__():
        yield from get_subclasses(subclass)
        yield subclass

def get_stack_from_name(name):
    for kls in get_subclasses(Stack):
        if kls.NAME == name:
            return kls
    return None


def get_generate_exp_conf_args():
    ''' define command line arguments '''
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", "-b", help="path to base_conf",
                        type=str, required=True)
    parser.add_argument("--stacks", "-s", help="stacks to consider",
                        type=str, nargs="+")
    parser.add_argument("--type", "-t", help="type of exp_conf to generate (PE or tpratios)",
                        type=str, required=True, choices=("pe", "tp"))
    parser.add_argument("--name", "-n", help="name of experiment",
                        type=str, required=True)
    parser.add_argument("--rdir", "-r", help="path of experiment results dir",
                        type=str, required=True)
    return parser.parse_args()


def main():
    args = get_generate_exp_conf_args()
    new_stacks = NEW_TPRATIOS_STACKS
    all_stacks = NEW_TPRATIOS_STACKS + DEFAULT_TPRATIOS_STACKS

    
    def get_stack_w_cc(stacks):
        stacks_w_cc = []
        for stack in stacks:
            stack_kls = get_stack_from_name(stack)
            for cc_algo in stack_kls.get_cc_algos():
                stacks_w_cc.append({ "name": stack_kls.NAME, "cc_algo": cc_algo })
        return stacks_w_cc

    new_stacks_w_cc = get_stack_w_cc(new_stacks)
    all_stacks_w_cc = get_stack_w_cc(all_stacks)

    print(len(new_stacks_w_cc))
    print(new_stacks_w_cc)
    print(len(all_stacks_w_cc))    
    
    stacks_combinations = []
    for i in range(len(new_stacks_w_cc)):
        for j in range(i, len(all_stacks_w_cc)):
            stack1 = new_stacks_w_cc[i]
            stack2 = all_stacks_w_cc[j]
            if args.type == "pe" and not (stack2["name"] == Tcp.NAME and stack2["cc_algo"] in stack1["cc_algo"]):
                continue
            stacks_combinations.append({
                "name": "{}-{}_{}-{}".format(stack1["name"], stack1["cc_algo"], stack2["name"], stack2["cc_algo"]),
                "stacks": [
                    { **stack1, **{ "port_no": "4000" }},
                    { **stack2, **{ "port_no": "4001" }}
                ]
            })
    
    base_conf = read_json_as_dict(args.base)
    exp_conf = {
        "experiment_name": args.name,
        "experiment_results_dir": args.rdir,
        **base_conf,
        "stacks_combinations": stacks_combinations
    }
    
    dump_dict_as_json(
        exp_conf,
        os.path.join(os.path.dirname(os.path.realpath(__file__)), exp_conf["experiment_name"] + ".json")
    )
    

if __name__ == "__main__":
    main()
