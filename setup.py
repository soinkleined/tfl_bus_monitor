"""
standard package import
"""
from setuptools import setup, find_packages
# read the contents of your README file
from pathlib import Path
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name='tfl_bus_monitor',
    python_requires='>=3.9',
    version='0.8',
    author='David Klein',
    author_email='david@soinkleined.com',
    url='https://www.soinkleined.com',
    description='TFL Bus Monitor - download Transport for London bus arrival times',
    long_description=long_description,
    long_description_content_type='text/markdown',
    packages=find_packages(),
    install_requires=[
        'requests>=2.0.0',
        'pytz>=2021.1',
    ],
    package_data={
        'tfl_bus_monitor': ['config/busstop_config.ini'],
    },
    entry_points={
        'console_scripts': [
            'busstop = tfl_bus_monitor.tfl_bus_monitor:main',
        ],
    },
)
