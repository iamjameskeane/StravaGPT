from datetime import datetime
from stravalib.client import Client

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
        authorise_url = self.client.authorization_url(client_id=self.client_id, redirect_uri=self.redirect_uri)
        print("Click the following URL to authorize: ", authorise_url)
        code = input("Enter the code you received after authorization: ")
        token_response = self.client.exchange_code_for_token(client_id=self.client_id, client_secret=self.client_secret, code=code)
        self.access_token = token_response["access_token"]
        self.refresh_token = token_response["refresh_token"]
        self.expires_at = token_response["expires_at"]

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