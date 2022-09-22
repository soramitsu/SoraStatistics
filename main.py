import json
import multiprocessing as mp
import os
import argparse

from networks.ethereum import eth_process
from networks.sora import sora_process

function_mappings = {
    "sora": sora_process,
    "ethereum": eth_process
}


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('config_path',
                        help='config file with networks data')

    args = parser.parse_args()

    f = open(args.config_path)

    data = json.load(f)

    pool = mp.Pool(mp.cpu_count() + 2)

    cwd = os.getcwd()

    jobs = []
    for elem in data["networks"]:
        p = function_mappings.get(elem["name"], None)
        if p is None:
            print("WARN: Cannot process {} network: Unknown network".format(elem["name"]))
            continue

        if "enable" not in elem:
            print("WARN: Cannot process {} network: enable not provided".format(elem["name"]))
            continue

        if not elem["enable"]:
            continue

        if "address" not in elem:
            print("WARN: Cannot process {} network: address not provided".format(elem["name"]))
            continue

        if "from-block" not in elem:
            elem["from-block"] = 0

        job = pool.apply_async(p, (cwd, elem["address"], elem["from-block"]))
        jobs.append(job)

    for job in jobs:
        job.get()

    pool.close()
    pool.join()


if __name__ == '__main__':
    main()
