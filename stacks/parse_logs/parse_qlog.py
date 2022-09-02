import re
from common import main, get_time_diff, read_json_as_dict

time_unit_divisor_map = {
    "us": 1000000
}

def retrieve_cwnd(event):
    # express in kB
    data = event[3]
    if event[2] == "congestion_metric_update" and "current_cwnd" in data:
        return int(data["current_cwnd"]) / 1000
    return None

def retrieve_time(event, time_divisor):
    # express in s
    return round(float(event[0]) / time_divisor, 6)

def qlog_parse_func(log_path):
    """ works for qlog_version draft-00 """
    traces = read_json_as_dict(log_path)["traces"][0]
    time_divisor = time_unit_divisor_map[traces["configuration"]["time_units"]]

    cwnd_trace = []
    start_time = -1

    for event in traces["events"]:
        if start_time < 0:
            # first event
            start_time = retrieve_time(event, time_divisor)

        cwnd = retrieve_cwnd(event)
        if cwnd is not None:  
            relative_time = retrieve_time(event, time_divisor) - start_time
            cwnd_trace.append((relative_time, cwnd))
    return cwnd_trace

if __name__ == "__main__":
    main(qlog_parse_func)
