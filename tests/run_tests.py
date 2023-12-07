import pytest
import requests
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone
from tfl_bus_monitor import TFLBusMonitor

Test_StopID = '490005432S2'

@pytest.fixture
def tfl_bus_monitor():
    return TFLBusMonitor()

def test_get_tfl_success(tfl_bus_monitor):
    tfl_id = Test_StopID
    timeout = 10
    response_data = {"example_key": "example_value"}
    with patch("requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: response_data)
        result = tfl_bus_monitor.get_tfl(tfl_id, timeout)
    assert result == response_data

def test_get_tfl_retry_on_connection_error(tfl_bus_monitor):
    tfl_id = Test_StopID
    timeout = 10
    with patch("requests.get") as mock_get:
        mock_get.side_effect = [requests.exceptions.ConnectionError, MagicMock(status_code=200, json=lambda: {})]
        result = tfl_bus_monitor.get_tfl(tfl_id, timeout)
    assert result == {}

def test_get_stop_name_cache(tfl_bus_monitor):
    stop_id = Test_StopID
    tfl_bus_monitor.stop_name_cache[stop_id] = "Cached Stop Name"
    result = tfl_bus_monitor.get_stop_name(stop_id)
    assert result == "Cached Stop Name"

def test_get_stop_name_request(tfl_bus_monitor):
    stop_id = Test_StopID
    response_data = {"commonName": "Example Stop Name"}
    with patch.object(tfl_bus_monitor, "get_tfl", return_value=response_data):
        result = tfl_bus_monitor.get_stop_name(stop_id)
    assert result == "Example Stop Name"

