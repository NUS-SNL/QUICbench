'''
script to get total order of throughput ratios when
2 flows compete at a common bottleneck
'''

import os
import sys
from collections import deque

sys.path.insert(1, os.path.join(sys.path[0], '..')) # allow importing from parent dir (repo)

from visualize.plot_tp_ratios import *

# DEFINING CONSTANTS:
# define margin for error in tp_ratios
EPS = 0.05
# stacks to consider for analyzing transitivity
ALL_STACKS = [
    (Mvfst.NAME, Mvfst.CUBIC),
    (Mvfst.NAME, Mvfst.BBR),
    (Mvfst.NAME, Mvfst.RENO),
    # Can only get transitivity for all stacks without msquic,
    # as the performance of msquic is not consistent across trials
    # (Msquic.NAME, Msquic.CUBIC),
    (Chromium.NAME, Chromium.CUBIC),
    (Chromium.NAME, Chromium.BBR),
    (Chromium.NAME, Chromium.BBRV2),
    (Quiche.NAME, Quiche.CUBIC),
    (Quiche.NAME, Quiche.RENO),
    (Tcp.NAME, Tcp.CUBIC),
    (Tcp.NAME, Tcp.BBR),
    (Tcp.NAME, Tcp.RENO)
]


def get_plot_transitivity_args():
    ''' define command line arguments '''
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", "-d", help="path to results dir",
                        type=str, required=True)
    parser.add_argument("--exp", "-e", help="name of experiment configuration",
                        type=str, required=True)
    return parser.parse_args()


def detect_cycle(adj_list):
    '''
    detect cycle in the graph given by the adj_list 
    reference: https://www.geeksforgeeks.org/detect-cycle-in-a-graph/
    '''
    n = len(adj_list)
    visited = [False for _ in range(n)]
    rec_stack = [False for _ in range(n)]
    cycle = None
    def detect_cycle_helper(v, curr_nodes):
        nonlocal cycle
        visited[v] = True
        rec_stack[v] = True
        curr_nodes.append(v)
        for neigh in adj_list[v]:
            if not visited[neigh]:
                if detect_cycle_helper(neigh, curr_nodes):
                    return True
            elif rec_stack[neigh]:
                cycle = curr_nodes + [neigh]
                return True
        rec_stack[v] = False
        curr_nodes.pop()
        return False

    curr_nodes = []
    for i in range(len(adj_list)):
        if not visited[i]:
            if detect_cycle_helper(i, curr_nodes):
                return True, cycle
    return False, None


def topo_sort(adj_list):
    '''
    returns topological order of graph given by the adj_list
    reference: https://www.geeksforgeeks.org/topological-sorting-indegree-based-solution/
    '''
    n = len(adj_list)
    in_degree = [0 for _ in range(n)]
    for i in range(n):
        for j in adj_list[i]:
            in_degree[j] += 1
    
    queue = deque()
    for i in range(n):
        if in_degree[i] == 0:
            queue.append(i)
    
    count = 0
    topo_order = []
    while queue:
        u = queue.popleft()
        topo_order.append(u)
        count += 1

        for v in adj_list[u]:
            in_degree[v] -= 1
            if in_degree[v] == 0:
                queue.append(v)

    assert count == n
    return topo_order


def main():
    args = get_plot_transitivity_args()
    stacks = ALL_STACKS
    # get tp_ratios_table
    stack_combinations_with_avgtp = get_stack_combis_avg_tps(args.dir, args.exp)
    stacks_to_tpratio = get_stacks_to_tpratio(stack_combinations_with_avgtp)
    tp_ratios_table = get_tpratios_table(stacks_to_tpratio, stacks)

    # create adj_list from tp_ratios_table
    n = len(stacks)
    adj_list = [set() for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            # draw an edge from i to j if stack i lose to stack j
            if tp_ratios_table[i][j] <= (0.5 - EPS):
                adj_list[i].add(j)

    has_cycle, cycle = detect_cycle(adj_list)
    if has_cycle:
        cycle_w_labels = [
            f"{stacks[idx][0]}-{stacks[idx][1]}" for idx in cycle
        ]        
        raise ValueError(
            "there is no total ordering. Cycle found: " + ",".join(cycle_w_labels)
        )

    topo_order_idxs = topo_sort(adj_list)
    topo_order = [
        f"{stacks[idx][0]}-{stacks[idx][1]}\n" for idx in topo_order_idxs
    ]
    with open(os.path.join(args.dir, "topo-order"), "w") as f:
        f.writelines(["Topo order:\n"] + topo_order)


if __name__ == "__main__":
    main()
