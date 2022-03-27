'''
Utils for reading/writing from files
'''
import csv

def write_to_csv(path, headers, rows):
    with open(path, "w", newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(headers)
        for row in rows:
            csv_writer.writerow(row)
