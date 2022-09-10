import re
from common import main, get_time_diff

def retrieve_cwnd(line):
    # express in kB
    tokens = line.split(' ')
    for i in range(len(tokens) - 1):
        if tokens[i].startswith("cwnd:"):
            return int(re.search(r'\d+', tokens[i])[0]) / 1000
    return None

def retrieve_time(line):
    meta_data = line.split(' ')[0]
    datetime = meta_data.split(':')[0]
    time = datetime.split('/')[1]
    hour, minute, sec = float(time[:2]), float(time[2:4]), float(time[4:])
    return round(hour * 3600 + minute * 60 + sec, 6)

def chromium_parse_func(log_path):
    cwnd_trace = []
    start_time = -1
    with open(log_path) as f:
        for line in f.readlines():
            if "Server: Processing IETF QUIC packet." in line and start_time < 0:
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
    main(chromium_parse_func)
