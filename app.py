import streamlit as st
from client import StravaGPT
import urllib
import dotenv
import os
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('run.log'),  # Logs to a file
        logging.StreamHandler()  # Logs to console
    ]
)
logging.getLogger("watchdog").setLevel(logging.WARNING)


logging.info("Starting StravaGPT Streamlit app")

st.set_page_config(page_title="StravaGPT", layout="wide")
st.title("StravaGPT - AI Chat Bot with Access to Strava API")

# Load environment variables
dotenv.load_dotenv()
logging.debug("Loaded environment variables")

# Initialize Strava client parameters
client_id = os.getenv("STRAVA_CLIENT_ID")
client_secret = os.getenv("STRAVA_CLIENT_SECRET")
redirect_uri = "http://localhost:5000/authorized"
openai_key = os.getenv("OPENAI_KEY")
mapbox_access_token = os.getenv("MAPBOX_KEY")
tavily_api_key = os.getenv("TAVILY_API_KEY")

logging.debug(f"Client ID: {client_id}, Client Secret: {client_secret}, Redirect URI: {redirect_uri}")
logging.debug(f"OpenAI Key: {openai_key}, Mapbox Token: {mapbox_access_token}, Tavily API Key: {tavily_api_key}")

# Initialize session state variables
if "messages" not in st.session_state:
    st.session_state.messages = []
    logging.debug("Initialized session state 'messages'")

if "client" not in st.session_state:
    st.session_state.client = None
    logging.debug("Initialized session state 'client'")

if "authorised" not in st.session_state:
    st.session_state.authorised = False
    logging.debug("Initialized session state 'authorised'")

if "data_fetched" not in st.session_state:
    st.session_state.data_fetched = False
    logging.debug("Initialized session state 'data_fetched'")

# Authorize Strava client
if st.session_state.client is None:
    logging.info("No existing Strava client found, creating new client")
    strava_client = StravaGPT(client_id, redirect_uri, client_secret, openai_key, mapbox_access_token, tavily_api_key)
    authorisation_url = strava_client.client.get_authorisation_url()
    logging.debug(f"Generated authorisation URL: {authorisation_url}")

    # Display authorization URL
    st.markdown(f"Please visit the following URL to authorize the app: [Authorize Strava]({authorisation_url})")

    auth_url = st.text_input("After authorizing, please enter the full redirect URL you were redirected to:")

    if auth_url:
        logging.debug(f"Received redirect URL from user: {auth_url}")
        # Parse URL to extract the authorization code
        parsed_url = urllib.parse.urlparse(auth_url)
        code = urllib.parse.parse_qs(parsed_url.query).get("code", [None])[0]
        if code:
            logging.info("Authorization code found, exchanging for token")
            try:
                token_response = strava_client.client.exchange_code_for_token(code)
                logging.debug(f"Token response: {token_response}")
                strava_client.client.set_tokens(token_response)
                st.session_state.client = strava_client
                st.session_state.authorised = True
                st.success("Authorization successful!")
                logging.info("Authorization successful, client initialized")
            except Exception as e:
                logging.error(f"Error exchanging code for token: {e}")
                st.error(f"Error: {str(e)}")
        else:
            logging.warning("No authorization code found in URL")
            st.error("Error: No authorization code found in the URL.")
else:
    logging.info("Using existing Strava client from session state")
    strava_client = st.session_state.client

# Fetch Strava data
if st.session_state.authorised and not st.session_state.data_fetched:
    logging.info("User is authorized but data not fetched yet")
    if st.button("Fetch Strava Data"):
        logging.info("Fetch Strava Data button clicked")
        try:
            with st.spinner("Fetching Strava data..."):
                strava_client.fetch_activities()
                if strava_client.activities is None or strava_client.activities == []:
                    logging.info("No Strava activities found")
                    st.error("No Strava activities found")
                    st.session_state.data_fetched = False
                else:
                    logging.debug("Strava activities fetched")

                    strava_client.load_system_prompt()
                    logging.debug("System prompt loaded")
                    strava_client.update_system_prompt_with_data()
                    logging.debug("System prompt updated with data")
                    st.session_state.data_fetched = True
                    st.success("Data fetched successfully!")
                    logging.info("Data fe``tched successfully")
        except Exception as e:
            logging.error(f"Error fetching Strava data: {e}")
            st.error(f"Error fetching Strava data: {str(e)}")

# Main chat interface
if st.session_state.authorised and st.session_state.data_fetched:
    logging.info("Displaying chat interface")
    
    # Display existing messages
    for i, message in enumerate(st.session_state.messages):
        logging.debug(f"Displaying message {i} - Role: {message['role']}")
        if message["role"] == "user":
            with st.chat_message("user"):
                st.markdown(message["content"])
        elif message["role"] == "assistant":
            with st.chat_message("assistant"):
                st.markdown(message["content"])
                if "plots" in message and message["plots"]:
                    logging.debug(f"Displaying {len(message['plots'])} plot(s)")
                    for fig in message["plots"]:
                        st.plotly_chart(fig, use_container_width=True)

    # User input
    if user_input := st.chat_input("Ask StravaGPT anything..."):
        logging.debug(f"Received user input: {user_input}")
        
        # Append user message to session state
        st.session_state.messages.append({"role": "user", "content": user_input})
        logging.debug("User message appended to session state")

        # Display user message
        with st.chat_message("user"):
            st.markdown(user_input)

        # Get StravaGPT's response and any generated plots
        try:
            response_text, generated_plots = strava_client.ask_question(user_input)
            logging.debug("StravaGPT response received")

            # Append assistant response
            st.session_state.messages.append({
                "role": "assistant",
                "content": response_text,
                "plots": generated_plots
            })
            logging.debug("Assistant response appended to session state")

            # Display assistant response
            with st.chat_message("assistant"):
                st.markdown(response_text)
                if generated_plots:
                    logging.debug(f"Displaying {len(generated_plots)} plot(s)")
                    for fig in generated_plots:
                        st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            logging.error(f"Error in StravaGPT response: {e}")
            st.error(f"Error: {str(e)}")

logging.info("App execution completed")
