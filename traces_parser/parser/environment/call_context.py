from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from typing_extensions import Self

from traces_parser.datatypes.storage_byte_group import StorageByteGroup
from traces_parser.datatypes.hexstring import HexString

if TYPE_CHECKING:
    from traces_parser.parser.instructions.instructions import (
        CallContextEnteringInstruction,
    )


class HaltType(Enum):
    NORMAL = "normal"
    EXCEPTIONAL = "exceptional"


@dataclass
class CallContext:
    parent: Self | None = field(repr=False)
    calldata: StorageByteGroup
    value: StorageByteGroup
    depth: int
    msg_sender: HexString
    code_address: HexString
    storage_address: HexString
    initiating_instruction: CallContextEnteringInstruction | None = field(
        default=None, compare=False, hash=False
    )
    return_data: StorageByteGroup = field(default_factory=StorageByteGroup)
    reverted: bool = False
    halt_type: HaltType | None = None
    is_contract_initialization: bool = False

    def __post_init__(self):
        self.msg_sender = self.msg_sender.as_address()
        self.code_address = self.code_address.as_address()
        self.storage_address = self.storage_address.as_address()

    def get_root(self) -> CallContext:
        if not self.parent:
            return self
        return self.parent.get_root()
