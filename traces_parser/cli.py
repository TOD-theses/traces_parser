"""CLI interface for traces_parser project."""

from argparse import ArgumentParser
from pathlib import Path

from traces_parser.parser.events_parser import parse_events
from traces_parser.parser.instructions_parser import parse_transaction
from traces_parser.utils.metadata_file_loader import load_metadata_file


def main():
    parser = ArgumentParser(description="Parse EVM traces")
    parser.add_argument(
        "--trace", type=Path, required=True, help="Path to the EIP-3155 trace"
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        required=True,
        help="Path to the transaction metadata file",
    )

    args = parser.parse_args()
    trace_path: Path = args.trace
    metadata_path: Path = args.metadata

    transaction_parsing_info = load_metadata_file(metadata_path)

    print(
        f"Parsing transaction from {transaction_parsing_info.sender.with_prefix()} to {transaction_parsing_info.to.with_prefix()}"
    )

    with open(trace_path) as trace_file:
        parsed_transaction = parse_transaction(
            transaction_parsing_info, parse_events(trace_file)
        )

        print(f"Parsed {len(parsed_transaction.instructions)} instructions")

        print("Call Tree")
        print(str(parsed_transaction.call_tree))
