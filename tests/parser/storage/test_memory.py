from tests.test_utils.test_utils import _test_group, _test_mem
from traces_analyzer.parser.storage.memory import Memory
from traces_analyzer.parser.storage.storage_value import StorageByteGroup
from traces_analyzer.utils.hexstring import HexString


def test_memory_empty():
    mem = Memory()

    assert mem.size() == 0


def test_memory_set_32():
    mem = Memory()

    mem.set(0, _test_group("00" * 32), 1)

    assert mem.size() == 32


def test_memory_set_expands():
    mem = Memory()

    mem.set(10, _test_group("00" * 32), 1)

    assert mem.size() == 64


def test_memory_set_expands_with_step_index():
    mem = Memory()

    mem.set(10, _test_group("00" * 32, 1), 2)

    mem_expanded_1 = mem.get(0, 10, -1)
    mem_set = mem.get(10, 32, -1)
    mem_expanded_2 = mem.get(42, 22, -1)

    assert {2} == set(byte.created_at_step_index for byte in mem_expanded_1)
    assert {1} == set(byte.created_at_step_index for byte in mem_set)
    assert {2} == set(byte.created_at_step_index for byte in mem_expanded_2)


def test_memory_get():
    mem = _test_mem("11223344" + "00" * 28, -1)

    result = mem.get(2, 4, -1)

    assert result.get_hexstring() == "33440000"


def test_memory_get_does_not_expand():
    mem = Memory()

    mem.get(50, 20, -1)

    assert mem.size() == 0


def test_memory_expands():
    mem = _test_mem("11" * 64, -1)

    mem.check_expansion(50, 20, 1)

    assert mem.size() == 96
    assert {1} == set(byte.created_at_step_index for byte in mem.get(64, 32, -1))
