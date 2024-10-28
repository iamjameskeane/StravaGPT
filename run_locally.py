from client import StravaGPT
from dotenv import load_dotenv
import os


load_dotenv()


def main():
    client_id = os.getenv("STRAVA_CLIENT_ID")
    client_secret = os.getenv("STRAVA_CLIENT_SECRET")
    openai_key = os.getenv("OPENAI_KEY")
    mapbox_access_token = os.getenv("MAPBOX_KEY")
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    redirect_uri = "http://localhost:5000/authorized"
    strava_gpt = StravaGPT(client_id, redirect_uri, client_secret, openai_key, mapbox_access_token, tavily_api_key)
    strava_gpt.chat_indefinitely()



if __name__ == "__main__":
    main()