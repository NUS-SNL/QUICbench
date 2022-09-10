'''
Utils for reading/writing from files
'''
import csv
import json

def write_to_csv(path, headers, rows):
    with open(path, "w", newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(headers)
        for row in rows:
            csv_writer.writerow(row)

def read_json_as_dict(json_filepath):
    with open(json_filepath) as f:
        return json.load(f)    

def dump_dict_as_json(dictionary, json_filepath):
    with open(json_filepath, "w") as f:
        json.dump(dictionary, f, indent=4)
