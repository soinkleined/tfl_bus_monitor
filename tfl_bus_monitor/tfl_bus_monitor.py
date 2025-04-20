from pathlib import Path
import configparser
import logging
import os
import time
import math
import json
import argparse
from importlib import resources
from datetime import datetime as dt
from typing import Any, List, Dict, Union, Optional

import pytz
import requests

# Constants
DEFAULT_CONFIG_NAME = "busstop_config.ini"
DEFAULT_TZ = "Europe/London"
CONFIG_SECTION = "busstop"
MAX_RETRIES = 5
MAX_BACKOFF = 60

# Logging setup
logging.basicConfig(
    format='[%(asctime)s] [%(process)d] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S %z'
)
logger = logging.getLogger(__name__)
logger.propagate = False
if __name__ != '__main__':
    gunicorn_logger = logging.getLogger('gunicorn.error')
    logger.setLevel(gunicorn_logger.level)


def get_config_path() -> Path:
    if "TFL_MONITOR_HOME" in os.environ:
        return Path(os.environ["TFL_MONITOR_HOME"]) / DEFAULT_CONFIG_NAME
    home_config = Path.home() / DEFAULT_CONFIG_NAME
    if home_config.is_file():
        return home_config
    package_path = resources.files('tfl_bus_monitor') / "config" / DEFAULT_CONFIG_NAME
    return Path(package_path)


class TFLBusMonitor:
    def __init__(self, config_file: Optional[Path] = None) -> None:
        self.config = configparser.ConfigParser(
            converters={'list': lambda x: [i.strip() for i in x.split(',')]})
        self.stop_name_cache: Dict[str, str] = {}
        self.config_file = config_file or get_config_path()
        self.url = 'https://api.tfl.gov.uk/StopPoint/'
        self.local_tz = pytz.timezone(DEFAULT_TZ)
        self.date_format = "%Y-%m-%d"
        self.time_format = "%H:%M:%S"

    def utc_to_local(self, utc_dt: dt) -> dt:
        return utc_dt.replace(tzinfo=pytz.utc).astimezone(self.local_tz)

    def get_stops(self, tfl_id: str, timeout: int) -> Optional[Dict[str, Any]]:
        retries = 0
        last_error = None
        while retries < MAX_RETRIES:
            try:
                response = requests.get(self.url + tfl_id, timeout=timeout)
                response.raise_for_status()
                logger.info("%s. %s -> %s%s", response.status_code, response.reason, self.url, tfl_id)
                return response.json()
            except requests.RequestException as err:
                last_error = err
                retry_secs = min(2 ** retries * 5, MAX_BACKOFF)
                logger.warning("Request error: %s. Retrying in %d seconds.", err, retry_secs)
                time.sleep(retry_secs)
                retries += 1

        logger.error("Max retries exceeded for StopPoint ID: %s. Last error: %s", tfl_id, last_error)
        return {"arrivals": [{"noInfo": f"Failed to fetch data for {tfl_id} after {MAX_RETRIES} retries. Last error: {last_error}"}]}

    def get_stop_name(self, stop_id: str) -> Optional[str]:
        if stop_id in self.stop_name_cache:
            return self.stop_name_cache[stop_id]
        json_result = self.get_stops(stop_id, 10)
        stop_name = json_result.get('commonName') if json_result else None
        if stop_name:
            self.stop_name_cache[stop_id] = stop_name
        return stop_name

    def parse_arrival_item(self, item: Dict[str, Any], number: int) -> Dict[str, str]:
        read_time = dt.strptime(item['expectedArrival'], "%Y-%m-%dT%H:%M:%SZ")
        local_dt = self.utc_to_local(read_time)
        arrival_time = local_dt.strftime(self.time_format)
        away_min = math.floor(int(item['timeToStation']) / 60)
        due_in = 'due' if away_min == 0 else f'{away_min}min'
        clean_destination = item['destinationName']
        for suffix in [
            "Underground Station",
            "Rail Station",
            "DLR Station",
            "Bus Station",
            "Tram Stop",
            "Coach Station"
        ]:
            clean_destination = clean_destination.replace(suffix, "").strip()
        return {
            "number": str(number),
            "lineName": item['lineName'],
            "destinationName": clean_destination,
            "arrivalTime": arrival_time,
            "dueIn": due_in
        }

    def get_arrival_times(self, stop_id: str, num_services: int) -> Dict[str, Union[str, List[Dict[str, str]]]]:
        services = []
        json_result = self.get_stops(f"{stop_id}/Arrivals", 10)
        if isinstance(json_result, list):
            json_result.sort(key=lambda x: x["expectedArrival"])
        stop_name = self.get_stop_name(stop_id)
        date_and_time = dt.now(self.local_tz).strftime(f"{self.date_format} {self.time_format}")
        for i, item in enumerate(json_result or []):
            services.append(self.parse_arrival_item(item, i + 1))
            if i + 1 >= num_services:
                break
        if not services:
            services.append({"noInfo": "No information at this time."})
        return {
            "stopName": stop_name or "Unknown Stop",
            "dateAndTime": date_and_time,
            "arrivals": services,
        }

    def get_all_arrivals(self) -> List[Dict[str, Union[str, List[Dict[str, str]]]]]:
        all_data = []
        try:
            self.config.read(self.config_file)
            if CONFIG_SECTION not in self.config:
                logger.error("Config section '%s' not found in file: %s", CONFIG_SECTION, self.config_file)
                return [{"stopName": "N/A", "dateAndTime": dt.now(self.local_tz).strftime(f"{self.date_format} {self.time_format}"), "arrivals": [{"noInfo": f"Missing section '{CONFIG_SECTION}' in config."}]}]
            stop_ids = self.config.getlist(CONFIG_SECTION, 'stopid')
            num_services_list = self.config.getlist(CONFIG_SECTION, 'num_services')
            for stop_id, num in zip(stop_ids, num_services_list):
                all_data.append(self.get_arrival_times(stop_id, int(num)))
        except Exception as e:
            logger.exception("Failed to read config or retrieve arrivals: %s", e)
            all_data.append({"stopName": "N/A", "dateAndTime": dt.now(self.local_tz).strftime(f"{self.date_format} {self.time_format}"), "arrivals": [{"noInfo": "An error occurred while processing configuration."}]})
        return all_data


