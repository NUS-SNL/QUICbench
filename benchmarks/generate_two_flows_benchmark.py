"""
Script to help generate benchmark jsons for two flows experiments
"""
import os
import sys

sys.path.insert(1, os.path.join(sys.path[0], '..')) # allow importing from parent dir (repo)

from stacks.chromium import Chromium
from stacks.msquic import Msquic
from stacks.mvfst import Mvfst
from stacks.quiche import Quiche
from stacks.tcp import Tcp
from utils.files import dump_dict_as_json

stacks_kls = [Chromium, Msquic, Mvfst, Quiche, Tcp]

def main():
    BUFFER_BDP = 0.5

    all_stacks = []
    for stack_kls in stacks_kls:
        for cc_algo in stack_kls.get_cc_algos():
            all_stacks.append({ "name": stack_kls.NAME, "cc_algo": cc_algo })
    
    stacks_combinations = []
    for i in range(len(all_stacks)):
        for j in range(i, len(all_stacks)):
            stack1 = all_stacks[i]
            stack2 = all_stacks[j]
            stacks_combinations.append({
                "name": "{}-{}_{}-{}".format(stack1["name"], stack1["cc_algo"], stack2["name"], stack2["cc_algo"]),
                "stacks": [
                    { **stack1, **{ "port_no": "4000 "}},
                    { **stack2, **{ "port_no": "4001 "}}
                ]
            })

    exp_conf = {
        "experiment_name": "two-flows-normal-{}bdp".format(BUFFER_BDP),
        "experiment_results_dir": "/home/quic/quic_bench_results/two-flows-normal-{}bdp".format(BUFFER_BDP),
        "num_trials": 5,
        "netem_conf": {
            "RTT_ms": 50,
            "bandwidth_Mbps": 20,
            "buffer_bdp": BUFFER_BDP
        },
        "flow_duration_s": 120,
        "virtual_interface": "enp1s0f1-br0",
        "stacks_combinations": stacks_combinations
    }

    dump_dict_as_json(exp_conf, os.path.join(os.path.dirname(os.path.realpath(__file__)), exp_conf["experiment_name"] + ".json"))

if __name__ == "__main__":
    main()
    