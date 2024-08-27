from stravagpt import StravaGPT


def main():
    client_id = open("keys/strava_client_id.key").read().strip()
    client_secret = open("keys/strava_client_secret.key").read().strip()
    openai_key = open("keys/openai.key").read().strip()
    mapbox_access_token = open("keys/mapbox.key").read().strip()
    redirect_uri = "http://localhost:5000/authorized"

    strava_gpt = StravaGPT(client_id, redirect_uri, client_secret, openai_key, mapbox_access_token)

    strava_gpt.chat_indefinitely()



if __name__ == "__main__":
    main()