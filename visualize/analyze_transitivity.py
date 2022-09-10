from plot_two_flows_tpratios import *


CUBIC_STACKS = [
    (Chromium.NAME, Chromium.CUBIC),
    # (Msquic.NAME, Msquic.CUBIC),
    (Mvfst.NAME, Mvfst.CUBIC),
    (Quiche.NAME, Quiche.CUBIC),
    (Tcp.NAME, Tcp.CUBIC)
]
BBR_STACKS = [
    (Chromium.NAME, Chromium.BBR),
    (Chromium.NAME, Chromium.BBRV2),
    (Mvfst.NAME, Mvfst.BBR),
    (Tcp.NAME, Tcp.BBR),
]
RENO_STACKS = [
    (Mvfst.NAME, Mvfst.RENO),
    (Quiche.NAME, Quiche.RENO),
    (Tcp.NAME, Tcp.RENO)
]

CHROMIUM_STACKS = [
    (Chromium.NAME, Chromium.CUBIC),
    (Chromium.NAME, Chromium.BBR),
    (Chromium.NAME, Chromium.BBRV2)
]
MVFST_STACKS = [
    (Mvfst.NAME, Mvfst.CUBIC),
    (Mvfst.NAME, Mvfst.BBR),
    (Mvfst.NAME, Mvfst.RENO)
]
TCP_STACKS = [
    (Tcp.NAME, Tcp.CUBIC),
    (Tcp.NAME, Tcp.BBR),
    (Tcp.NAME, Tcp.RENO)
]
QUICHE_STACKS = [
    (Quiche.NAME, Quiche.CUBIC),
    (Quiche.NAME, Quiche.RENO)
]

ALL_STACKS_WO_MSQUIC = [
    (Chromium.NAME, Chromium.CUBIC),
    (Chromium.NAME, Chromium.BBR),
    (Chromium.NAME, Chromium.BBRV2),
    (Mvfst.NAME, Mvfst.CUBIC),
    (Mvfst.NAME, Mvfst.BBR),
    (Mvfst.NAME, Mvfst.RENO),
    (Quiche.NAME, Quiche.CUBIC),
    (Quiche.NAME, Quiche.RENO),
    (Tcp.NAME, Tcp.CUBIC),
    (Tcp.NAME, Tcp.BBR),
    (Tcp.NAME, Tcp.RENO)
]



def analyze_transitivity_for_stacks(stacks_to_tpratio, stacks):
    cells = get_tpratios_table(stacks_to_tpratio, stacks)
    order = [' ' for _ in range(len(stacks))]
    order_map = {}

    # Determine index in total order for stack[i]
    for i in range(len(cells)):
        lower = []
        higher = []
        for j in range(len(cells)):
            if i == j:
                continue
            cell = float(cells[i][j])
            if cell < 0.95:
                higher.append(stacks[j])
            elif cell >= 0.95 and cell <= 1.05 and stacks[i] < stacks[j]:
                higher.append(stacks[j])
            else:
                lower.append(stacks[j])
        order_idx = len(lower)
        stack = stacks[i]
        if order[order_idx] != ' ':
            raise ValueError("Not transitive: i={},j={},stack={}".format(i, j, stacks[i]))
        order[order_idx] = stack
        order_map[stack] = order_idx

    # Verify that order makes sense
    for i in range(len(cells)):
        lower = []
        higher = []
        for j in range(len(cells)):
            if i == j:
                continue
            cell = float(cells[i][j])
            if cell < 0.95:
                higher.append(stacks[j])
            elif cell >= 0.95 and cell <= 1.05 and stacks[i] < stacks[j]:
                higher.append(stacks[j])
            else:
                lower.append(stacks[j])
        for l in lower:
            if order_map[l] > order_map[stacks[i]]:
                print("WRONG ORDER")
        for h in higher:
            if order_map[h] < order_map[stacks[i]]:
                print("WRONG ORDER")

    # Print total ordering of stack
    for i in range(len(order)):
        if i > 0:
            stack_i_idx = stacks.index(order[i])
            stack_j_idx = stacks.index(order[i-1])
            cell = float(cells[stack_i_idx][stack_j_idx])
            if cell >= 0.95 and cell <= 1.05:
                print(" = ", end="")
            else:
                print(" < ", end="")
        print(" ".join(order[i]), end="")
    print()



def analyze_transitivity(two_flows_results_dir, exp_conf_name):
    stack_combinations_with_avgtp = get_stack_combis_avg_tps(two_flows_results_dir, exp_conf_name)
    stacks_to_tpratio = get_stacks_to_tpratio(stack_combinations_with_avgtp)
    # Can only get transitivity for all stacks without msquic,
    # as the performance of msquic is not consistent across trials
    analyze_transitivity_for_stacks(stacks_to_tpratio, ALL_STACKS_WO_MSQUIC)


# Analyze whether results based in results_dir gives rise to performance transitivity between stacks
def main():
    results_dir, exp_conf_name = sys.argv[1], sys.argv[2]
    analyze_transitivity(results_dir, exp_conf_name)


if __name__ == "__main__":
    main()
