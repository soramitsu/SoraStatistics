from models.store import TokenStore, set_precision

import gql
from gql.transport.aiohttp import AIOHTTPTransport
import pandas as pd
from datetime import datetime
from substrateinterface.utils import ss58
import argparse

# Select your transport with a defined url endpoint
transport = AIOHTTPTransport(url="https://api.subquery.network/sq/sora-xor/sora")

# Create a GraphQL client using the defined transport
client = gql.Client(transport=transport, fetch_schema_from_transport=True, execute_timeout=None)


class Context:

    def __init__(self):
        self.store = TokenStore()


# Provide a GraphQL query
query = gql.gql(
    """
query HistoryElements(
  $first: Int = null
  $last: Int = null
  $after: Cursor = ""
  $before: Cursor = ""
  $orderBy: [HistoryElementsOrderBy!] = TIMESTAMP_DESC
  $filter: HistoryElementFilter
  $idsOnly: Boolean! = false
) {
  historyElements(
    first: $first
    last: $last
    before: $before
    after: $after
    orderBy: $orderBy
    filter: $filter
  ) {
    edges {
      cursor @skip(if: $idsOnly)
      node {
        id
        timestamp
        blockHash @skip(if: $idsOnly)
        blockHeight @skip(if: $idsOnly)
        module @skip(if: $idsOnly)
        method @skip(if: $idsOnly)
        address @skip(if: $idsOnly)
        networkFee @skip(if: $idsOnly)
        execution @skip(if: $idsOnly)
        data @skip(if: $idsOnly)
      }
    }
    pageInfo @skip(if: $idsOnly) {
      hasNextPage
      hasPreviousPage
      startCursor
      endCursor
    }
    totalCount @skip(if: $idsOnly)
  }
}
"""
)


def process_transfer(context: Context, node, transaction):
    transaction["amount"] = node["data"]["amount"]
    transaction["ticker"] = context.store.get_asset_ticker(node["data"]["assetId"])
    transaction["send_or_receive"] = "S" if node["data"]["from"] == address else "R"
    transaction["sender"] = node["data"]["from"]
    transaction["receiver"] = node["data"]["to"]
    return [transaction]


def process_swap(context: Context, node, transaction):
    from_transaction = transaction.copy()
    from_transaction["lp_fee"] = node["data"]["liquidityProviderFee"]
    from_transaction["lp_fee_ticker"] = "XOR"
    from_transaction["amount"] = node["data"]["baseAssetAmount"]
    from_transaction["ticker"] = context.store.get_asset_ticker(node["data"]["baseAssetId"])
    from_transaction["send_or_receive"] = "S"
    from_transaction["sender"] = address

    transaction["line"] = 2
    transaction["network_fee"] = ""
    transaction["fee_ticker"] = ""
    transaction["amount"] = node["data"]["targetAssetAmount"]
    transaction["ticker"] = context.store.get_asset_ticker(node["data"]["targetAssetId"])
    transaction["send_or_receive"] = "R"
    transaction["receiver"] = address

    return [from_transaction, transaction]


def process_pool(context: Context, node, transaction):
    if node["method"] == "withdrawLiquidity":
        transaction["send_or_receive"] = "R"
        transaction["receiver"] = address
    else:
        transaction["send_or_receive"] = "S"
        transaction["sender"] = address

    from_transaction = transaction.copy()
    from_transaction["amount"] = node["data"]["baseAssetAmount"]
    from_transaction["ticker"] = context.store.get_asset_ticker(node["data"]["baseAssetId"])

    transaction["line"] = 2
    transaction["network_fee"] = ""
    transaction["fee_ticker"] = ""
    transaction["amount"] = node["data"]["targetAssetAmount"]
    transaction["ticker"] = context.store.get_asset_ticker(node["data"]["targetAssetId"])

    return [from_transaction, transaction]


def process_to_bridge(context: Context, node, transaction):
    transaction["amount"] = node["data"]["amount"]
    transaction["ticker"] = context.store.get_asset_ticker(node["data"]["assetId"])
    transaction["send_or_receive"] = "S"
    transaction["sender"] = address
    transaction["receiver"] = node["data"]["sidechainAddress"]

    return [transaction]


def process_register(context: Context, node, transaction):
    transaction["amount"] = context.store.get_asset_amount(node["data"]["assetId"])
    transaction["ticker"] = context.store.get_asset_ticker(node["data"]["assetId"])
    transaction["send_or_receive"] = "R"
    transaction["receiver"] = address

    return [transaction]


