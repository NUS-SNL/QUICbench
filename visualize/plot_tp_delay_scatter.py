import os
import sys
import json
import argparse
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import statistics
import math
import csv

sys.path.insert(1, os.path.join(sys.path[0], '..')) # allow importing from parent dir (repo)

from utils.files import read_json_as_dict
from constants import *
from stacks.chromium import Chromium
from stacks.msquic import Msquic
from stacks.mvfst import Mvfst
from stacks.quiche import Quiche
from stacks.tcp import Tcp


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


def get_tp_delay_scatter_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", "-r", help="path to results dir", type=str)
    parser.add_argument("--exp_conf", "-e", help="name of experiment configuration", type=str)
    parser.add_argument("--type", "-t", help="'s' for single flows, 't' for two flows, 'f' for five flows", type=str)
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


def get_avg_values(tp_df, delay_df):
    avg_throughput = tp_df.iloc[:,1].mean()
    avg_delay = delay_df.iloc[:,1].mean()
    return avg_throughput, avg_delay


def get_arr_avg(arr):
    if len(arr) == 0:
        return 0
    return round(sum(arr) / len(arr), 5)


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


def calc_and_save_stats(stats, cc_algo, save_path):
    class Rectangle:
        # Credits: https://stackoverflow.com/questions/27152904/calculate-overlapped-area-between-two-rectangles
        def __init__(self, xmin, ymin, xmax, ymax):
            self.xmin = xmin
            self.ymin = ymin
            self.xmax = xmax
            self.ymax = ymax

        def area(self):
            return (self.xmax - self.xmin) * (self.ymax - self.ymin)

        def intersection(self, b):
            dx = min(self.xmax, b.xmax) - max(self.xmin, b.xmin)
            dy = min(self.ymax, b.ymax) - max(self.ymin, b.ymin)
            return max(0, dx) * max(0, dy)


    base_stats = stats[(Tcp.NAME, cc_algo)]
    b_tmean, b_dmean, b_tstd, b_dstd = base_stats["tmean"], base_stats["dmean"], base_stats["tstd"], base_stats["dstd"]
    b_rect = Rectangle(b_dmean - b_dstd, b_tmean - b_tstd, b_dmean + b_dstd, b_tmean + b_tstd)

    headers = ["variant", "tmean", "dmean", "tstd", "dstd", "overlap", "dist"]
    rows = []
    for stack, stat in stats.items():
        stack_name, stack_cc = stack
        tmean, dmean, tstd, dstd = stat["tmean"], stat["dmean"], stat["tstd"], stat["dstd"]        
        
        rect = Rectangle(dmean - dstd, tmean - tstd, dmean + dstd, tmean + tstd)
        overlap = round(rect.intersection(b_rect) / rect.area(), 5)
        dist = round(math.dist((tmean, dmean), (b_tmean, b_dmean)), 5)
        
        label = stat["label"] if "label" in stat else "{}-{}".format(stack_name, stack_cc)
        row = [label, tmean, dmean, tstd, dstd, overlap, dist]
        rows.append(row)
    
    with open(save_path, 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(headers)
        csv_writer.writerows(rows)


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
            
            plotted_avg_throughputs = []
            i = 0
            stats = {}
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
                if stack_name != "tcp":
                    plt.scatter(x_delays, y_tps, label="{}".format(stack_name), alpha=0.2, color=stack_color_map[(stack_name, stack_cc)])
                else:
                    plt.scatter(x_delays, y_tps, label="{}".format("kernel"), alpha=0.2, color=stack_color_map[(stack_name, stack_cc)])

                avg_throughput, avg_delay = get_arr_avg(y_tps), get_arr_avg(x_delays)
                plt.scatter([avg_delay], [avg_throughput], color=stack_color_map[(stack_name, stack_cc)], marker="X")

                plotted_avg_throughputs.append((avg_throughput, i))
                i += 1

                # add stats
                if len(y_tps) == 0:
                    continue
                # add stats
                stats[(stack_name, stack_cc)] = {
                    "tmean": avg_throughput,
                    "dmean": avg_delay,
                    "tstd": round(statistics.stdev(y_tps), 5),
                    "dstd": round(statistics.stdev(x_delays), 5)
                }
            
            # reorder legend labels by avg throughputs
            handles, labels = plt.gca().get_legend_handles_labels()
            order = list(map(lambda x : x[1], reversed(sorted(plotted_avg_throughputs))))
            plt.legend([handles[idx] for idx in order], [labels[idx] for idx in order], prop={'size': 13.5})
            # plt.legend([handles[idx] for idx in order], [labels[idx] for idx in order])

            plt.ylabel("throughput (Mbps)", fontsize=13.5)
            plt.ylim(0, bandwidth + 2)
            # plt.xlim(0, exp_conf["netem_conf"]["RTT_ms"] * exp_conf["netem_conf"]["buffer_bdp"] + 2)
            plt.xlabel("delay (ms)", fontsize=13.5)

            plot_path = os.path.join(two_flows_results_dir, "trial{}-2f-tp-delay-scatter-{}".format(trial_no, cc_algo))

            plt.savefig(plot_path)

            stats_save_path = os.path.join(two_flows_results_dir, "trial{}-2f-tp-delay-stats-{}.csv".format(trial_no, cc_algo))
            calc_and_save_stats(stats, cc_algo, stats_save_path)


def plot_two_flows_mod_vs_o(mod_results_dir, exp_conf_name, stack_name, tcp_name, mod_label, orig_label):
    exp_conf_path = os.path.join(mod_results_dir, exp_conf_name)
    exp_conf = read_json_as_dict(exp_conf_path)
    sample_interval = exp_conf["netem_conf"]["RTT_ms"] * 10 / 1000 # 10 RTT sample interval
    bandwidth = exp_conf["netem_conf"]["bandwidth_Mbps"]
    flow_duration_s = exp_conf["flow_duration_s"]
    num_trials = exp_conf["num_trials"]

    for trial_no in range(1):
        # plot for each algo
        plt.clf()

        to_plot = []
        tcp_cc_algo = None
        for stack_combi in exp_conf["stacks_combinations"]:
            stacks = stack_combi["stacks"]
            stack = stacks[0] if stacks[0]["name"] != Tcp.NAME else stacks[1]
            if stack_combi["name"] == stack_name:
                to_plot.append((stack, stack_name, mod_label, "orange"))
                to_plot.append((stack, stack_name + "_o", orig_label, stack_color_map[(stack["name"], stack["cc_algo"])]))
            elif stack_combi["name"] == tcp_name:
                to_plot.append((stack, tcp_name, "Kernel", stack_color_map[(stack["name"], stack["cc_algo"])]))
                tcp_cc_algo = stack["cc_algo"]

        stats = {}
        for quic_stack, stack_combi_name, label, color in to_plot:
            stack_combi_dir = os.path.join(mod_results_dir, stack_combi_name)
            trial_dir = os.path.join(stack_combi_dir, os.listdir(stack_combi_dir)[trial_no]) # take trial no.

            port_no = quic_stack["port_no"]
            tp_trace, delay_trace = get_tp_delay_trace_df(trial_dir, port_no)

            x_delays, y_tps = get_scatter_data(tp_trace, delay_trace, sample_interval, flow_duration_s / 10, flow_duration_s - flow_duration_s / 10)
            plt.scatter(x_delays, y_tps, label=label, alpha=0.2, color=color)

            avg_throughput, avg_delay = get_arr_avg(y_tps), get_arr_avg(x_delays)
            plt.scatter([avg_delay], [avg_throughput], color=color, marker="X")

            # add stats
            if len(y_tps) == 0:
                continue
            stats[(label, quic_stack["cc_algo"])] = {
                "tmean": avg_throughput,
                "dmean": avg_delay,
                "tstd": round(statistics.stdev(y_tps), 5),
                "dstd": round(statistics.stdev(x_delays), 5),
                "label": label
            }        
        
        plt.legend(prop={'size': 13.5})
        plt.ylabel("throughput (Mbps)", fontsize=13.5)
        plt.ylim(0, bandwidth + 2)
        plt.xlabel("delay (ms)", fontsize=13.5)

        plot_path = os.path.join(mod_results_dir, "trial{}-2f-tp-delay-scatter-{}".format(trial_no, stack_name))

        plt.savefig(plot_path)

        stats_save_path = os.path.join(mod_results_dir, "trial{}-2f-tp-delay-stats-{}.csv".format(trial_no, stack_name))
        calc_and_save_stats(stats, tcp_cc_algo, stats_save_path)        


def plot_two_flows_mod_vs_o_hardcoded():
    for bdp in [0.5, 1, 3, 5]:
        plot_two_flows_mod_vs_o(
            "/home/quic/quic_bench_results/two-flows-modified1-{}bdp".format(bdp),
            "two-flows-modified1-{}bdp.json".format(bdp),
            "chromium-cubic_tcp-cubic",
            "tcp-cubic_tcp-cubic",
            "chromium-cubic (N=1)",
            "chromium-cubic (N=2)",
        )
        plot_two_flows_mod_vs_o(
            "/home/quic/quic_bench_results/two-flows-modified1-{}bdp".format(bdp),
            "two-flows-modified1-{}bdp.json".format(bdp),
            "mvfst-bbr_tcp-bbr",
            "tcp-bbr_tcp-bbr",
            "mvfst-bbr (scale 100%)",
            "mvfst-bbr (scale 120%)",
        )
        plot_two_flows_mod_vs_o(
            "/home/quic/quic_bench_results/two-flows-modified2-{}bdp".format(bdp),
            "two-flows-modified2-{}bdp.json".format(bdp),
            "chromium-cubic_tcp-cubic",
            "tcp-cubic_tcp-cubic",
            "chromium-cubic (ack freq 2)",
            "chromium-cubic (ack freq 10)",
        )
        plot_two_flows_mod_vs_o(
            "/home/quic/quic_bench_results/two-flows-modified2-{}bdp".format(bdp),
            "two-flows-modified2-{}bdp.json".format(bdp),
            "chromium-bbr_tcp-bbr",
            "tcp-bbr_tcp-bbr",
            "chromium-bbr (ack freq 2)",
            "chromium-bbr (ack freq 10)",
        )
        plot_two_flows_mod_vs_o(
            "/home/quic/quic_bench_results/two-flows-modified2-{}bdp".format(bdp),
            "two-flows-modified2-{}bdp.json".format(bdp),
            "chromium-bbrv2_tcp-bbr",
            "tcp-bbr_tcp-bbr",
            "chromium-bbrv2 (ack freq 2)",
            "chromium-bbrv2 (ack freq 10)",
        )
        plot_two_flows_mod_vs_o(
            "/home/quic/quic_bench_results/two-flows-modified2-{}bdp".format(bdp),
            "two-flows-modified2-{}bdp.json".format(bdp),
            "mvfst-cubic_tcp-cubic",
            "tcp-cubic_tcp-cubic",
            "mvfst-cubic (ack freq 2)",
            "mvfst-cubic (ack freq 10)",
        )        
        plot_two_flows_mod_vs_o(
            "/home/quic/quic_bench_results/two-flows-modified2-{}bdp".format(bdp),
            "two-flows-modified2-{}bdp.json".format(bdp),
            "mvfst-bbr_tcp-bbr",
            "tcp-bbr_tcp-bbr",
            "mvfst-bbr (ack freq 2)",
            "mvfst-bbr (ack freq 10)",
        )
        plot_two_flows_mod_vs_o(
            "/home/quic/quic_bench_results/two-flows-modified2-{}bdp".format(bdp),
            "two-flows-modified2-{}bdp.json".format(bdp),
            "mvfst-newreno_tcp-reno",
            "tcp-reno_tcp-reno",
            "mvfst-newreno (ack freq 2)",
            "mvfst-newreno (ack freq 10)",
        )        


def main():
    args = get_tp_delay_scatter_args()
    results_dir, exp_conf_name = args.results, args.exp_conf
    if args.type == "s":
        plot_single_flow_by_cc(results_dir, exp_conf_name)
    else:
        plot_two_flows_by_cc(results_dir, exp_conf_name)


if __name__ == "__main__":
    main()
    #plot_two_flows_mod_vs_o_hardcoded()
