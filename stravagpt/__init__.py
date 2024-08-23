# Import necessary modules and functions
from .client import StravaGPT  # Import the StravaGPT class from client.py
from .strava import Strava # Import the strava class or functions from strava.py
from .plotter import create_route_plot  # Import functions from plotter.py
from .constants import columns, tools  # Import constants

# Attempt to import the OpenAI module, handle the error if not found
try:
    from openai import OpenAI
except ImportError:
    print("Module OpenAI not found. Make sure it is installed and accessible.")

# Define which names to be available for import when doing 'from stravagpt import *'
__all__ = ['StravaGPT', 'Strava', 'create_route_plot', 'columns', 'tools']