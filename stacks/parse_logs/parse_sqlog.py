import json
import re
from common import main, get_time_diff

# not specified in quiche qlog, but it's 1000
TIME_DIVISOR = 1000

def retrieve_cwnd(event):
    # express in kB
    data = event["data"]
    if event["name"] == "recovery:metrics_updated" and "congestion_window" in data:
        return int(data["congestion_window"]) / 1000
    return None

def retrieve_time(event):
    # express in s
    return round(float(event["time"]) / TIME_DIVISOR, 6)

def sqlog_parse_func(log_path):
    """ for stream qlog qlog_version 0.3 """
    
    cwnd_trace = []
    start_time = -1
    with open(log_path) as f:
        for event in f.readlines()[1:]:
            try:
                event = json.loads(event.strip())
            except:
                continue
            if start_time < 0:
                # first event
                start_time = retrieve_time(event)
            cwnd = retrieve_cwnd(event)
            if cwnd is not None:  
                relative_time = retrieve_time(event) - start_time
                cwnd_trace.append((relative_time, cwnd))
    return cwnd_trace


if __name__ == "__main__":
    main(sqlog_parse_func)
