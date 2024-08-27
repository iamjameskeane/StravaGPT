import base64
import pandas as pd
import polars as pl
import json
from datetime import datetime
import os
import threading
import itertools
import time
from stravagpt.strava import Strava
from openai import OpenAI
from stravagpt.plotter import create_route_plot
from stravagpt.constants import columns, tools, banner

class StravaGPT:
    def __init__(self, client_id, redirect_uri, client_secret, openai_key, mapbox_access_token):
        self.mapbox_access_token = mapbox_access_token
        self.openai_client = OpenAI(api_key=openai_key)
        self.client = Strava(client_id, redirect_uri, client_secret)
        self.client.authorise()

        # Define and start the loading animation in a separate thread
        self.loading = True
        self.loader_thread = threading.Thread(target=self._loader_animation, daemon=True)
        self.loader_thread.start()

        # Fetch and process activities
        self.activities = self.client.get_activities()
        self.activities_df = pd.DataFrame(columns=columns)
        for activity in self.activities:
            activity_dict = activity.to_dict()
            self.activities_df = pd.concat([self.activities_df, pd.DataFrame([activity_dict])], ignore_index=True)

        # Stop the loading animation
        self.loading = False
        self.loader_thread.join()

        self.activities_pl = pl.from_pandas(self.activities_df)
        self.schema = self.activities_pl.schema

        # Construct path to system_prompt.txt relative to the package directory
        package_dir = os.path.dirname(__file__)
        system_prompt_path = os.path.join(package_dir, "system_prompt.txt")
        
        with open(system_prompt_path, "r") as f:
            self.system_prompt = f.read().replace("***schema***", str(self.schema))
        
        self.system_prompt = self.system_prompt.replace("***current_date***", str(datetime.now()))
        
        athlete = self.client.get_athlete()
        athlete_data = {
            "name": athlete.firstname + " " + athlete.lastname,
            "sex": athlete.sex,
            "location": athlete.city + ", " + athlete.state + ", " + athlete.country
        }
        self.system_prompt = self.system_prompt.replace("***athlete_data***", str(athlete_data))

        athlete_stats_data = self.client.get_athlete_stats(athlete.id)

        athlete_stats = [{
            "all_ride_totals" :
                {
                    "count" : athlete_stats_data.all_ride_totals.count,
                    "distance" : athlete_stats_data.all_ride_totals.distance,
                    "elapsed_time" : athlete_stats_data.all_ride_totals.elapsed_time,
                    "elevation_gain" : athlete_stats_data.all_ride_totals.elevation_gain,
                    "moving_time" : athlete_stats_data.all_ride_totals.moving_time,
                },
            },
            {
            "all_run_totals" :
                {
                    "count" : athlete_stats_data.all_run_totals.count,
                    "distance" : athlete_stats_data.all_run_totals.distance,
                    "elapsed_time" : athlete_stats_data.all_run_totals.elapsed_time,
                    "elevation_gain" : athlete_stats_data.all_run_totals.elevation_gain,
                    "moving_time" : athlete_stats_data.all_run_totals.moving_time,
                }
            },
            {
            "all_swim_totals" :
                {
                    "count" : athlete_stats_data.all_swim_totals.count,
                    "distance" : athlete_stats_data.all_swim_totals.distance,
                    "elapsed_time" : athlete_stats_data.all_swim_totals.elapsed_time,
                    "elevation_gain" : athlete_stats_data.all_swim_totals.elevation_gain,
                    "moving_time" : athlete_stats_data.all_swim_totals.moving_time,
                }
            }]
        
        self.system_prompt = self.system_prompt.replace("***athlete_stats***", str(athlete_stats))

        self.messages = [{"role": "system", "content": self.system_prompt}]
        self.tools = tools

    def _loader_animation(self):
        frames = [
            "[===       ]",
            "[ ===      ]",
            "[  ===     ]",
            "[   ===    ]",
            "[    ===   ]",
            "[     ===  ]",
            "[      === ]",
            "[       ===]",
            "[      === ]",
            "[     ===  ]",
            "[    ===   ]",
            "[   ===    ]",
            "[  ===     ]",
            "[ ===      ]"
        ]
        idx = 0
        while self.loading:
            print(f'\rLoading activities {frames[idx % len(frames)]}', end='', flush=True)
            time.sleep(0.1)
            idx += 1
        print('\rActivities loaded successfully!        ', end='\r')
        print("\n")

    def _thinking_animation(self):
        frames = ["—", "\\", "|", "/"]
        idx = 0
        while not self.thinking_complete:
            print(f'\rSystem > Thinking {frames[idx % len(frames)]}', end='', flush=True)
            time.sleep(0.1)
            idx += 1
        print('\rSystem > Thinking complete!            ', end='\r')

    def encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def query_data(self, query):
        return self.activities_pl.sql(query)

    def plot_route(self, activity_id, zoom):
        try:
            streams = self.client.get_activity_streams(activity_id, types=["latlng"], resolution="medium")

            # Construct path to the plots directory within the package directory
            package_dir = os.path.dirname(__file__)
            plots_dir = os.path.join(package_dir, "plots")
            os.makedirs(plots_dir, exist_ok=True)
            
            plot_path = os.path.join(plots_dir, "route_map.jpg")
            create_route_plot(streams["latlng"], self.mapbox_access_token, zoom, plot_path)
            return plot_path
          
        except Exception as e:
            return(f"Error: {str(e)}")
    
    def get_activity_data(self, activity_id, stream_types, resolution):
        try:
            streams = self.client.get_activity_streams(activity_id, types=stream_types, resolution=resolution)
            return list(zip(*[streams[key].data for key in streams.keys()]))
        except Exception as e:
            return(f"Error: {str(e)}")

    def process_tool_calls(self, messages, response):
        for tool_call in response.choices[0].message.tool_calls:
            tool_name = tool_call.function.name
            tool_id = tool_call.id
            tool_args = json.loads(tool_call.function.arguments)

            if tool_name == "query_data":
                messages.append(response.choices[0].message)
                sql_query = tool_args["query"]
                try:
                    result = str(self.query_data(sql_query).to_dicts())
                except Exception as e:
                    result = {"Error": str(e)}

                tool_call_result_message = {
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": json.dumps(result)
                }
                messages.append(tool_call_result_message)

            elif tool_name == "get_activity_data":
                messages.append(response.choices[0].message)
                activity_id = tool_args["activity_id"]
                stream_types = tool_args["stream_types"]
                resolution = tool_args["resolution"]
                result = self.get_activity_data(activity_id, stream_types, resolution)
                tool_call_result_message = {
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": json.dumps(result)
                }
                messages.append(tool_call_result_message)

            elif tool_name == "plot_route":
                messages.append(response.choices[0].message)

                activity_id = tool_args["activity_id"]
                zoom = tool_args["zoom"]
                result = self.plot_route(activity_id, zoom)
                
                if "Error" in result:
                    tool_call_result_message = {
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "content": result
                    }
                    messages.append(tool_call_result_message)
                else:
                    tool_call_result_message = {
                            "role": "tool",
                            "tool_call_id": tool_id,
                            "content": f"Graph generated for {activity_id}, saved to {result}",
                        }
                    messages.append(tool_call_result_message)

                    encoded_image = self.encode_image(result)
                    vision_message = {
                        "role": "user",
                        "content": [
                            {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{encoded_image}"
                            }
                            }
                        ]
                    }
                        
                    messages.append(vision_message)

        return messages

    def ask_question(self, question):
        self.messages.append({"role": "user", "content": question})

        #start thinking
        self.thinking_complete = False
        self.loader_thread = threading.Thread(target=self._thinking_animation, daemon=True)
        self.loader_thread.start()

        response = self.openai_client.chat.completions.create(
            model="gpt-4o",
            messages=self.messages,
            tools=self.tools,
            temperature=0.3
        )

        while response.choices[0].finish_reason == "tool_calls":
            self.messages = self.process_tool_calls(self.messages, response)

            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=self.messages,
                tools=self.tools,
                temperature=0.3
            )
            
        #stop thinking
        self.thinking_complete = True
        self.loader_thread.join()
        
        return response.choices[0].message.content

    def chat_indefinitely(self):
        print(banner)
        message = "System > Hey, I'm StravaGPT. What can I help with? 👋 "
        print(message)
        self.messages.append({"role": "system", "content": message})
        while True:
            user_input = input("User > ")
            if user_input.lower() == "exit":
                print("Goodbye!")
                break
            response = self.ask_question(user_input)
            print("System > " + response)