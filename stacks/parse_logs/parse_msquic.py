import re
from common import main, get_time_diff

def retrieve_cwnd(line):
    # express in kB
    for val in line.split(' '):
        if val.lower().startswith('cwnd'):
            return int(val.split('=')[1]) / 1000
    return None

def retrieve_time(line):
    # express in s
    meta_data = re.findall(r'(?<=\[).+?(?=\])', line)
    time_str = meta_data[2]
    hour, minute, sec = tuple(map(float, time_str.split(':')))
    return round(hour * 3600 + minute * 60 + sec, 6)

def msquic_parse_func(log_path):
    cwnd_trace = []
    start_time = -1
    with open(log_path) as f:
        for line in f.readlines():
            if "Created, IsServer=1," in line and start_time < 0:
                # first event
                start_time = retrieve_time(line)

            cwnd = retrieve_cwnd(line)
            if cwnd is not None:  
                if start_time < 0:
                    start_time = retrieve_time(line)
                relative_time = get_time_diff(retrieve_time(line), start_time)
                cwnd_trace.append((relative_time, cwnd))
    return cwnd_trace

if __name__ == "__main__":
    main(msquic_parse_func)
