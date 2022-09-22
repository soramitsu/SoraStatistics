# Sorascan

Sorascan is a tool to scan networks and create *.csv` reports with all transactions.

## Supported Networks

| Name      | Config option | Report option |
|-----------|---------------|---------------|
| Sora      | "sora"        | ETH           |
| Ethereum  | "ethereum"    | SORA          |

## Config

The config is needed to set which addresses and with what parameters you want to receive in the report. 
The config template is [here](template_config.json).

An example of one address entry. You can request multiple addresses from the same network by specifying them in separate entries.
```json
{
      "enable": true, // does it should be processed?
      "name": "network option",
      "address": "address",
      "from-block": 0 // optional: if it is not set, then from genesis
}
```

## How to run

First, you need to set up an environment. You need to create a `.env` file with [template](env_template).

If you need Ethereum network, you have to set up `ETHERSCAN_KEY`. Where to get `ETHERSCAN_KEY`? [Here](https://docs.etherscan.io/getting-started/viewing-api-usage-statistics).

Then run `main.py` script with the following commands
```commandline
pip install -r requirements.txt
python main.py /path/to/config.json
```

As a result, you will have as many reports as the addresses you specified in the config.
The name of a report will be in the next format: `NetworkName Time Date Address (StartBlock:FinishBlock]`
