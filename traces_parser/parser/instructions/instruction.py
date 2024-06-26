from dataclasses import dataclass, field
from typing import ClassVar


from traces_parser.parser.environment.call_context import CallContext
from traces_parser.parser.environment.parsing_environment import (
    InstructionOutputOracle,
    ParsingEnvironment,
)
from traces_parser.parser.information_flow.information_flow_dsl import FlowSpec, noop
from traces_parser.parser.information_flow.information_flow_dsl_implementation import (
    Flow,
)
from traces_parser.parser.storage.storage_writes import StorageAccesses, StorageWrites


@dataclass(frozen=True, repr=False, eq=False)
class Instruction:
    opcode: int
    name: str
    program_counter: int
    step_index: int
    call_context: CallContext = field(compare=False, hash=False)
    flow: Flow
    flow_spec: ClassVar[FlowSpec] = noop()

    def get_accesses(self) -> StorageAccesses:
        return self.flow.accesses

    def get_writes(self) -> StorageWrites:
        return self.flow.writes

    @classmethod
    def parse_flow(
        cls, env: ParsingEnvironment, output_oracle: InstructionOutputOracle
    ) -> Flow:
        return cls.flow_spec.compute(env, output_oracle)

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, Instruction)
            and self.opcode == other.opcode
            and self.program_counter == other.program_counter
            and self.flow == other.flow
        )

    def __str__(self) -> str:
        return f"<{self.name}@{self.call_context.code_address}:{self.program_counter}#{self.step_index}>"

    def __repr__(self) -> str:
        return self.__str__()
