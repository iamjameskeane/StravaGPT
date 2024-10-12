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
    },
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
                    "description": "The Activity ID of the activity to plot, this is a unique identifier value from Strava",
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
        "description": "Get the stream data of an activity. Call this to get in-depth data of an activity.",
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
},
{
    "type": "function",
    "function": {
        "name": "get_activity_photos",
        "description": "Get the urls of photos for an activty",
        "parameters": {
            "type": "object",
            "properties": {
                "activity_id": {
                    "type": "string",
                    "description": "The ActivityID of the activity to plot, this is a numeric value",
                },
                "max_resolution": {
                    "type": "integer",
                    "description": "The maximum resolution of the photos to return",
                },
            },
            "required": ["activity_id"],
            "additionalProperties": False,
        },
    }
},
{
    "type": "function",
    "function": {
        "name": "search",
        "description": "Search Internet Using Tavily API",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The query to search for",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    }
}
]

banner = r"""
    ____  __.             ________   
    |    |/ _| __ __  ____ \_____  \  
    |      <  |  |  \/    \  _(__  <  
    |    |  \ |  |  /   |  \/       \ 
    |____|__ \|____/|___|  /______  / 
            \/           \/       \/  
        StravaGPT - AI Chat Bot
        with Access to Strava API
"""