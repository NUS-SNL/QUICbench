''' script to plot performance envelopes '''

import glob
import os
import sys
import argparse
import pandas as pd
import numpy as np
import math
import matplotlib.pyplot as plt
from scipy.spatial import ConvexHull, convex_hull_plot_2d
from scipy.interpolate import interp1d

sys.path.insert(1, os.path.join(sys.path[0], '..')) # allow importing from parent dir (repo)

from constants import *
from utils.files import read_json_as_dict
from stacks.chromium import Chromium
from stacks.msquic import Msquic
from stacks.mvfst import Mvfst
from stacks.quiche import Quiche
from stacks.tcp import Tcp

# DEFINING CONSTANTS:
# sampling threshold to remove outliers
THRESH=0.95
# sampling step as a multiple of RTT
STEP_RTT_MULT = 10

VALID_CC_ALGOS = ["cubic", "bbr", "reno"]
# default list of QUIC stacks to consider for plotting performance envelopes
DEFAULT_STACKS = {
    "cubic": [Chromium.NAME, Msquic.NAME, Mvfst.NAME, Quiche.NAME],
    "bbr": [Chromium.NAME, Mvfst.NAME],
    "reno": [Mvfst.NAME, Quiche.NAME],
}
REFERENCE_STACK = Tcp.NAME

PLOT_COLORS = {
    Tcp.NAME: "rv",
    Quiche.NAME: "ks",
    Chromium.NAME: "g^",
    Mvfst.NAME: "b.",
    Msquic.NAME: "mp"
}


def get_plot_perf_env_args():
    ''' define command line arguments '''
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", "-d", help="path to results dir",
                        type=str, required=True)
    parser.add_argument("--exp", "-e", help="name of experiment configuration",
                        type=str, required=True)
    parser.add_argument("--cc", "-c", help="congestion control algo to plot PEs for",
                        type=str, required=True, choices=VALID_CC_ALGOS)
    parser.add_argument("--stacks", "-s", help="stacks to consider for plotting PEs",
                        type=str, nargs="+")
    parser.add_argument("--smooth", "-sm", help="plot smoothened convex hull without points",
                        action='store_true')
    return parser.parse_args()


def get_stack_combi(exp_conf, test_stack, cc_algo):
    '''
    return stack combination dict in experiment config that corresponds to 
    desired PE experiment with test_stack and cc_algo

    The PE experiment is a two-flow experiment with a test QUIC flow and 
    a reference TCP flow
    '''
    for stack_combi in exp_conf["stacks_combinations"]:
        stacks = stack_combi["stacks"]
        test_flow_found = False
        ref_flow_found = False
        for s in stacks:
            if not test_flow_found and s["name"] == test_stack and s["cc_algo"].endswith(cc_algo):
                test_flow_found = True
                continue
            elif not ref_flow_found and s["name"] == REFERENCE_STACK and s["cc_algo"].endswith(cc_algo):
                ref_flow_found = True
                continue
        if test_flow_found and ref_flow_found and len(stacks) == 2:
            return stack_combi
    raise ValueError("experiment for test_stack {} cannot be found".format(test_stack))


def get_stacks_data(results_dir, exp_conf, stacks, cc_algo):
    '''
    Process each stack's PE experiment results and returns dictionary
    of stack name to its data of:
    - Set of points (throughput, delay) with outliers removed
    - Convex hull of points
    - Mean
    - Original set of points
    '''
    sample_interval = exp_conf["netem_conf"]["RTT_ms"] / 1000 * STEP_RTT_MULT
    data = {}

    for test_stack in stacks:
        stack_combi = get_stack_combi(exp_conf, test_stack, cc_algo)
        stack_results_dir = os.path.join(results_dir, stack_combi["name"])
        # get results from 1st trial
        pe_results_dir = os.path.join(stack_results_dir,
                                      list(glob.iglob(f"{stack_results_dir}/*"))[0])
        test_stack_d = [s for s in stack_combi["stacks"] if s["name"] == test_stack][0]
        test_stack_port_no = test_stack_d["port_no"]

        # get time series of (time, throughput, delay)
        time_series = []
        delay_df = pd.read_csv(os.path.join(pe_results_dir, test_stack_port_no + DELAY_TRACE_SUFFIX))
        tp_df = pd.read_csv(os.path.join(pe_results_dir, test_stack_port_no + THROUGHPUT_TRACE_SUFFIX))
        tp_times, tp_values, tp_len = tp_df.iloc[:,0], tp_df.iloc[:,1], len(tp_df.index)

        for index, row in delay_df.iterrows():
            time, delay = row.iloc[0], row.iloc[1]
            tp_idx = tp_times.searchsorted(time)
            tp = tp_values.iloc[tp_idx]
            time_series.append(list(map(float, (time, tp, delay))))

        # obtain points by sampling data every sample_interval
        points = []
        epoch = time_series[0][0]
        for time, tp, delay in time_series:
            if time >= epoch:
                points.append([tp, delay])
                epoch += sample_interval

        mean = list(np.mean(np.array(points), axis=0))
        #keep only THRESH % points closest to the mean
        hull_points = sorted(
            points,
            key=lambda p : math.pow(mean[0] - p[0], 2) + math.pow(mean[1] - p[1], 2)
        )
        hull_points = hull_points[:int(len(hull_points) * THRESH)]
        hull_points = np.array(hull_points)
        hull = ConvexHull(hull_points)

        data[test_stack] = (hull_points, hull, mean, points)

    return data


