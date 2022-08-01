import os
import sys
import json
import argparse
import pandas as pd
import matplotlib.pyplot as plt
import csv

sys.path.insert(1, os.path.join(sys.path[0], '..')) # allow importing from parent dir (repo)

from utils.files import read_json_as_dict
from constants import *
from stacks.chromium import Chromium
from stacks.msquic import Msquic
from stacks.mvfst import Mvfst
from stacks.quiche import Quiche
from stacks.tcp import Tcp


AVG_TP_FIELD = "avg_tp"
ALL_STACKS = [
    (Chromium.NAME, Chromium.CUBIC),
    (Chromium.NAME, Chromium.BBR),
    (Chromium.NAME, Chromium.BBRV2),
    (Msquic.NAME, Msquic.CUBIC),
    (Mvfst.NAME, Mvfst.CUBIC),
    (Mvfst.NAME, Mvfst.BBR),
    (Mvfst.NAME, Mvfst.RENO),
    (Quiche.NAME, Quiche.CUBIC),
    (Quiche.NAME, Quiche.RENO),
    (Tcp.NAME, Tcp.CUBIC),
    (Tcp.NAME, Tcp.BBR),
    (Tcp.NAME, Tcp.RENO)
]

def get_avg_throughput(trial_dir, port_no):
    tp_trace_path = os.path.join(trial_dir, port_no + THROUGHPUT_TRACE_SUFFIX)
    df = pd.read_csv(tp_trace_path)
    return round(df["throughput (Mbps)"].mean(), 5)


def get_stack_combis_avg_tps(two_flows_results_dir, exp_conf_name):
    """
    get stack combis added with each stack's average throughput
    """
    exp_conf_path = os.path.join(two_flows_results_dir, exp_conf_name)
    exp_conf = read_json_as_dict(exp_conf_path)
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
                stack[AVG_TP_FIELD].append(get_avg_throughput(trial_dir, port_no))
                
    return stack_combinations


def get_stacks_to_tpratio(stack_combinations_with_avgtp):
    def get_stack_hash(stack):
        return (stack["name"], stack["cc_algo"])
    def get_stack_avgtp(stack):
        return sum(stack[AVG_TP_FIELD]) / len(stack[AVG_TP_FIELD])

    stacks_to_tpratio = {}
    for stack_combi in stack_combinations_with_avgtp:
        stack1 = stack_combi["stacks"][0]
        stack2 = stack_combi["stacks"][1]
        stack1_hash, stack1_avgtp = get_stack_hash(stack1), get_stack_avgtp(stack1)
        stack2_hash, stack2_avgtp = get_stack_hash(stack2), get_stack_avgtp(stack2)
        stacks_to_tpratio[(stack1_hash, stack2_hash)] = round(stack1_avgtp / stack2_avgtp, 5)
        stacks_to_tpratio[(stack2_hash, stack1_hash)] = round(stack2_avgtp / stack1_avgtp, 5)
    return stacks_to_tpratio


def get_tpratios_table(stacks_to_tpratio, stacks):
    n = len(stacks)
    cells = [[None for j in range(n)] for i in range(n)]
    for i in range(n):
        for j in range(n):
            stack1 = stacks[i]
            stack2 = stacks[j]
            cells[i][j] = str(stacks_to_tpratio[(stack1, stack2)])
    return cells


def plot_two_flows_tpratios(two_flows_results_dir, exp_conf_name):
    """
    plot 2d matrix showing all two flows experiment and their throughput ratios
    """
    stack_combinations_with_avgtp = get_stack_combis_avg_tps(two_flows_results_dir, exp_conf_name)
    stacks_to_tpratio = get_stacks_to_tpratio(stack_combinations_with_avgtp)
    cells = get_tpratios_table(stacks_to_tpratio, ALL_STACKS)
    
    n = len(ALL_STACKS)
    title_headers = ["{} {}".format(x[0], x[1]) for x in ALL_STACKS]
    output_file = os.path.join(two_flows_results_dir, "tpratios_matrix.csv")
    with open(output_file, 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow([' '] + title_headers)
        for i in range(n):
            csv_writer.writerow([title_headers[i]] + cells[i])


def main():
    results_dir, exp_conf_name = sys.argv[1], sys.argv[2]
    plot_two_flows_tpratios(results_dir, exp_conf_name)


if __name__ == "__main__":
    main()