def main() -> None:
    def print_json(data: Any) -> None:
        print(json.dumps(data, indent=4))

    def print_text(data: List[Dict[str, Any]], line_filter: Optional[str] = None, dest_filter: Optional[str] = None) -> None:
        for stop in data:
            align = math.ceil((76 + len(stop['stopName'])) / 2)
            print(f"\033[1;33;40m{stop['stopName']:>{align}}\033[0m\n")
            for service in stop['arrivals']:
                if 'noInfo' in service:
                    print(f"\033[1;33;40m{service['noInfo']}\033[0m")
                elif (not line_filter or service['lineName'].lower() == line_filter.lower()) and \
                     (not dest_filter or dest_filter.lower() in service['destinationName'].lower()):
                    line_width = 10 if len(service['lineName']) > 4 else 4
                    dest_width = 48 if line_width == 10 else 54
                    line_align = '>' if line_width == 4 else '<'
                    print(
                        f"\033[0;33;40m{service['number']:3} "
                        f"{service['lineName']:{line_align}{line_width}} "
                        f"{service['destinationName']:>{dest_width}} "
                        f"{service['arrivalTime']:>9} "
                        f"{service['dueIn']:>6}\033[0m"
                    )
            print("\n")

    def formatter(prog: str) -> argparse.HelpFormatter:
        return argparse.HelpFormatter(prog, max_help_position=100, width=200)

    parser = argparse.ArgumentParser(
        description="Get arrival data (bus/tube) from TFL",
        formatter_class=formatter
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-t', '--text', action='store_true', help='print formatted text')
    group.add_argument('-j', '--json', action='store_true', help='pretty print json (default)')
    parser.add_argument('-c', '--config', type=Path, help='path to local config file')
    parser.add_argument('--route', type=str, help='filter by line name or bus number(e.g. "Victoria" or "73")')
    parser.add_argument('--destination', type=str, help='filter by destination name (e.g. "Ealing Broadway")')
    args = parser.parse_args()

    monitor = TFLBusMonitor(config_file=args.config)
    arrivals_json = monitor.get_all_arrivals()

    if args.text:
        print_text(arrivals_json, args.route, args.destination)
    else:
        print_json(arrivals_json)


if __name__ == "__main__":
    main()

