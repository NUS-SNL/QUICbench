import os
import sys
import argparse
import json
import subprocess
import time
import random
from datetime import datetime
from operator import itemgetter

from constants import *
from stacks.chromium import Chromium
from stacks.msquic import Msquic
from stacks.mvfst import Mvfst
from stacks.quiche import Quiche
from stacks.tcp import Tcp
from utils.remote_cmd import get_remote_cmd, get_remote_cmd_sudo, get_scp_file_to_remote_cmd
from network.set_netem import set_netem
from network.clear_netem import clear_netem
from network.test_network import *
from network.tcpdump import TCPDump


def get_prog_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stacks_conf", "-s", help="path to stacks configuration", type=str, 
        default="./config/stacks_conf_default.json")
    parser.add_argument("--general_conf", "-k", help="path to general configuration", type=str,
        default="./config/general_conf_default.json")
    parser.add_argument("--exp_conf", "-e", help="path to experiment configuration", type=str)
    parser.add_argument("--stack_log", "-l", help="enable stacks logging", action='store_true')
    return parser.parse_args()


def validate_exp_iflogging(exp_conf):
    """ If stacks logging is enabled, we have to ensure that: """
    def fail_validate():
        sys.exit("exiting... stacks logging is enabled and exp_conf is not valid.")
    if exp_conf["netem_conf"]["bandwidth_Mbps"] > 15:
        fail_validate()
    # only single flow
    for combi in exp_conf["stacks_combinations"]:
        if len(combi["stacks"]) > 1:
            fail_validate()


def check_sudo_privileges(server_hostname, server_pw_path):
    subprocess.run("sudo echo 'Got sudo privileges for local machine.'", shell=True, check=True)
    try:
        subprocess.run(get_remote_cmd_sudo(server_hostname, server_pw_path, "sudo echo 'Got sudo privileges for server machine.'"),
            shell=True, check=True, timeout=1)
    except subprocess.TimeoutExpired:
        sys.exit("exiting... server password is incorrect.")


def init_stacks(stacks_conf, server_ip, server_hostname, server_pw_path):
    chromium_stack = Chromium(server_ip, server_hostname, **stacks_conf[Chromium.NAME])
    msquic_stack = Msquic(server_ip, server_hostname, **stacks_conf[Msquic.NAME])
    mvfst_stack = Mvfst(server_ip, server_hostname, **stacks_conf[Mvfst.NAME])
    quiche_stack = Quiche(server_ip, server_hostname, **stacks_conf[Quiche.NAME])
    tcp_stack = Tcp(server_ip, server_hostname, server_pw_path)
    return {
        Chromium.NAME: chromium_stack,
        Msquic.NAME: msquic_stack,
        Mvfst.NAME: mvfst_stack,
        Quiche.NAME: quiche_stack,
        Tcp.NAME: tcp_stack
    }


def set_kernel_params(kernel_params, server_hostname, server_pw_path):
    print("Setting kernel parameters:")
    for param, value in kernel_params.items():
        subprocess.run("sudo sysctl -w {}=\"{}\"".format(param, value), shell=True, check=True)
        subprocess.run(get_remote_cmd_sudo(server_hostname, server_pw_path, "sudo sysctl -w {}=\\\"{}\\\"".format(param, value)), 
            shell=True, check=True)


