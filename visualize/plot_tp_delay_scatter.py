import os
import sys
import json
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(1, os.path.join(sys.path[0], '..')) # allow importing from parent dir (repo)

from utils.files import read_json_as_dict
from constants import *


CC_ALGOS = ["cubic", "reno", "bbr"]


def get_scatter_data(tp_df, delay_df, sample_interval):
    delay_times = delay_df.iloc[:,0]
    delay_values = delay_df.iloc[:,1]
    delay_len = len(delay_df.index)

    y_tps = []
    x_delays = []
    prev_time = 0
    for index, row in tp_df.iterrows():
        time, throughput = row.iloc[0], row.iloc[1]
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

    for cc_algo in CC_ALGOS:
        # plot for each algo
        plt.clf()
        for stack_combi in exp_conf["stacks_combinations"]:
            stack = stack_combi["stacks"][0] # single flow
            if cc_algo not in stack["cc_algo"]:
                continue

            stack_combi_dir = os.path.join(single_flow_results_dir, stack_combi["name"])
            trial_dir = os.path.join(stack_combi_dir, os.listdir(stack_combi_dir)[0]) # take 1 trial only

            port_no = stack["port_no"]
            tp_trace_path = os.path.join(trial_dir, port_no + THROUGHPUT_TRACE_SUFFIX)
            delay_trace_path = os.path.join(trial_dir, port_no + DELAY_TRACE_SUFFIX)

            x_delays, y_tps = get_scatter_data(pd.read_csv(tp_trace_path), pd.read_csv(delay_trace_path), sample_interval)
            plt.scatter(x_delays, y_tps, label="{}-{}".format(stack["name"], stack["cc_algo"]), alpha=0.2)
        plt.legend()
        plt.ylabel("throughput (Mbps)")
        plt.xlabel("delay (ms)")

        plot_path = os.path.join(single_flow_results_dir, "tp-delay-scatter-{}".format(cc_algo))

        plt.savefig(plot_path)


def main():
    results_dir, exp_conf_name = sys.argv[1], sys.argv[2]
    plot_single_flow_by_cc(results_dir, exp_conf_name)


if __name__ == "__main__":
    main()
