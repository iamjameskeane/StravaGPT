import streamlit as st
from client import StravaGPT
import urllib
import dotenv
import os

st.set_page_config(page_title="StravaGPT", layout="wide")
st.title("StravaGPT - AI Chat Bot with Access to Strava API")

dotenv.load_dotenv()

# Initialize Strava client parameters
client_id = os.getenv("STRAVA_CLIENT_ID")
client_secret = os.getenv("STRAVA_CLIENT_SECRET")
redirect_uri = "http://localhost:5000/authorized"
openai_key = os.getenv("OPENAI_KEY")
mapbox_access_token = os.getenv("MAPBOX_KEY")
tavily_api_key = os.getenv("TAVILY_API_KEY")

# Initialize session state variables
if "messages" not in st.session_state:
    st.session_state.messages = []

if "client" not in st.session_state:
    st.session_state.client = None

if "authorised" not in st.session_state:
    st.session_state.authorised = False

if "data_fetched" not in st.session_state:
    st.session_state.data_fetched = False

# Authorize Strava client
if st.session_state.client is None:
    strava_client = StravaGPT(client_id, redirect_uri, client_secret, openai_key, mapbox_access_token, tavily_api_key)
    authorisation_url = strava_client.client.get_authorisation_url()

    # Display authorization URL
    st.markdown(
        f"Please visit the following URL to authorize the app: [Authorize Strava]({authorisation_url})"
    )

    auth_url = st.text_input("After authorizing, please enter the full redirect URL you were redirected to:")

    if auth_url:
        # Parse URL to extract the authorization code
        parsed_url = urllib.parse.urlparse(auth_url)
        code = urllib.parse.parse_qs(parsed_url.query).get("code", [None])[0]
        if code:
            token_response = strava_client.client.exchange_code_for_token(code)
            strava_client.client.set_tokens(token_response)
            st.session_state.client = strava_client
            st.session_state.authorised = True
            st.success("Authorization successful!")
        else:
            st.error("Error: No authorization code found in the URL.")

else:
    strava_client = st.session_state.client

# Fetch Strava data
if st.session_state.authorised and not st.session_state.data_fetched:
    if st.button("Fetch Strava Data"):
        try:
            with st.spinner("Fetching Strava data..."):
                strava_client.fetch_activities()
                strava_client.load_system_prompt()
                strava_client.update_system_prompt_with_data()
                st.session_state.data_fetched = True
                st.success("Data fetched successfully!")
        except Exception as e:
            st.error(f"Error fetching Strava{str(e)}")

# Main chat interface
if st.session_state.authorised and st.session_state.data_fetched:
    # Display existing messages
    for i, message in enumerate(st.session_state.messages):
        if message["role"] == "user":
            with st.chat_message("user"):
                st.markdown(message["content"])
        elif message["role"] == "assistant":
            with st.chat_message("assistant"):
                st.markdown(message["content"])
                if "plots" in message and message["plots"]:
                    for fig in message["plots"]:
                        st.plotly_chart(fig, use_container_width=True)

    # User input
    if user_input := st.chat_input("Ask StravaGPT anything..."):
        # Append user message to session state
        st.session_state.messages.append({"role": "user", "content": user_input})

        # Display user message
        with st.chat_message("user"):
            st.markdown(user_input)

        # Get StravaGPT's response and any generated plots
        response_text, generated_plots = strava_client.ask_question(user_input)

        # Append assistant response
        st.session_state.messages.append({
            "role": "assistant",
            "content": response_text,
            "plots": generated_plots
        })

        # Display assistant response
        with st.chat_message("assistant"):
            st.markdown(response_text)
            if generated_plots:
                for fig in generated_plots:
                    st.plotly_chart(fig, use_container_width=True)