def process_module(context: Context, node, transaction):
    transaction["type"] = node["method"]

    if "execution" in node and not node["execution"]["success"]:
        transaction["type"] = "failed"
        return [transaction]

    if node["module"] == "assets" and node["method"] == "transfer":
        return process_transfer(context, node, transaction)
    elif node["module"] == "assets" and node["method"] == "register":
        return process_register(context, node, transaction)
    elif node["module"] == "liquidityProxy" and node["method"] == "swap":
        return process_swap(context, node, transaction)
    elif node["module"] == "poolXYK" and (
            node["method"] == "withdrawLiquidity" or node["method"] == "depositLiquidity"):
        return process_pool(context, node, transaction)
    elif node["module"] == "pswapDistribution" and node["method"] == "claimIncentive":

        transaction["send_or_receive"] = "R"
        transaction["receiver"] = address

        for elem in node["data"]:
            new_transaction = transaction.copy()
            new_transaction["amount"] = set_precision(elem["amount"],
                                                      context.store.get_asset_precision(elem["assetId"]))
            new_transaction["ticker"] = context.store.get_asset_ticker(elem["assetId"])
            transactions.append(new_transaction)

        return transactions

    elif node["module"] == "ethBridge" and node["method"] == "transferToSidechain":

        return process_to_bridge(context, node, transaction)

    elif node["module"] == "utility" and node["method"] == "batchAll":

        for elem in node["data"]:
            if elem["module"] == "poolXYK" and elem["method"] == "depositLiquidity":
                elem["data"]["baseAssetAmount"] = elem["data"]["args"]["input_a_desired"]
                elem["data"]["baseAssetId"] = elem["data"]["args"]["input_asset_a"]
                elem["data"]["targetAssetAmount"] = elem["data"]["args"]["input_b_desired"]
                elem["data"]["targetAssetId"] = elem["data"]["args"]["input_asset_b"]
                return process_module(context, elem, transaction)

    return []


if __name__ == '__main__':

    parser = argparse.ArgumentParser()

    parser.add_argument("-from-height", "--from-height", required=False,
                        help="Height from what you need all transactions")
    parser.add_argument('address', help="Address by which statistics are needed")

    args = parser.parse_args()

    address = args.address
    from_height = 0 if args.from_height is None else args.from_height

    if not ss58.is_valid_ss58_address(address):
        raise ValueError(f"Address {address} is not valid ss58 address")

    variables = {"filter": {
        "and": [{"blockHeight": {"greaterThan": from_height}},
                {"or": [
                    {"module": {"equalTo": "assets"}, "method": {"equalTo": "transfer"}},
                    {"module": {"equalTo": "liquidityProxy"}, "method": {"equalTo": "swap"}},

                    {"module": {"equalTo": "liquidityProxy"},
                     "method": {"equalTo": "swapTransfer"}},

                    {"module": {"equalTo": "utility"}, "method": {"equalTo": "batchAll"},
                     "data": {"contains": [{"module": "poolXYK", "method": "initializePool"},
                                           {"module": "poolXYK",
                                            "method": "depositLiquidity"}]}},

                    {"module": {"includesInsensitive": "poolXYK"},
                     "method": {"equalTo": "depositLiquidity"}},
                    {"module": {"includesInsensitive": "poolXYK"},
                     "method": {"equalTo": "withdrawLiquidity"}},

                    {"module": {"equalTo": "ethBridge"}, "method": {"equalTo": "transferToSidechain"}},

                    {"module": {"equalTo": "assets"}, "method": {"equalTo": "register"}},

                ]},
                {
                    "or": [
                        {"address": {"equalTo": address}},
                        {"data": {"contains": {
                            "to": address}}}]
                }
                ]
    }}

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

    context = Context()

    while True:
        page_transactions = pd.DataFrame()
        result = client.execute(query, variable_values=variables)

        elements = result["historyElements"]
        page_info = elements["pageInfo"]
        edges = elements["edges"]
        for edge in edges:
            node = edge["node"]

            transaction = transaction_template.copy()
            transaction["scan"] = "SubQuery"
            transaction["network"] = "SORA Main Net"
            transaction["timestamp"] = node["timestamp"]
            transaction["date"] = datetime.utcfromtimestamp(node["timestamp"]).strftime('%Y-%m-%d %H:%M:%S')
            transaction["height"] = node["blockHeight"]
            transaction["tx_hash"] = node["id"]
            transaction["line"] = 1
            transaction["network_fee"] = node["networkFee"]
            transaction["fee_ticker"] = "XOR"

            new_transactions = process_module(context, node, transaction)

            for elem in new_transactions:
                page_transactions = page_transactions.append(elem, ignore_index=True)

        transactions = pd.concat([transactions, page_transactions])
        variables["after"] = page_info["endCursor"]
        if not page_info["hasNextPage"]:
            break

    if transactions.empty:
        print(f"No transactions for {address}")
        exit(0)

    to_height = transactions.head(1)["height"].values[0]
    stime = datetime.now().strftime("%H:%M %d.%m.%y")
    name = f"{stime} {address[:4]}...{address[-4:]} ({from_height}:{to_height}]"
    transactions.rename(columns=columns).to_csv(f"{name}.csv")
    print(f"Statistics saved in {name}.csv")
