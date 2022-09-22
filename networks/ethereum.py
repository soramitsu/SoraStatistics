from etherscan import Etherscan
from dotenv import dotenv_values
from datetime import datetime
from utils.precision import set_precision
import pandas as pd
import os


def eth_process(base_path, address, from_block):
    config = dotenv_values(".env")
    client = Etherscan(config["ETHERSCAN_KEY"])

    columns = {"scan": "Scan Tool", "network": "Data Source", "timestamp": "Time Stamp", "date": "Date and Time (UTC)",
               "height": "Block height", "tx_hash": "Transaction hash", "line": "Line Number",
               "type": "Transaction Type", "amount": "Token amount", "ticker": "Token ticker",
               "send_or_receive": "Sender or Receiver", "sender": "Sending wallet",
               "receiver": "Receiving side address",
               "network_fee": "Network fee amount", "fee_ticker": "Network fee token ticker",
               "lp_fee": "Liquidity Provider Fee",
               "lp_fee_ticker": "Liquidity Provider Fee token ticker"}

    transaction_template = dict.fromkeys(columns.keys(), "")

    transactions = pd.DataFrame()
    try:
        res = client.get_erc20_token_transfer_events_by_address(address=address,
                                                                startblock=from_block,
                                                                endblock=99999999,
                                                                sort="desc")
    except AssertionError as e:
        estr = str(e)
        if "No transactions found" in estr:
            return
        if "Result window is too large" in estr:
            return
        print(estr)
        return

    for tx in res:
        transaction = transaction_template.copy()
        transaction["scan"] = "EtherScan"
        transaction["network"] = "ETH Main Net"
        transaction["timestamp"] = tx["timeStamp"]
        transaction["date"] = datetime.utcfromtimestamp(int(tx["timeStamp"])).strftime('%Y-%m-%d %H:%M:%S')
        transaction["height"] = tx["blockNumber"]
        transaction["tx_hash"] = tx["hash"]
        transaction["line"] = 1
        transaction["network_fee"] = tx["gas"]
        transaction["fee_ticker"] = "Gwei"

        transaction["type"] = "transfer"

        transaction["amount"] = set_precision(tx["value"], int(tx["tokenDecimal"]))
        transaction["ticker"] = tx["tokenSymbol"]

        transaction["send_or_receive"] = "S" if tx["from"] == address else "R"
        transaction["sender"] = tx["from"]
        transaction["receiver"] = tx["to"]

        transactions = transactions.append(transaction, ignore_index=True)

    if transactions.empty:
        return

    to_block = transactions.head(1)["height"].values[0]
    stime = datetime.now().strftime("%H:%M %d.%m.%y")
    name = f"ETH {stime} {address[:4]}...{address[-4:]} ({from_block}:{to_block}]"
    filepath = os.path.join(base_path, f"{name}.csv")
    transactions.rename(columns=columns).to_csv(filepath)
