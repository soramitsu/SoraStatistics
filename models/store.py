from models.token import Token
from utils.precision import set_precision

import json
import websocket
from websocket import create_connection


class TokenStore:
    def __init__(self):
        self.store = dict()
        self.hosts = ["wss://sora.api.onfinality.io/public-ws",
                      "wss://ws.mof.sora.org/",
                      "wss://mof2.sora.org/",
                      "wss://mof3.sora.org/"]
        self.host = 0
        self._ws_reset()
        self._init_store()

    def _init_store(self):
        req_info = {"id": self.id, "jsonrpc": "2.0", "method": "assets_listAssetInfos",
                    "params": []}
        req = self._reliable_send(json.dumps(req_info))

        if req is None:
            # default store
            self.store = {
                "0x0200000000000000000000000000000000000000000000000000000000000000": Token("SORA", "XOR", 18),
                "0x0200040000000000000000000000000000000000000000000000000000000000": Token("SORA Validator Token",
                                                                                            "VAL", 18),
                "0x0200050000000000000000000000000000000000000000000000000000000000": Token("Polkaswap", "PSWAP", 18),
                "0x0200060000000000000000000000000000000000000000000000000000000000": Token("Dai", "DAI", 18),
                "0x0200070000000000000000000000000000000000000000000000000000000000": Token("Ether", "ETH", 18),
                "0x0200080000000000000000000000000000000000000000000000000000000000": Token("SORA Synthetic USD",
                                                                                            "XSTUSD", 18),
            }
            return

        self.id += 1

        tokens = json.loads(req)
        for elem in tokens["result"]:
            self.store[elem["asset_id"]] = Token(elem["name"], elem["symbol"], elem["precision"])

    def _get_host(self):
        host = self.hosts[self.host]
        self.host += 1
        self.host %= len(self.hosts)
        return host

    def _ws_reset(self):
        self.ws = create_connection(self._get_host())
        self.id = 0

    def __del__(self):
        self.ws.close()

    def get_asset_amount(self, asset_id: str, block_hash: str):
        if asset_id not in self.store:
            if not self._fetch_token(asset_id):
                return 0

        precision = self.store[asset_id].precision

        req_supply = {"id": self.id, "jsonrpc": "2.0", "method": "assets_totalSupply",
                      "params": [asset_id, block_hash]}
        rcv = self._reliable_send(json.dumps(req_supply))
        if rcv is None:
            return 0
        supply = json.loads(rcv)
        self.id += 1

        if "balance" not in supply["result"]:
            return 0

        return set_precision(supply["result"]["balance"], int(precision))

    def get_asset_ticker(self, asset_id: str):
        if asset_id not in self.store:
            if not self._fetch_token(asset_id):
                return asset_id

        return self.store[asset_id].ticker

    def get_asset_precision(self, asset_id: str):
        if asset_id not in self.store:
            if not self._fetch_token(asset_id):
                return 0

        return self.store[asset_id].precision

    def _reliable_send(self, req: str):
        i = len(self.hosts)
        while i > 0:
            try:
                self.ws.send(req)
                return self.ws.recv()
            except websocket.WebSocketConnectionClosedException:
                self._ws_reset()
                i -= 1
                continue
        return None

    def _fetch_token(self, asset_id):
        req_info = {"id": self.id, "jsonrpc": "2.0", "method": "assets_getAssetInfo",
                    "params": [asset_id]}
        rcv = self._reliable_send(json.dumps(req_info))
        if rcv is None:
            return False
        info = json.loads(rcv)
        self.id += 1

        if "symbol" not in info["result"] or len(info["result"]["symbol"]) == 0:
            return False

        self.store[asset_id] = Token(info["result"]["name"], info["result"]["symbol"],
                                     int(info["result"]["precision"]))

        return True
