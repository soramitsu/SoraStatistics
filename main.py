import json
import multiprocessing as mp
import os
import shutil
from datetime import datetime
import argparse

import pandas as pd
from networks.ethereum import eth_process
from networks.sora import sora_process

function_mappings = {
    "sora": sora_process,
    "ethereum": eth_process
}


def compile_final_report(base_path, add_networks):
    networks = os.path.join(base_path, "networks")

    data_frame = pd.DataFrame()
    for filename in os.listdir(networks):
        new_transactions = pd.read_csv(os.path.join(networks, filename), index_col=0)
        data_frame = data_frame.append(new_transactions, ignore_index=True)

    data_frame = data_frame.sort_values(by="Time Stamp", ascending=False, ignore_index=True)

    if data_frame.empty:
        print("No transactions")
        return

    stime = datetime.now().strftime("%H:%M %d.%m.%y")
    name = f"Report {stime}.csv"
    file_path = os.path.join(base_path, name)
    data_frame.to_csv(file_path)

    if not add_networks:
        root = os.path.split(base_path)[0]
        os.rename(file_path, os.path.join(root, name))
        shutil.rmtree(base_path)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('--add-networks', dest="add_networks", action='store_true',
                        help='add networks\' reports to result')
    parser.add_argument('config_path',
                        help='config file with networks data')

    args = parser.parse_args()

    f = open(args.config_path)

    data = json.load(f)

    pool = mp.Pool(mp.cpu_count() + 2)

    stime = datetime.now().strftime("%H:%M %d.%m.%y")
    cwd = os.getcwd()

    base_path = os.path.join(cwd, stime)
    shutil.rmtree(base_path, ignore_errors=True)
    networks = os.path.join(base_path, "networks")
    os.mkdir(base_path)
    os.mkdir(networks)

    jobs = []
    for elem in data["networks"]:
        p = function_mappings.get(elem["name"], None)
        if p is None:
            print("WARN: Cannot process {} network: Unknown network".format(elem["name"]))
            continue

        if "address" not in elem:
            print("WARN: Cannot process {} network: address not provided".format(elem["name"]))
            continue

        if "from-block" not in elem:
            elem["from-block"] = 0

        job = pool.apply_async(p, (networks, elem["address"], elem["from-block"]))
        jobs.append(job)

    for job in jobs:
        job.get()

    pool.close()
    pool.join()

    compile_final_report(base_path, args.add_networks)


if __name__ == '__main__':
    main()
