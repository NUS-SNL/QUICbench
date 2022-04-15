import os
import sys
import json
import argparse
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(1, os.path.join(sys.path[0], '..')) # allow importing from parent dir (repo)

from utils.files import read_json_as_dict
from constants import *
from stacks.chromium import Chromium
from stacks.msquic import Msquic
from stacks.mvfst import Mvfst
from stacks.quiche import Quiche
from stacks.tcp import Tcp
from plot_tp_delay_scatter import CC_ALGOS, stack_color_map, get_tp_delay_trace_df, get_avg_values


CC_ALGOS = ["cubic", "reno", "bbr"]
stack_color_map = {
    (Chromium.NAME, Chromium.CUBIC): 'tab:blue',
    (Chromium.NAME, Chromium.BBR): 'tab:blue',
    (Chromium.NAME, Chromium.BBRV2): 'midnightblue',
    (Msquic.NAME, Msquic.CUBIC): 'tab:orange',
    (Mvfst.NAME, Mvfst.CUBIC): 'tab:red',
    (Mvfst.NAME, Mvfst.BBR): 'tab:red',
    (Mvfst.NAME, Mvfst.RENO): 'tab:red',
    (Quiche.NAME, Quiche.CUBIC): 'tab:purple',
    (Quiche.NAME, Quiche.RENO): 'tab:purple',
    (Tcp.NAME, Tcp.CUBIC): 'tab:green',
    (Tcp.NAME, Tcp.BBR): 'tab:green',
    (Tcp.NAME, Tcp.RENO): 'tab:green'
}


def get_traces_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", "-r", help="path to results dir", type=str)
    parser.add_argument("--exp_conf", "-e", help="name of experiment configuration", type=str)
    return parser.parse_args()


def plot_two_flows_tp_by_cc(two_flows_results_dir, exp_conf_name):
    """
    Plot two flows traces, grouped by congestion control algo
    and using tcp as the control stack
    """
    exp_conf_path = os.path.join(two_flows_results_dir, exp_conf_name)
    exp_conf = read_json_as_dict(exp_conf_path)
    bandwidth = exp_conf["netem_conf"]["bandwidth_Mbps"]
    num_trials = exp_conf["num_trials"]

    for trial_no in range(num_trials):
        for cc_algo in CC_ALGOS:
            # plot for each algo
            plt.clf()
            
            plotted_avg_throughputs = []
            i = 0
            for stack_combi in exp_conf["stacks_combinations"]:
                stacks = stack_combi["stacks"]
                num_tcp = sum([1 if s["name"] == Tcp.NAME else 0 for s in stacks])
                num_cc = sum([1 if cc_algo in s["cc_algo"] else 0 for s in stacks])
                if num_tcp == 0 or num_cc != 2: # experiment must have 1 tcp flow as control and both running the same cc
                    continue

                quic_stack = stacks[0] if stacks[0]["name"] != Tcp.NAME else stacks[1]
                
                stack_combi_dir = os.path.join(two_flows_results_dir, stack_combi["name"])
                trial_dir = os.path.join(stack_combi_dir, os.listdir(stack_combi_dir)[trial_no]) # take trial no.

                port_no = quic_stack["port_no"]
                tp_trace, delay_trace = get_tp_delay_trace_df(trial_dir, port_no)
                times, throughputs = tp_trace.iloc[:,0], tp_trace.iloc[:,1]

                stack_name, stack_cc = quic_stack["name"], quic_stack["cc_algo"]
                plt.plot(times, throughputs, label="{}-{}".format(stack_name, stack_cc), color=stack_color_map[(stack_name, stack_cc)],
                         linewidth=1)

                avg_throughput, avg_delay = get_avg_values(tp_trace, delay_trace)
                plotted_avg_throughputs.append((avg_throughput, i))
                i += 1
            
            # reorder legend labels by avg throughputs
            handles, labels = plt.gca().get_legend_handles_labels()
            order = list(map(lambda x : x[1], reversed(sorted(plotted_avg_throughputs))))
            plt.legend([handles[idx] for idx in order], [labels[idx] for idx in order])

            plt.ylabel("throughput (Mbps)")
            plt.ylim(0, bandwidth + 2)
            plt.xlabel("time (s)")

            plot_path = os.path.join(two_flows_results_dir, "trial{}-2f-tp-trace-{}".format(trial_no, cc_algo))

            plt.savefig(plot_path)


def main():
    args = get_traces_args()
    results_dir, exp_conf_name = args.results, args.exp_conf
    plot_two_flows_tp_by_cc(results_dir, exp_conf_name)


if __name__ == "__main__":
    main()
