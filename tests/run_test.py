"""
standard package import
"""
from unittest.mock import patch, MagicMock
import requests
import pytest
from tfl_bus_monitor import TFLBusMonitor

TEST_STOPID = '490005432S2'

@pytest.fixture
def tfl_bus_monitor():
    """pytest decorator"""
    return TFLBusMonitor()

def test_get_tfl_success(tfl_bus_monitor):
    """test get_tfl success"""
    tfl_id = TEST_STOPID
    timeout = 10
    response_data = {"example_key": "example_value"}
    with patch("requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: response_data)
        result = tfl_bus_monitor.get_tfl(tfl_id, timeout)
    assert result == response_data

def test_get_tfl_retry_on_connection_error(tfl_bus_monitor):
    """test get_tfl fail"""
    tfl_id = TEST_STOPID
    timeout = 10
    with patch("requests.get") as mock_get:
        mock_get.side_effect = [requests.exceptions.ConnectionError,
                               MagicMock(status_code=200,
                               json=lambda: {})]
        result = tfl_bus_monitor.get_tfl(tfl_id, timeout)
    assert result == {}

def test_get_stop_name_cache(tfl_bus_monitor):
    """test get_stop_name_cache"""
    stop_id = TEST_STOPID
    tfl_bus_monitor.stop_name_cache[stop_id] = "Cached Stop Name"
    result = tfl_bus_monitor.get_stop_name(stop_id)
    assert result == "Cached Stop Name"

def test_get_stop_name_request(tfl_bus_monitor):
    """test get_stop_name request"""
    stop_id = TEST_STOPID
    response_data = {"commonName": "Example Stop Name"}
    with patch.object(tfl_bus_monitor, "get_tfl", return_value=response_data):
        result = tfl_bus_monitor.get_stop_name(stop_id)
    assert result == "Example Stop Name"
