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
from stacks import *
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
    # logging has been found to affect performance in some stacks when bandwidth > 15 Mbps
    if exp_conf["netem_conf"]["bandwidth_Mbps"] > 15:
        fail_validate()
    # only use with single flow has been well-tested
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
    stacks_dict = {}    
    def get_subclasses(kls):
        for subclass in kls.__subclasses__():
            yield from get_subclasses(subclass)
            yield subclass
    all_stacks_kls = set(get_subclasses(stack.Stack))
    for kls in all_stacks_kls:
        stacks_dict[kls.NAME] = kls(server_ip=server_ip, server_hostname=server_hostname,
                                    server_pw_path=server_pw_path,
                                    **stacks_conf.get(kls.NAME, {}))
    return stacks_dict


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
