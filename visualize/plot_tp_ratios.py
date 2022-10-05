'''
script to plot heatmap of throughput ratios when 
2 flows compete at a common bottleneck
'''

import csv
import os
import sys
import argparse
import numpy as np
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


# DEFINING CONSTANTS:
AVG_TP_FIELD = "avg_tp"
# stacks to consider for plotting throughput ratios
ALL_STACKS = [
    (Mvfst.NAME, Mvfst.CUBIC),
    (Mvfst.NAME, Mvfst.BBR),
    (Mvfst.NAME, Mvfst.RENO),    
    (Msquic.NAME, Msquic.CUBIC),
    (Chromium.NAME, Chromium.CUBIC),
    (Chromium.NAME, Chromium.BBR),
    (Chromium.NAME, Chromium.BBRV2),
    (Quiche.NAME, Quiche.CUBIC),
    (Quiche.NAME, Quiche.RENO),
    (Tcp.NAME, Tcp.CUBIC),
    (Tcp.NAME, Tcp.BBR),
    (Tcp.NAME, Tcp.RENO)
]


def get_plot_tp_ratios_args():
    ''' define command line arguments '''
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", "-d", help="path to results dir",
                        type=str, required=True)
    parser.add_argument("--exp", "-e", help="name of experiment configuration",
                        type=str, required=True)
    return parser.parse_args()


def get_trace_avg_throughput(trial_dir, port_no):
    ''' returns average throughput of throughput trace of flow with port_no in trial_dir '''
    tp_trace_path = os.path.join(trial_dir, port_no + THROUGHPUT_TRACE_SUFFIX)
    df = pd.read_csv(tp_trace_path)
    return df["throughput (Mbps)"].mean()


def get_stack_combis_avg_tps(two_flows_results_dir, exp_conf_name):
    '''
    get stack combis added with each stack's average throughput
    '''
    exp_conf = read_json_as_dict(
        os.path.join(two_flows_results_dir, exp_conf_name)
    )
    stack_combinations = exp_conf["stacks_combinations"]
    num_trials = exp_conf["num_trials"]
    
    for stack_combi in stack_combinations:
        stack_combi_dir = os.path.join(two_flows_results_dir, stack_combi["name"])
        for trial_dirname in os.listdir(stack_combi_dir):
            trial_dir = os.path.join(stack_combi_dir, trial_dirname)

            for stack in stack_combi["stacks"]:
                port_no = stack["port_no"]
                if AVG_TP_FIELD not in stack:
                    stack[AVG_TP_FIELD] = []
                stack[AVG_TP_FIELD].append(get_trace_avg_throughput(trial_dir, port_no))
                
    return stack_combinations


def get_stacks_to_tpratio(stack_combinations_with_avgtp):
    '''
    returns map of 2-flows experiment to the throughput ratio given stack_combinations_with_avgtp
    '''
    def get_stack_hash(stack):
        return (stack["name"], stack["cc_algo"])
    def get_stack_avgtp(stack):
        return sum(stack[AVG_TP_FIELD]) / len(stack[AVG_TP_FIELD])

    stacks_to_tpratio = {}
    for stack_combi in stack_combinations_with_avgtp:
        assert len(stack_combi["stacks"]) == 2
        stack1 = stack_combi["stacks"][0]
        stack2 = stack_combi["stacks"][1]
        stack1_hash, stack1_avgtp = get_stack_hash(stack1), get_stack_avgtp(stack1)
        stack2_hash, stack2_avgtp = get_stack_hash(stack2), get_stack_avgtp(stack2)
        total_avgtp = stack1_avgtp + stack2_avgtp

        stacks_to_tpratio[(stack1_hash, stack2_hash)] = round(stack1_avgtp / total_avgtp, 5)
        stacks_to_tpratio[(stack2_hash, stack1_hash)] = round(stack2_avgtp / total_avgtp, 5)
    return stacks_to_tpratio


def get_tpratios_table(stacks_to_tpratio, stacks):
    ''' returns raw data of tp ratios given stacks '''
    n = len(stacks)
    cells = [[None for j in range(n)] for i in range(n)]
    for i in range(n):
        for j in range(n):
            stack1 = stacks[i]
            stack2 = stacks[j]
            cells[i][j] = stacks_to_tpratio[(stack1, stack2)]
    return cells


def plot_heatmap(tp_ratios_table, row_labels, col_labels, ax=None, cbar_kw=None, cbarlabel="", **kwargs):
    if ax is None:
        ax = plt.gca()

    if cbar_kw is None:
        cbar_kw = {}

    # Plot the heatmap
    im = ax.imshow(tp_ratios_table, **kwargs)

    # Create colorbar
    cbar = ax.figure.colorbar(im, ax=ax, **cbar_kw)
    cbar.ax.set_ylabel(cbarlabel, rotation=-90, va="bottom")

    # Show all ticks and label them with the respective list entries.
    ax.set_xticks(np.arange(tp_ratios_table.shape[1]), labels=col_labels)
    ax.set_yticks(np.arange(tp_ratios_table.shape[0]), labels=row_labels)

    # Let the horizontal axes labeling appear on top.
    ax.tick_params(top=True, bottom=False,
                   labeltop=True, labelbottom=False)

    # Rotate the tick labels and set their alignment.
    plt.setp(ax.get_xticklabels(), rotation=-30, ha="right",
             rotation_mode="anchor")

    # Turn spines off and create white grid.
    ax.spines[:].set_visible(False)

    ax.set_xticks(np.arange(tp_ratios_table.shape[1]+1)-.5, minor=True)
    ax.set_yticks(np.arange(tp_ratios_table.shape[0]+1)-.5, minor=True)
    ax.grid(which="minor", color="w", linestyle='-', linewidth=1)
    ax.tick_params(which="minor", bottom=False, left=False)

    return im, cbar


def main():
    args = get_plot_tp_ratios_args()
    # get tp_ratios_table
    stack_combinations_with_avgtp = get_stack_combis_avg_tps(args.dir, args.exp)
    stacks_to_tpratio = get_stacks_to_tpratio(stack_combinations_with_avgtp)
    tp_ratios_table = get_tpratios_table(stacks_to_tpratio, ALL_STACKS)
    
    labels = [f"{s} {c}" for s, c in ALL_STACKS]
    # save tp_ratios_table
    output_file = os.path.join(args.dir, "tpratios_xy_matrix.csv")
    with open(output_file, 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow([' '] + labels)
        for i in range(len(ALL_STACKS)):
            csv_writer.writerow([labels[i]] + tp_ratios_table[i])    

    # plot heatmap
    tp_ratios_table = np.transpose(np.array(tp_ratios_table))    
    fig, ax = plt.subplots()
    im, cbar = plot_heatmap(np.array(tp_ratios_table), labels, labels, ax=ax,
                            cmap="viridis", cbarlabel="Throughput Ratio")
    fig.tight_layout()
    plt.savefig(os.path.join(args.dir, "tpratios_heatmap.png"))


if __name__ == "__main__":
    main()
