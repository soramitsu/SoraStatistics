from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport
import pandas as pd
import sys
from substrateinterface.utils import ss58

# Select your transport with a defined url endpoint
transport = AIOHTTPTransport(url="https://api.subquery.network/sq/sora-xor/sora")

# Create a GraphQL client using the defined transport
client = Client(transport=transport, fetch_schema_from_transport=True)

id_to_name = {"0x0200000000000000000000000000000000000000000000000000000000000000": "XOR",
              "0x0200040000000000000000000000000000000000000000000000000000000000": "VAL",
              "0x0200050000000000000000000000000000000000000000000000000000000000": "PSWAP",
              "0x0200080000000000000000000000000000000000000000000000000000000000": "XSTUSD"}

# Provide a GraphQL query
query = gql(
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

if __name__ == '__main__':

    if len(sys.argv) != 2:
        print("Use python3 stat.py address")

    address = sys.argv[1]

    if not ss58.is_valid_ss58_address(address):
        raise ValueError(f"Address {address} is not valid ss58 address")

    variables = {"filter": {"and": [{"module": {"equalTo": "assets"}, "method": {"equalTo": "transfer"}}, {
        "or": [
            {"address": {"equalTo": address}},
            {"data": {"contains": {
                "to": address}}}]}]},
                 }

    columns = ["Time Stamp", "Block height", "Transaction hash", "Token amount", "Token ticker", "Network fee amount",
               "Network fee token ticker", "Sender or Receiver", "Sending wallet", "Receiving side address"]

    transactions = pd.DataFrame(columns=columns)

    size = 0
    while True:
        page_transactions = pd.DataFrame(columns=columns)
        result = client.execute(query, variable_values=variables)
        elements = result["historyElements"]
        page_info = elements["pageInfo"]
        edges = elements["edges"]
        for edge in edges:
            node = edge["node"]
            ticker = node["data"]["assetId"]
            if ticker in id_to_name:
                ticker = id_to_name[ticker]
            flag = "R"
            if node["data"]["from"] == address:
                flag = "S"
            page_transactions.loc[size] = [node["timestamp"], node["blockHeight"], node["id"], node["data"]["amount"],
                                           ticker,
                                           node["networkFee"], "XOR",
                                           flag,
                                           node["data"]["from"],
                                           node["data"]["to"]]
            size += 1

        transactions = pd.concat([transactions, page_transactions])
        variables["after"] = page_info["endCursor"]
        if not page_info["hasNextPage"]:
            break

    transactions.to_csv(f"{address}.csv")
    print(f"Statistics saved in {address}.csv")
