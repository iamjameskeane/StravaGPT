from datetime import datetime
from stravalib.client import Client
import webbrowser
import time
from urllib.parse import urlparse, parse_qs

class Strava():
    def __init__(self, client_id, redirect_uri, client_secret):
        self.client_id = client_id
        self.redirect_uri = redirect_uri
        self.client_secret = client_secret
        self.access_token = None
        self.refresh_token = None
        self.expires_at = None
        self.client = Client()


    def authorise(self):
        authorize_url = self.client.authorization_url(client_id=self.client_id, redirect_uri=self.redirect_uri)
        
        # Try to open the browser and get the code automatically
        try:
            webbrowser.open_new_tab(authorize_url)
            print("Authorization page opened in your default browser.")
            print("Please authorize the application and wait...")
            
            # Wait for a short time to allow the user to authorize
            time.sleep(10)
            
            # Try to get the code from the redirect URL
            redirect_response = input("Please paste the full redirect URL here: ")
            parsed_url = urlparse(redirect_response)
            code = parse_qs(parsed_url.query).get('code', [None])[0]
            
            if code:
                print("Authorization code retrieved successfully.")
            else:
                raise ValueError("No authorization code found in the URL.")
            
        except Exception as e:
            print(f"Automatic authorization failed: {str(e)}")
            print("Falling back to manual input method.")
            print("Please visit this URL to authorize: ", authorize_url)
            code = input("Enter the code you received after authorization: ")
        
        # Exchange the code for tokens
        token_response = self.client.exchange_code_for_token(
            client_id=self.client_id,
            client_secret=self.client_secret,
            code=code
        )
        
        self.access_token = token_response["access_token"]
        self.refresh_token = token_response["refresh_token"]
        self.expires_at = token_response["expires_at"]
        
        # Update the client with the new access token
        self.client.access_token = self.access_token
        
        print("Authorization successful!")

    def get_authorisation_url(self):
        return self.client.authorization_url(client_id=self.client_id, redirect_uri=self.redirect_uri)
    
    def exchange_code_for_token(self, code):
        token_response = self.client.exchange_code_for_token(
            client_id=self.client_id,
            client_secret=self.client_secret,
            code=code
        )
        return token_response
    
    def set_tokens(self, token_response):
        self.access_token = token_response["access_token"]
        self.refresh_token = token_response["refresh_token"]
        self.expires_at = token_response["expires_at"]

        #update access token
        self.client.access_token = self.access_token


    def get_activities(self, start_date=None, end_date=None):
        if start_date is None:
            start_date = datetime(2020, 1, 1)
        if end_date is None:
            end_date = datetime.now()
        
        return self.client.get_activities(after=start_date, before=end_date)

    def get_activity_streams(self, activity_id, types=["time", "heartrate", "latlng"], resolution="medium"):
        streams = self.client.get_activity_streams(activity_id, types=types, resolution=resolution)
        return streams
    
    def get_athlete(self):
        return self.client.get_athlete()
    
    def get_athlete_stats(self, athlete_id):
        return self.client.get_athlete_stats(athlete_id)
    
    def get_activity_photos(self, activity_id, max_resolution=250):
        batch = self.client.get_activity_photos(activity_id, max_resolution)

        photos = []
        for i, photo in enumerate(batch):
            photos.append(photo.urls[str(max_resolution)])
        return photos

