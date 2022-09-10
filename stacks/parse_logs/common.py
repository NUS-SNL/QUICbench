''' Defines common interface to parse logs of stacks '''

import sys
import os
import argparse

sys.path.insert(1, os.path.join(sys.path[0], '../..')) # allow importing from parent dir (repo)

from utils.files import write_to_csv, read_json_as_dict

SECONDS_IN_DAY = 24 * 60 * 60

def get_time_diff(later_s_of_day, earlier_s_of_day):
    return (later_s_of_day - earlier_s_of_day + SECONDS_IN_DAY) % SECONDS_IN_DAY

def get_parse_log_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--infile", "-i", help="path to log", type=str)
    parser.add_argument("--outfile", "-o", help="path to write cwnd output to", type=str)
    return parser.parse_args()

def main(stack_parse_func):
    args = get_parse_log_args()
    time_cwnd_rows = stack_parse_func(args.infile)
    write_to_csv(args.outfile, ["time (s)", "cwnd (kB)"], time_cwnd_rows)
