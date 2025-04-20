# tfl_bus_monitor

Download and display Transport For London (TfL) bus arrival time information using the TfL Unified API. Includes CLI and Python usage with optional filtering and config-based setup.

## Install from PyPI

```bash
pip install tfl_bus_monitor
```

## Command-Line Usage

```bash
busstop [-h] [-t | -j] [-c CONFIG] [--route ROUTE] [--destination DESTINATION]
```

### Options:

- `-h`, `--help` — Show help message and exit  
- `-t`, `--text` — Print formatted text  
- `-j`, `--json` — Pretty-print JSON (default)  
- `-c CONFIG`, `--config CONFIG` — Path to custom INI config file  
- `--route ROUTE` — Filter results by line name or bus number  
- `--destination DESTINATION` — Filter results by destination name  

### Example

```bash
busstop --text --route 73 --destination "Ealing Broadway"
```

## Python Usage

```python
from tfl_bus_monitor.tfl_bus_monitor import TFLBusMonitor, get_config_path

monitor = TFLBusMonitor()
data = monitor.get_all_arrivals()
print(data)
```

## Configuration

By default, the tool looks for a file named `busstop_config.ini` in:

1. `$BUSSTOP_HOME/`
2. User home directory (`~/busstop_config.ini`)
3. Embedded package config directory

### Example `busstop_config.ini`

```ini
[busstop]
stopid = 490008660N, 490004973E
num_services = 5, 3
```

Each `stopid` corresponds to a TfL StopPoint ID, and `num_services` indicates how many upcoming services to show per stop.
