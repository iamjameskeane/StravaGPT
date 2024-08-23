import base64
import requests
import pandas as pd
import polars as pl
import json
from datetime import datetime
from tqdm import tqdm
from strava import strava
from openai import OpenAI
from plotter import create_route_plot

# Function to encode the image
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

if __name__ == "__main__":
    MAPBOX_ACCESS_TOKEN = open("keys/mapbox.key").read().strip()
    CLIENT_ID = open("keys/strava_client_id.key").read().strip()
    CLIENT_SECRET = open("keys/strava_client_secret.key").read().strip()
    REDIRECT_URI = "http://localhost:8080"
    OPENAI_KEY = open("keys/openai.key").read().strip()

    openai_client = OpenAI(api_key=OPENAI_KEY)

    client = strava(CLIENT_ID, REDIRECT_URI, CLIENT_SECRET)
    client.authorise()
    activities = client.get_activities()

    # Define the column names (ensure these match the actual activity fields)
    columns = [
        "id", "achievement_count", "athlete", "athlete_count", "average_speed", "average_watts",
        "comment_count", "commute", "device_watts", "distance", "elapsed_time", "elev_high",
        "elev_low", "end_latlng", "external_id", "flagged", "gear_id", "has_kudoed",
        "hide_from_home", "kilojoules", "kudos_count", "manual", "map", "max_speed", "max_watts",
        "moving_time", "name", "photo_count", "private", "sport_type", "start_date",
        "start_date_local", "start_latlng", "timezone", "total_elevation_gain", "total_photo_count",
        "trainer", "type", "upload_id", "upload_id_str", "weighted_average_watts", "workout_type",
        "best_efforts", "calories", "description", "device_name", "embed_token", "gear", "laps",
        "photos", "segment_efforts", "splits_metric", "splits_standard", "guid", "utc_offset",
        "location_city", "location_state", "location_country", "start_latitude", "start_longitude",
        "pr_count", "suffer_score", "has_heartrate", "average_heartrate", "max_heartrate",
        "average_cadence", "average_temp", "instagram_primary_photo", "partner_logo_url",
        "partner_brand_tag", "from_accepted_tag", "segment_leaderboard_opt_out", "perceived_exertion"
    ]

    # Create a Pandas DataFrame
    activities_df = pd.DataFrame(columns=columns)

    # Add the activities to the DataFrame
    for activity in tqdm(activities, desc="Loading Activities..."):
        activity_dict = activity.to_dict()
        activities_df = pd.concat([activities_df, pd.DataFrame([activity_dict])], ignore_index=True)

    # Convert the Pandas DataFrame to Polars DataFrame
    activities_pl = pl.from_pandas(activities_df)

    # Schema
    schema = activities_pl.schema

    def query_data(query):
        return activities_pl.sql(query)

    def plot_route(activity_id, zoom):
        try:
            streams = client.get_activity_streams(activity_id, types=["latlng"], resolution="medium")
            return create_route_plot(streams["latlng"], MAPBOX_ACCESS_TOKEN, zoom, "route_map.jpg")
        except Exception as e:
            return("Activity Not Found")
    
    def get_activity_data(activity_id, stream_types, resolution):
        try:
            streams = client.get_activity_streams(activity_id, types=stream_types, resolution=resolution)
            return list(zip(*[streams[key].data for key in streams.keys()]))
        except Exception as e:
            return("Activity Not Found")

    tools = [
        {
        "type": "function",
        "name": "query_data",
        "function": {
            "name": "query_data",
            "description": "Query Strava Data using SQL Queries. Call this whenever you need to execute an SQL query on Strava data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The SQL query to execute",
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "plot_route",
            "description": "Plot the route of an activity. Call this to get a map of the route of an activity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "activity_id": {
                        "type": "string",
                        "description": "The ActivityID of the activity to plot, this is a numeric value",
                    },
                    "zoom": {
                        "type": "integer",
                        "description": "The zoom level of the map 0-22, (0, The Earth),  (3, A continent) (4, Large islands) (6, Large rivers) (10, Large roads) (15, Buildings)",
                    },
                },
                "required": ["activity_id", "zoom"],
                "additionalProperties": False,
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_activity_data",
            "description": "Get the stream data of an activity. Call this to get indepth data of an activity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "activity_id": {
                        "type": "string",
                        "description": "The ActivityID of the activity to plot, this is a numeric value",
                    },
                    "stream_types": {
                        "type": "array",
                        "description": "A list of the types of streams to fetch.",
                        "items": {
                            "type": "string",
                            "enum": ["time", "latlng", "distance", "altitude", "velocity_smooth", "heartrate", "cadence", "watts", "temp", "moving", "grade_smooth"],
                        }
                    },
                    "resolution": {
                        "type": "string",
                        "description": "Indicates desired number of data points. ‘low’ (100) or ‘medium’ (1000)",
                        "enum": ["low", "medium"],
                    },
                },
                "required": ["activity_id", "stream_types", "resolution"],
                "additionalProperties": False,
            },
        }
    }
    ]


    system_prompt = open("./system_prompt.txt").read().replace("***schema***", str(schema))
    system_prompt = system_prompt.replace("***current_date***", str(datetime.now()))

    def process_tool_calls(messages, response):
        for tool_call in response.choices[0].message.tool_calls:
            tool_name = tool_call.function.name
            tool_id = tool_call.id
            tool_args = json.loads(tool_call.function.arguments)

            if tool_name == "query_data":
                sql_query = tool_args["query"]
                try:
                    result = str(query_data(sql_query).to_dicts())
                except Exception as e:
                    result = {"error": str(e)}

                tool_call_result_message = {
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": json.dumps(result)
                }
                
                messages.append(response.choices[0].message)
                messages.append(tool_call_result_message)

            elif tool_name == "get_activity_data":
                activity_id = tool_args["activity_id"]
                stream_types = tool_args["stream_types"]
                resolution = tool_args["resolution"]
                result = get_activity_data(activity_id, stream_types, resolution)
                if result == "Activity Not Found":
                    tool_call_result_message = {
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "content": "Activity Not Found",
                    }
                else:
                    tool_call_result_message = {
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "content": json.dumps(result)
                    }
                    messages.append(response.choices[0].message)
                    messages.append(tool_call_result_message)

            elif tool_name == "plot_route":
                messages.append(response.choices[0].message)

                activity_id = tool_args["activity_id"]
                zoom = tool_args["zoom"]
                image_path = plot_route(activity_id, zoom)
                
                if image_path == "Activity Not Found":
                    tool_call_result_message = {
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "content": "Activity Not Found",
                    }
                    messages.append(tool_call_result_message)
                else:
                    tool_call_result_message = {
                            "role": "tool",
                            "tool_call_id": tool_id,
                            "content": "Graphs for activity " + activity_id + "have been generated.",
                        }
                    messages.append(tool_call_result_message)

                    encoded_image = encode_image(image_path)
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

    messages = [{"role": "system", "content": system_prompt}]
    while True:
        # User message input
        print("User > ", end="")
        message = input()

        if message.lower() == "exit":
            break

        messages.append({"role": "user", "content": message})

        # Get the initial response from ChatGPT
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=tools,
            temperature=0.3
        )

        #while stop reason is tool_call
        print("System > I'm thiking...")
        while response.choices[0].finish_reason == "tool_calls":
            messages = process_tool_calls(messages, response)

            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=tools,
                temperature=0.3
            )

        # Handle the final response
        print("System > " + response.choices[0].message.content)
        messages.append({"role": "system", "content": response.choices[0].message.content})