import json
from pathlib import Path
from traces_parser.parser.instructions_parser import TransactionParsingInfo
from traces_parser.utils.hexstring import HexString


def load_metadata_file(path: Path) -> TransactionParsingInfo:
    with open(path) as metadata_file:
        metadata = json.load(metadata_file)
        victim_tx_hash: str = metadata["transactions_order"][-1]
        tx: dict[str, str] = metadata["transactions"][victim_tx_hash]

        return TransactionParsingInfo(
            sender=HexString(tx["from"]),
            to=HexString(tx["to"]),
            calldata=HexString(tx["input"]),
            value=HexString(tx["value"]),
            verify_storages=True,
        )
