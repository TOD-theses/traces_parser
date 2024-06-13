from abc import abstractmethod
from dataclasses import dataclass

from traces_parser.parser.environment.parsing_environment import (
    InstructionOutputOracle,
    ParsingEnvironment,
)
from traces_parser.parser.storage.storage_writes import StorageAccesses, StorageWrites


@dataclass(frozen=True)
class Flow:
    accesses: StorageAccesses
    writes: StorageWrites


class FlowSpec:
    @abstractmethod
    def compute(
        self, env: ParsingEnvironment, output_oracle: InstructionOutputOracle
    ) -> Flow:
        """Compute the output of an information flow for a specific environment"""
        pass
