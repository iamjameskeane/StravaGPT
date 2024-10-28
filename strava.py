import logging
from datetime import datetime
from stravalib.client import Client
import webbrowser
import time
from urllib.parse import urlparse, parse_qs

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('run.log'),  # Logs to a file
        logging.StreamHandler()  # Logs to console
    ]
)
logging.getLogger("watchdog").setLevel(logging.WARNING)


class Strava():
    def __init__(self, client_id, redirect_uri, client_secret):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug(f"Initializing Strava client with client_id: {client_id}, redirect_uri: {redirect_uri}")
        
        self.client_id = client_id
        self.redirect_uri = redirect_uri
        self.client_secret = client_secret
        self.access_token = None
        self.refresh_token = None
        self.expires_at = None
        self.client = Client()
        self.logger.info("Strava client initialized successfully.")

    def authorise(self):
        self.logger.debug("Starting authorization process...")
        try:
            authorize_url = self.client.authorization_url(client_id=self.client_id, redirect_uri=self.redirect_uri)
            self.logger.debug(f"Generated authorization URL: {authorize_url}")

            webbrowser.open_new_tab(authorize_url)
            self.logger.info("Authorization page opened in browser.")
            
            time.sleep(10)
            
            redirect_response = input("Please paste the full redirect URL here: ")
            self.logger.debug(f"Received redirect response: {redirect_response}")
            
            parsed_url = urlparse(redirect_response)
            code = parse_qs(parsed_url.query).get('code', [None])[0]
            self.logger.debug(f"Parsed authorization code: {code}")

            if not code:
                raise ValueError("No authorization code found in the URL.")
            self.logger.info("Authorization code successfully retrieved.")

        except Exception as e:
            self.logger.error(f"Error during authorization: {str(e)}", exc_info=True)
            print("Falling back to manual input method.")
            print("Please visit this URL to authorize: ", authorize_url)
            code = input("Enter the code you received after authorization: ")

        try:
            token_response = self.client.exchange_code_for_token(
                client_id=self.client_id,
                client_secret=self.client_secret,
                code=code
            )
            self.logger.debug(f"Token exchange response: {token_response}")
            
            self.set_tokens(token_response)
            self.logger.info("Authorization and token exchange successful.")
        except Exception as e:
            self.logger.error(f"Error exchanging code for token: {str(e)}", exc_info=True)
            raise e

    def get_authorisation_url(self):
        try:
            self.logger.debug("Generating authorization URL...")
            url = self.client.authorization_url(client_id=self.client_id, redirect_uri=self.redirect_uri)
            self.logger.debug(f"Authorization URL: {url}")
            return url
        except Exception as e:
            self.logger.error(f"Failed to generate authorization URL: {str(e)}", exc_info=True)
            raise e

    def exchange_code_for_token(self, code):
        try:
            self.logger.debug(f"Exchanging code {code} for token...")
            token_response = self.client.exchange_code_for_token(
                client_id=self.client_id,
                client_secret=self.client_secret,
                code=code
            )
            self.logger.debug(f"Token response: {token_response}")
            return token_response
        except Exception as e:
            self.logger.error(f"Error during token exchange: {str(e)}", exc_info=True)
            raise e

    def set_tokens(self, token_response):
        try:
            self.logger.debug(f"Setting tokens: {token_response}")
            self.access_token = token_response["access_token"]
            self.refresh_token = token_response["refresh_token"]
            self.expires_at = token_response["expires_at"]
            self.client.access_token = self.access_token
            self.logger.info("Tokens set successfully.")
        except Exception as e:
            self.logger.error(f"Error setting tokens: {str(e)}", exc_info=True)
            raise e

    def get_activities(self, start_date=None, end_date=None):
        self.logger.debug(f"Fetching activities from {start_date} to {end_date}...")
        try:
            if start_date is None:
                start_date = datetime(2020, 1, 1)
            if end_date is None:
                end_date = datetime.now()
            
            activities = self.client.get_activities(after=start_date, before=end_date)
            self.logger.info(f"Fetched activities between {start_date} and {end_date}")
            return activities
        except Exception as e:
            self.logger.error(f"Error fetching activities: {str(e)}", exc_info=True)
            raise e

    def get_activity_streams(self, activity_id, types=["time", "heartrate", "latlng"], resolution="medium"):
        self.logger.debug(f"Fetching activity streams for activity_id: {activity_id}, types: {types}, resolution: {resolution}")
        try:
            streams = self.client.get_activity_streams(activity_id, types=types, resolution=resolution)
            self.logger.info(f"Fetched activity streams for activity_id: {activity_id}")
            return streams
        except Exception as e:
            self.logger.error(f"Error fetching activity streams for activity_id: {activity_id}: {str(e)}", exc_info=True)
            raise e

    def get_athlete(self):
        self.logger.debug("Fetching athlete information...")
        try:
            athlete = self.client.get_athlete()
            self.logger.info("Fetched athlete information successfully.")
            return athlete
        except Exception as e:
            self.logger.error(f"Error fetching athlete information: {str(e)}", exc_info=True)
            raise e

    def get_athlete_stats(self, athlete_id):
        self.logger.debug(f"Fetching stats for athlete_id: {athlete_id}")
        try:
            stats = self.client.get_athlete_stats(athlete_id)
            self.logger.info(f"Fetched athlete stats for athlete_id: {athlete_id}")
            return stats
        except Exception as e:
            self.logger.error(f"Error fetching athlete stats for athlete_id: {athlete_id}: {str(e)}", exc_info=True)
            raise e

    def get_activity_photos(self, activity_id, max_resolution=250):
        self.logger.debug(f"Fetching activity photos for activity_id: {activity_id} with resolution: {max_resolution}")
        try:
            batch = self.client.get_activity_photos(activity_id, max_resolution)
            photos = [photo.urls[str(max_resolution)] for photo in batch]
            self.logger.info(f"Fetched {len(photos)} photos for activity_id: {activity_id}")
            return photos
        except Exception as e:
            self.logger.error(f"Error fetching activity photos for activity_id: {activity_id}: {str(e)}", exc_info=True)
            raise e
