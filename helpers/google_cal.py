from google_auth_oauthlib.flow import Flow
from config import Config, SCOPES

def build_google_flow(state=None):
    return Flow.from_client_config(
        {
            "web": {
                "client_id":     Config.GOOGLE_CLIENT_ID,
                "client_secret": Config.GOOGLE_CLIENT_SECRET,
                "auth_uri":      "https://accounts.google.com/o/oauth2/auth",
                "token_uri":     "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
        state=state
    )