def main():
    args = get_prog_args()
    with open(args.stacks_conf) as f:
        stacks_conf = json.load(f)
    with open(args.general_conf) as f:
        general_conf = json.load(f)
    with open(args.exp_conf) as f:
        exp_conf = json.load(f)
    
    if args.stack_log:
        validate_exp_iflogging(exp_conf)

    server_ip, server_hostname, interface, server_ingress_interface, server_repo_path = \
        itemgetter("server_ip", "server_hostname", "interface", "server_ingress_interface", "server_repo_path")(general_conf)

    server_pw_path = general_conf["server_pw_path"]    
    check_sudo_privileges(server_hostname, server_pw_path)
    
    stacks_kls = init_stacks(stacks_conf, server_ip, server_hostname, server_pw_path)
    set_kernel_params(general_conf["kernel_params"], server_hostname, server_pw_path)

    has_veth, virtual_interface = "virtual_interface" in exp_conf, exp_conf.get("virtual_interface")
    set_netem(server_hostname, server_pw_path, server_ip, interface, 
        server_ingress_interface, exp_conf["netem_conf"], virtual_interface)
    
    test_rtt(server_ip)
    test_bandwidth(server_hostname, server_ip)

    # Starting experiment
    experiment_results_dir, num_trials, flow_duration_s, stacks_combinations = \
        itemgetter("experiment_results_dir", "num_trials", "flow_duration_s", "stacks_combinations")(exp_conf)
    
    try:
        # set up results dir on server-side
        subprocess.run(get_remote_cmd(server_hostname, ["mkdir", experiment_results_dir]), check=True)
        for conf in [args.stacks_conf, args.general_conf, args.exp_conf]:
            subprocess.run(get_scp_file_to_remote_cmd(server_hostname, conf, experiment_results_dir), check=True)

        for combi in stacks_combinations:
            combi_name, combi_stacks  = itemgetter("name", "stacks")(combi)
            combi_results_dir = os.path.join(experiment_results_dir, combi_name)
            subprocess.run(get_remote_cmd(server_hostname, ["mkdir", combi_results_dir]), check=True)

            random.shuffle(combi_stacks)

            successful_trials = 0
            failed_trials = 0
            while successful_trials < num_trials and failed_trials < int(num_trials * 2): # retries
                # run a trial for stack combination
                trial_datetime = datetime.now().strftime("%Y-%m-%d:%H:%M:%S")
                trial_results_dir = os.path.join(combi_results_dir, trial_datetime)
                subprocess.run(get_remote_cmd(server_hostname, ["mkdir", trial_results_dir]), check=True)

                try:                
                    # start servers
                    stack_processes = []
                    for stack in combi_stacks:
                        stack_name, stack_cc_algo, stack_port_no = itemgetter("name", "cc_algo", "port_no")(stack)
                        if args.stack_log:
                            log_path = os.path.join(trial_results_dir, str(stack_port_no) + STACK_LOG_SUFFIX)
                            proc = stacks_kls[stack_name].run_remote_server_wlogs(
                                stack_port_no, stack_cc_algo, flow_duration_s + 5, log_path
                            )
                        else:
                            proc = stacks_kls[stack_name].run_remote_server(stack_port_no, stack_cc_algo, flow_duration_s + 5)
                        stack_processes.append(proc)

                    time.sleep(2) # wait for servers to start

                    # start tcpdump
                    if has_veth:
                        tcpdump_veth_output_file = os.path.join(trial_results_dir, VETH_PCAP_FILENAME)
                        tcpdump_veth = TCPDump(server_hostname, server_ip, virtual_interface, tcpdump_veth_output_file)
                        tcpdump_veth.start()
                    tcpdump_interface_output_file = os.path.join(trial_results_dir, INTERFACE_PCAP_FILENAME)
                    tcpdump_interface = TCPDump(server_hostname, server_ip, interface, tcpdump_interface_output_file)
                    tcpdump_interface.start()

                    # start clients
                    for stack in combi_stacks:
                        stack_name, stack_cc_algo, stack_port_no = itemgetter("name", "cc_algo", "port_no")(stack)
                        proc = stacks_kls[stack_name].run_client(stack_port_no, stack_cc_algo, flow_duration_s)
                        stack_processes.append(proc)

                    # wait for all server/client processes to finish
                    for proc in stack_processes:
                        proc.wait()

                    # stop tcpdump
                    tcpdump_interface.stop()
                    if has_veth:
                        tcpdump_veth.stop()

                    subprocess.run(get_remote_cmd(server_hostname,
                        ["python3", os.path.join(server_repo_path, "parse", "parse_pcap.py"),
                        "--exp_conf={}".format(os.path.join(experiment_results_dir, os.path.basename(args.exp_conf))),
                        "--general_conf={}".format(os.path.join(experiment_results_dir, os.path.basename(args.general_conf))),
                        "--name={}".format(combi_name), "--trial_dir={}".format(trial_results_dir)
                        ]
                    ), check=True)
                    
                    if args.stack_log:
                        # only for single flow
                        stack = combi_stacks[0]
                        stack_name, stack_port_no = itemgetter("name", "port_no")(stack)
                        subprocess.run(get_remote_cmd(server_hostname,
                            ["python3", os.path.join(server_repo_path, "stacks", "parse_logs", stacks_conf["stack_parser_map"][stack_name]),
                            "--infile={}".format(log_path),
                            "--outfile={}".format(os.path.join(trial_results_dir, stack_port_no + CWND_TRACE_SUFFIX))
                            ]
                        ), check=True)
                    
                    successful_trials += 1
                
                except:
                    time.sleep(flow_duration_s) # wait for servers to timeout

                    # reset interface
                    subprocess.run(["sudo", "ip", "link", "set", "dev", interface, "down"], check=True)
                    subprocess.run(["sudo", "ip", "link", "set", "dev", interface, "up"], check=True)
                    clear_netem(server_hostname, server_pw_path, server_ip, interface, server_ingress_interface, virtual_interface)
                    set_netem(server_hostname, server_pw_path, server_ip, interface, 
                        server_ingress_interface, exp_conf["netem_conf"], virtual_interface)

                    # kill processes
                    subprocess.run(get_remote_cmd(server_hostname, ["pkill", "tcpdump"]))

                    # delete trial
                    subprocess.run(get_remote_cmd(
                        server_hostname, ["rm", "-rf", trial_results_dir]
                    ))
                    failed_trials += 1

    finally:
        # clean up
        clear_netem(server_hostname, server_pw_path, server_ip, interface, server_ingress_interface, virtual_interface)


if __name__ == "__main__":
    main()
