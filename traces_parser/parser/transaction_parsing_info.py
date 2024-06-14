from dataclasses import dataclass
from typing import Sequence

from traces_parser.parser.environment.call_context_manager import CallTree
from traces_parser.parser.instructions.instruction import Instruction
from traces_parser.datatypes.hexstring import HexString


@dataclass
class TransactionParsingInfo:
    sender: HexString
    to: HexString
    calldata: HexString
    value: HexString
    verify_storages: bool = True


@dataclass
class ParsedTransaction:
    instructions: Sequence[Instruction]
    call_tree: CallTree