def plot_performance_envelopes(stacks_data, smooth_points, results_dir, cc_algo):
    '''
    Plot performance envelopes based on stacks data and report conformance and deviation
    '''
    # Helper functions
    def point_in_hull(point, hull, tolerance=1e-12):
        ''' https://stackoverflow.com/questions/16750618/whats-an-efficient-way-to-find-if-a-point-lies-in-the-convex-hull-of-a-point-cl '''
        return all(
            (np.dot(eq[:-1], point) + eq[-1] <= tolerance)
            for eq in hull.equations)


    plt.figure(figsize = (4, 4))

    # get control data
    control_data = stacks_data[REFERENCE_STACK]
    control_hull_points, control_hull, control_mean, control_points = control_data
    # sorted keys to make sure the legends are all in sorted order
    for test_stack in sorted(stacks_data.keys(), key = lambda x: -stacks_data[x][2][0]):
        test_data = stacks_data[test_stack]
        hull_points, hull, test_mean, points = test_data

        # Calculate deviation
        deviation = math.sqrt(
            math.pow(test_mean[0] - control_mean[0], 2) + math.pow(test_mean[1] - control_mean[1], 2)
        )
        deviation = round(deviation, 2)

        # Calculate conformance
        total_points = len(hull_points.tolist()) + len(control_hull_points.tolist())
        in_points = 0
        for p in hull_points.tolist():
            if point_in_hull(p, control_hull):
                in_points += 1
        for q in control_hull_points.tolist():
            if point_in_hull(q, hull):
                in_points += 1
        conformance = round(in_points / total_points, 2)

        # Plot performance envelopes
        plt_format = PLOT_COLORS[test_stack]
        x = hull_points[hull.vertices, 1]
        y = hull_points[hull.vertices, 0]        
        if smooth_points:
            t = np.arange(len(x))
            ti = np.linspace(0, t.max(), 10 * t.size)
            xi = interp1d(t, x, kind=cc_algo)(ti)
            yi = interp1d(t, y, kind=cc_algo)(ti)
            plt.fill(
                xi, yi, plt_format[0],
                label = f"{test_stack} Conformance={conformance} Deviation={deviation}",
                alpha=0.4
            )
        else:
            plt.fill(x, y, plt_format[0], alpha=0.3)
            plt.plot([item[1] for item in points], [item[0] for item in points], plt_format, label = test_stack)
            for simplex in hull.simplices:
                plt.plot(hull_points[simplex, 1], hull_points[simplex, 0], plt_format[0]+'-')
    
    plt.xlabel="Delay (ms)"
    plt.ylabel="Throughput (Mbps)"
    plt.legend()
    plt.savefig(os.path.join(results_dir, cc_algo + "-perf-env.png"))


def main():
    args = get_plot_perf_env_args()
    exp_conf = read_json_as_dict(os.path.join(args.dir, args.exp))
    
    stacks = args.stacks if args.stacks else DEFAULT_STACKS[args.cc]
    stacks.append(REFERENCE_STACK)
    stacks_data = get_stacks_data(args.dir, exp_conf, stacks, args.cc)

    plot_performance_envelopes(stacks_data, args.smooth, args.dir, args.cc)


if __name__ == "__main__":
    main()
