import base64
import pandas as pd
import polars as pl
import json
from datetime import datetime
import os
from openai import OpenAI
from tavily import TavilyClient
import plotly.io as pio
import requests

from strava import Strava
from plotter import create_route_plot
from constants import columns, tools, banner

import concurrent.futures
import logging

# Set up logging configuration
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('run.log'),  # Logs to a file
        logging.StreamHandler()  # Logs to console
    ]
)
logging.getLogger("watchdog").setLevel(logging.WARNING)


class StravaGPT:
    def __init__(self, client_id, redirect_uri, client_secret, openai_key, mapbox_access_token, tavily_api_key):
        logging.info("Initializing StravaGPT with provided API keys and credentials.")
        
        self.mapbox_access_token = mapbox_access_token
        self.openai_client = OpenAI(api_key=openai_key)
        self.client = Strava(client_id, redirect_uri, client_secret)
        self.tavily = TavilyClient(api_key=tavily_api_key)
        self.tools = tools

        # Initialize empty attributes to store fetched data
        self.activities_df = pd.DataFrame(columns=columns)
        self.activities_pl = None
        self.schema = None
        self.system_prompt = None
        self.messages = []
        self.generated_plots = []  # Initialize an empty list to store generated plots
        self.images = []  # Initialize an empty list to store generated images

        logging.info("StravaGPT initialized successfully.")

    # Authorize the Strava client
    def authorise(self):
        logging.info("Authorizing Strava client.")
        self.client.authorise()
        logging.info("Strava client authorization complete.")

    # Fetch the activities and prepare the data for further use
    def fetch_activities(self):
        logging.info("Fetching activities from Strava.")
        try:
            self.activities = self.client.get_activities()
            logging.debug(f"Fetched activities.")
            for activity in self.activities:
                activity_dict = activity.to_dict()
                self.activities_df = pd.concat([self.activities_df, pd.DataFrame([activity_dict])], ignore_index=True)

            #check records in activities_df
            logging.debug(f"Activities DataFrame shape: {self.activities_df.shape}")

            if self.activities_df.shape[0] == 0:
                logging.info("No activities found.")
                return

            # Convert the pandas DataFrame to a polars DataFrame and store its schema
            self.activities_pl = pl.from_pandas(self.activities_df)
            self.schema = self.activities_pl.schema
            logging.info("Activities fetched and processed into DataFrame.")
        except Exception as e:
            logging.error(f"Error fetching activities: {str(e)}")

    # Load the system prompt template from a file
    def load_system_prompt(self):
        logging.info("Loading system prompt template.")
        try:
            package_dir = os.path.dirname(__file__)
            system_prompt_path = os.path.join(package_dir, "system_prompt.txt")

            with open(system_prompt_path, "r") as f:
                self.system_prompt = f.read().replace("***schema***", str(self.schema))

            self.system_prompt = self.system_prompt.replace("***current_date***", str(datetime.now()))
            logging.info("System prompt loaded successfully.")
        except Exception as e:
            logging.error(f"Error loading system prompt: {str(e)}")

    # Update the system prompt with athlete data and stats
    def update_system_prompt_with_data(self):
        logging.info("Updating system prompt with athlete data and statistics.")
        try:
            athlete = self.client.get_athlete()
            athlete_data = {
                "name": athlete.firstname + " " + athlete.lastname,
                "sex": athlete.sex,
                "location": f"{athlete.city}, {athlete.state}, {athlete.country}"
            }
            self.system_prompt = self.system_prompt.replace("***athlete_data***", str(athlete_data))

            athlete_stats_data = self.client.get_athlete_stats(athlete.id)
            athlete_stats = self._extract_athlete_stats(athlete_stats_data)
            self.system_prompt = self.system_prompt.replace("***athlete_stats***", str(athlete_stats))

            # Add system message
            self.messages.append({"role": "system", "content": self.system_prompt})
            logging.info("System prompt updated with athlete data and stats.")
        except Exception as e:
            logging.error(f"Error updating system prompt with data: {str(e)}")

    # Helper method to extract athlete statistics
    def _extract_athlete_stats(self, athlete_stats_data):
        logging.debug("Extracting athlete statistics.")
        try:
            return [
                {
                    "all_ride_totals": {
                        "count": athlete_stats_data.all_ride_totals.count,
                        "distance": athlete_stats_data.all_ride_totals.distance,
                        "elapsed_time": athlete_stats_data.all_ride_totals.elapsed_time,
                        "elevation_gain": athlete_stats_data.all_ride_totals.elevation_gain,
                        "moving_time": athlete_stats_data.all_ride_totals.moving_time,
                    }
                },
                {
                    "all_run_totals": {
                        "count": athlete_stats_data.all_run_totals.count,
                        "distance": athlete_stats_data.all_run_totals.distance,
                        "elapsed_time": athlete_stats_data.all_run_totals.elapsed_time,
                        "elevation_gain": athlete_stats_data.all_run_totals.elevation_gain,
                        "moving_time": athlete_stats_data.all_run_totals.moving_time,
                    }
                },
                {
                    "all_swim_totals": {
                        "count": athlete_stats_data.all_swim_totals.count,
                        "distance": athlete_stats_data.all_swim_totals.distance,
                        "elapsed_time": athlete_stats_data.all_swim_totals.elapsed_time,
                        "elevation_gain": athlete_stats_data.all_swim_totals.elevation_gain,
                        "moving_time": athlete_stats_data.all_swim_totals.moving_time,
                    }
                }
            ]
        except Exception as e:
            logging.error(f"Error extracting athlete stats: {str(e)}")
            return []

    # Encode image to base64
    def encode_image(self, image_bytes):
        logging.debug("Encoding image to base64.")
        try:
            return base64.b64encode(image_bytes).decode('utf-8')
        except Exception as e:
            logging.error(f"Error encoding image: {str(e)}")
            return None

    # Query data using SQL
    def query_data(self, query):
        logging.info(f"Querying data with query: {query}")
        try:
            return self.activities_pl.sql(query)
        except Exception as e:
            logging.error(f"Error querying data: {str(e)}")
            return None

    # Generate image description using OpenAI Vision capabilities
    def generate_image_description(self, image_url):
        logging.info(f"Generating image description for image at: {image_url}")
        try:
            messages = [
                {
                    "role": "system",
                    "content": "You are an assistant that provides detailed descriptions of images."
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Describe the image"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_url
                            },
                        },
                    ]
                },
            ]

            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.5,
                max_tokens=300,
            )

            return response.choices[0].message.content
        except Exception as e:
            logging.error(f"Error generating image description: {str(e)}")
            return None

    # Plot route and return the figure and description
    def plot_route(self, activity_id, zoom):
        logging.info(f"Plotting route for activity ID: {activity_id} with zoom level: {zoom}")
        try:
            streams = self.client.get_activity_streams(activity_id, types=["latlng"], resolution="medium")
            fig = create_route_plot(streams["latlng"], self.mapbox_access_token, zoom)

            # Convert figure to image and encode to base64
            image_bytes = fig.to_image(format="jpeg")
            image_base64 = self.encode_image(image_bytes)
            image_url = f"data:image/jpeg;base64,{image_base64}"

            # Generate description of the plot
            description = self.generate_image_description(image_url)

            logging.info(f"Route plotted successfully for activity ID: {activity_id}")
            return fig, description  # Return the Plotly figure and description
        except Exception as e:
            logging.error(f"Error plotting route: {str(e)}")
            return f"Error: {str(e)}", None

    # Get activity data
    def get_activity_data(self, activity_id, stream_types, resolution):
        logging.info(f"Fetching activity data for activity ID: {activity_id}")
        try:
            streams = self.client.get_activity_streams(activity_id, types=stream_types, resolution=resolution)
            return list(zip(*[streams[key].data for key in streams.keys()]))
        except Exception as e:
            logging.error(f"Error fetching activity data: {str(e)}")
            return f"Error: {str(e)}"

    # Get activity photos and generate descriptions in parallel
    def get_activity_photos(self, activity_id, max_resolution=2000):
        logging.info(f"Fetching activity photos for activity ID: {activity_id}")
        try:
            photos = self.client.get_activity_photos(activity_id, max_resolution)

            def process_photo(photo_url):
                try:
                    # Generate description
                    description = self.generate_image_description(photo_url)

                    return {
                        "url": photo_url,
                        "description": description
                    }
                except Exception as e:
                    logging.error(f"Error processing photo: {str(e)}")
                    return {
                        "url": photo_url,
                        "description": f"Error in processing image: {str(e)}"
                    }

            # Process photos in parallel
            with concurrent.futures.ThreadPoolExecutor() as executor:
                photo_descriptions = list(executor.map(process_photo, photos))

            logging.info(f"Fetched and processed {len(photo_descriptions)} photos for activity ID: {activity_id}")
            return photo_descriptions
        except Exception as e:
            logging.error(f"Error fetching activity photos: {str(e)}")
            return []

    def search(self, query):
        logging.info(f"Performing search with query: {query}")
        return self.tavily.search(query)

    # Process tool calls
    def process_tool_calls(self, messages, response):
        for tool_call in response.choices[0].message.tool_calls:
            tool_name = tool_call.function.name
            tool_id = tool_call.id
            tool_args = json.loads(tool_call.function.arguments)
            logging.info(f"Processing tool call: {tool_name} with arguments: {tool_args}")

            if tool_name == "query_data":
                logging.info("Processing query_data tool call")
                messages.append(response.choices[0].message)
                sql_query = tool_args["query"]
                logging.info(f"SQL query: {sql_query}")
                try:
                    result = str(self.query_data(sql_query).to_dicts())
                    logging.info(f"Query result: {result}")
                except Exception as e:
                    result = {"Error": str(e)}

                tool_call_result_message = {
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": json.dumps(result)
                }
                messages.append(tool_call_result_message)
                logging.info(f"Tool call result message: {tool_call_result_message}")

            elif tool_name == "get_activity_data":
                logging.info("Processing get_activity_data tool call")
                messages.append(response.choices[0].message)
                activity_id = tool_args["activity_id"]
                stream_types = tool_args["stream_types"]
                resolution = tool_args["resolution"]
                logging.info(f"Activity ID: {activity_id}, stream types: {stream_types}, resolution: {resolution}")
                result = self.get_activity_data(activity_id, stream_types, resolution)
                tool_call_result_message = {
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": json.dumps(result)
                }
                messages.append(tool_call_result_message)
                logging.info(f"Tool call result message: {tool_call_result_message}")

            elif tool_name == "plot_route":
                logging.info("Processing plot_route tool call")
                messages.append(response.choices[0].message)

                activity_id = tool_args["activity_id"]
                zoom = tool_args["zoom"]
                logging.info(f"Activity ID: {activity_id}, zoom: {zoom}")
                result, description = self.plot_route(activity_id, zoom)

                if isinstance(result, str) and "Error" in result:
                    logging.error("Error plotting route")
                    tool_call_result_message = {
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "content": result
                    }
                    messages.append(tool_call_result_message)
                else:
                    logging.info(f"Successfully plotted route for {activity_id} with description: {description}")
                    # result is the figure
                    self.generated_plots.append(result)  # Store the figure
                    # Add description to the conversation
                    tool_call_result_message = {
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "content": f"Plot generated for activity {activity_id}. Description: {description}"
                    }
                    messages.append(tool_call_result_message)

            elif tool_name == "get_activity_photos":
                logging.info("Processing get_activity_photos tool call")
                messages.append(response.choices[0].message)
                activity_id = tool_args["activity_id"]
                max_resolution = tool_args.get("max_resolution", 250)
                logging.info(f"Activity ID: {activity_id}, max resolution: {max_resolution}")
                result = self.get_activity_photos(activity_id, max_resolution)

                tool_call_result_message = {
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": json.dumps(result)
                }
                messages.append(tool_call_result_message)
                logging.info(f"Tool call result message: {tool_call_result_message}")

            elif tool_name == "search":
                messages.append(response.choices[0].message)
                query = tool_args["query"]
                logging.info(f"Doing search with query: {query}")
                result = self.search(query)
                tool_call_result_message = {
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": json.dumps(result)
                }
                messages.append(tool_call_result_message)
                logging.info(f"Tool call result message: {tool_call_result_message}")

        return messages

    # Ask question and handle the conversation
    def ask_question(self, question):
        logging.info(f"User: {question}")
        self.generated_plots = []  # Reset generated plots
        self.messages.append({"role": "user", "content": question})

        response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=self.messages,
            tools=self.tools,
            temperature=0.3
        )

        while response.choices[0].finish_reason == "tool_calls":
            logging.info("Processing tool calls")
            self.messages = self.process_tool_calls(self.messages, response)

            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=self.messages,
                tools=self.tools,
                temperature=0.3
            )
        logging.info("Done processing tool calls")

        # Append assistant's final message to the conversation
        self.messages.append({"role": "assistant", "content": response.choices[0].message.content})

        logging.info(f"Assistant: {response.choices[0].message.content}")

        return response.choices[0].message.content, self.generated_plots

    # Chat indefinitely (if used outside Streamlit)
    def chat_indefinitely(self):
        print(banner)
        message = "Hey, I'm StravaGPT. What can I help with? 👋"
        print(f"System > {message}")
        
        # Add the system message to the conversation
        self.messages.append({"role": "system", "content": message})
        
        while True:
            try:
                # Capture user input
                user_input = input("User > ")
                
                # Exit condition
                if user_input.lower() == "exit":
                    print("Goodbye!")
                    break
                
                # Process the user's input and get the response
                response_text, _ = self.ask_question(user_input)
                
                # Print the assistant's response
                print(f"Assistant > {response_text}")
            
            except Exception as e:
                # Handle any exceptions in a graceful way
                print(f"Error: {str(e)}. Please try again.")