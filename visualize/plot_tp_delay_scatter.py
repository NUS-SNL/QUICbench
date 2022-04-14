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


CC_ALGOS = ["cubic", "reno", "bbr"]


def get_tp_delay_scatter_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", "-r", help="path to results dir", type=str)
    parser.add_argument("--exp_conf", "-e", help="name of experiment configuration", type=str)
    parser.add_argument("--type", "-t", help="'s' for single flows, 't' for two flows", type=str)
    return parser.parse_args()


def get_tp_delay_trace_df(trial_dir, port_no):
    tp_trace_path = os.path.join(trial_dir, port_no + THROUGHPUT_TRACE_SUFFIX)
    delay_trace_path = os.path.join(trial_dir, port_no + DELAY_TRACE_SUFFIX)
    return pd.read_csv(tp_trace_path), pd.read_csv(delay_trace_path)


def get_scatter_data(tp_df, delay_df, sample_interval, start_from = None, end_by = None):
    delay_times = delay_df.iloc[:,0]
    delay_values = delay_df.iloc[:,1]
    delay_len = len(delay_df.index)

    y_tps = []
    x_delays = []
    prev_time = 0
    for index, row in tp_df.iterrows():
        time, throughput = row.iloc[0], row.iloc[1]
        if (start_from and time < start_from) or (end_by and time > end_by): # truncate trace
            continue
        if (time - prev_time) < sample_interval:
            continue
        prev_time = time

        idx = delay_times.searchsorted(time)
        if idx >= delay_len:
            break

        delay_time = delay_times.iloc[idx]
        delay_val = delay_values.iloc[idx]

        x_delays.append(delay_val)
        y_tps.append(throughput)

    return x_delays, y_tps


def plot_single_flow_by_cc(single_flow_results_dir, exp_conf_name):
    """
    Plot single flow throughput delay scatter plot, grouped by congestion control algo
    """
    exp_conf_path = os.path.join(single_flow_results_dir, exp_conf_name)
    exp_conf = read_json_as_dict(exp_conf_path)
    sample_interval = exp_conf["netem_conf"]["RTT_ms"] * 10 / 1000 # 10 RTT sample interval
    num_trials = exp_conf["num_trials"]

    for trial_no in range(num_trials):
        for cc_algo in CC_ALGOS:
            # plot for each algo
            plt.clf()
            for stack_combi in exp_conf["stacks_combinations"]:
                stack = stack_combi["stacks"][0] # single flow
                if cc_algo not in stack["cc_algo"]:
                    continue

                stack_combi_dir = os.path.join(single_flow_results_dir, stack_combi["name"])
                trial_dir = os.path.join(stack_combi_dir, os.listdir(stack_combi_dir)[trial_no]) # take 1 trial only

                port_no = stack["port_no"]
                tp_trace, delay_trace = get_tp_delay_trace_df(trial_dir, port_no)

                x_delays, y_tps = get_scatter_data(tp_trace, delay_trace, sample_interval)
                plt.scatter(x_delays, y_tps, label="{}-{}".format(stack["name"], stack["cc_algo"]), alpha=0.2)
            plt.legend()
            plt.ylabel("throughput (Mbps)")
            plt.xlabel("delay (ms)")

            plot_path = os.path.join(single_flow_results_dir, "trial{}-tp-delay-scatter-{}".format(trial_no, cc_algo))

            plt.savefig(plot_path)


def plot_two_flows_by_cc(two_flows_results_dir, exp_conf_name):
    """
    Plot two flows throughput delay scatter plot, grouped by congestion control algo
    and using tcp as the control stack
    """    
    exp_conf_path = os.path.join(two_flows_results_dir, exp_conf_name)
    exp_conf = read_json_as_dict(exp_conf_path)
    sample_interval = exp_conf["netem_conf"]["RTT_ms"] * 10 / 1000 # 10 RTT sample interval
    bandwidth = exp_conf["netem_conf"]["bandwidth_Mbps"]
    flow_duration_s = exp_conf["flow_duration_s"]
    num_trials = exp_conf["num_trials"]

    for trial_no in range(num_trials):
        for cc_algo in CC_ALGOS:
            # plot for each algo
            plt.clf()
            
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

                x_delays, y_tps = get_scatter_data(tp_trace, delay_trace, sample_interval, flow_duration_s / 10, flow_duration_s - flow_duration_s / 10)
                stack_name, stack_cc = quic_stack["name"], quic_stack["cc_algo"]
                plt.scatter(x_delays, y_tps, label="{}-{}".format(stack_name, stack_cc), alpha=0.2)
            
            plt.legend()
            plt.ylabel("throughput (Mbps)")
            plt.ylim(0, bandwidth + 2)
            plt.xlabel("delay (ms)")

            plot_path = os.path.join(two_flows_results_dir, "trial{}-2f-tp-delay-scatter-{}".format(trial_no, cc_algo))

            plt.savefig(plot_path)


def main():
    args = get_tp_delay_scatter_args()
    results_dir, exp_conf_name = args.results, args.exp_conf
    if args.type == "s":
        plot_single_flow_by_cc(results_dir, exp_conf_name)
    else:
        plot_two_flows_by_cc(results_dir, exp_conf_name)


if __name__ == "__main__":
    main()
