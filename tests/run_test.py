import pytest
from unittest.mock import patch, MagicMock
import requests
from tfl_bus_monitor import TFLBusMonitor

TEST_STOPID = '490005432S2'


@pytest.fixture
def tfl_bus_monitor():
    return TFLBusMonitor()


# ---- Tests for parse_arrival_item ----

def test_parse_arrival_item_valid(tfl_bus_monitor):
    """Test parse_arrival_item returns cleaned data"""
    item = {
        "expectedArrival": "2025-04-20T20:00:00Z",
        "timeToStation": 120,
        "destinationName": "Oxford Circus Underground Station",
        "lineName": "12"
    }
    result = tfl_bus_monitor.parse_arrival_item(item, 1)
    assert result["lineName"] == "12"
    assert result["destinationName"] == "Oxford Circus"
    assert "arrivalTime" in result
    assert result["dueIn"] == "2min"


def test_parse_arrival_item_malformed(tfl_bus_monitor):
    """Test parse_arrival_item returns error info on malformed input"""
    item = {"destinationName": "Somewhere"}  # missing fields
    result = tfl_bus_monitor.parse_arrival_item(item, 1)
    assert "noInfo" in result


# ---- Tests for get_arrival_times ----

def test_get_arrival_times_valid(tfl_bus_monitor):
    """Test get_arrival_times returns formatted output"""
    with patch.object(tfl_bus_monitor, "get_stops") as mock_stops, \
         patch.object(tfl_bus_monitor, "get_stop_name", return_value="Test Stop"):
        mock_stops.return_value = [{
            "expectedArrival": "2025-04-20T20:01:00Z",
            "timeToStation": 60,
            "destinationName": "Euston Rail Station",
            "lineName": "73"
        }]
        result = tfl_bus_monitor.get_arrival_times(TEST_STOPID, 1)
        assert result["stopName"] == "Test Stop"
        assert "arrivals" in result
        assert result["arrivals"][0]["lineName"] == "73"


def test_get_arrival_times_empty(tfl_bus_monitor):
    """Test get_arrival_times handles no arrivals gracefully"""
    with patch.object(tfl_bus_monitor, "get_stops", return_value=[]), \
         patch.object(tfl_bus_monitor, "get_stop_name", return_value="Test Stop"):
        result = tfl_bus_monitor.get_arrival_times(TEST_STOPID, 1)
        assert result["arrivals"][0]["noInfo"] == "No information at this time."


# ---- Tests for get_all_arrivals ----

def test_get_all_arrivals_valid_config(tfl_bus_monitor):
    """Test get_all_arrivals with mocked config and stop retrieval"""

    class FakeConfig:
        def read(self, *_):
            pass

        def __contains__(self, key):
            return key == "busstop"

        def getlist(self, section, key):
            if key == "stopid":
                return ["490000173A"]
            elif key == "num_services":
                return ["2"]

    tfl_bus_monitor.config = FakeConfig()

    with patch.object(tfl_bus_monitor, "get_arrival_times",
                      return_value={"stopName": "Foo", "arrivals": []}):
        result = tfl_bus_monitor.get_all_arrivals()

    assert isinstance(result, list)
    assert result[0]["stopName"] == "Foo"


def test_get_all_arrivals_missing_section(tfl_bus_monitor):
    """Test get_all_arrivals handles missing config section"""
    tfl_bus_monitor.config.read = MagicMock()
    tfl_bus_monitor.config.__contains__ = lambda self, k: False  # simulate missing [busstop]
    result = tfl_bus_monitor.get_all_arrivals()
    assert "Missing section" in result[0]["arrivals"][0]["noInfo"]


def test_get_all_arrivals_config_failure(tfl_bus_monitor):
    """Test get_all_arrivals handles unexpected config read error"""
    tfl_bus_monitor.config.read = MagicMock(side_effect=Exception("Boom!"))
    result = tfl_bus_monitor.get_all_arrivals()
    assert "error" in result[0]["arrivals"][0]["noInfo"].lower()

