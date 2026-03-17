import itertools

from core import utils


def test_offsets_echo_count():
    offsets = utils.offsets_echo_count({"echo.1": 1}, {"echo.1": 2})
    assert offsets == {"echo.1": 1}
    #
    offsets = utils.offsets_echo_count({"echo.1": 1}, {"echo.2": 5})
    assert offsets == {"echo.2": 0}
    #
    offsets = utils.offsets_echo_count({"echo.1": 1}, {"echo.1": 1})
    assert offsets == {}
