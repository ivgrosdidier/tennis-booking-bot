import os
from flask import Blueprint, request, redirect, url_for, flash, session
from googleapiclient.discovery import build
from extensions import db, auth_required, get_current_uid, get_logger
from helpers.crypto import encrypt_string
from helpers.google_cal import build_google_flow
from config import Config, IS_DEV

logger = get_logger(__name__)
calendar_bp = Blueprint("calendar", __name__)

# Allow OAuth to work over HTTP for local development
if IS_DEV:
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'


@calendar_bp.route("/connect-google-calendar", methods=["POST"])
@auth_required
def connect_google_calendar():
    calendar_name = (request.form.get("calendar_name") or "").strip() or Config.DEFAULT_CALENDAR_NAME
    session["requested_calendar_name"] = calendar_name

    flow = build_google_flow()
    
    # Use the Config variable as the absolute Source of Truth.
    # This prevents the app from sending "revision" or "internal" URLs 
    # that haven't been whitelisted in the Google Cloud Console.
    flow.redirect_uri = Config.GOOGLE_REDIRECT_URI

    logger.debug(f"Generated redirect_uri for authorization: {flow.redirect_uri}")

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
    )
    session["google_oauth_state"]    = state
    session["google_oauth_verifier"] = flow.code_verifier

    logger.info(f"Google OAuth started for calendar='{calendar_name}'")
    return redirect(authorization_url)


@calendar_bp.route("/oauth2callback")
@auth_required
def oauth2callback():
    uid      = get_current_uid()
    state    = session.get("google_oauth_state")
    verifier = session.get("google_oauth_verifier")
    calendar_name = session.get("requested_calendar_name", Config.DEFAULT_CALENDAR_NAME)

    # Log state information for debugging
    url_state = request.args.get("state")
    logger.debug(f"State Check - Session: {state}, URL: {url_state}")

    if not state or state != url_state:
        reason = "missing from session" if not state else "mismatch with URL"
        logger.error(f"OAuth callback failed uid={uid}: state {reason}")
        if not state:
            logger.debug(f"Available session keys: {list(session.keys())}")
        flash("Google Calendar connection failed. Please try again.", "error")
        return redirect(url_for("dashboard.dashboard"))

    # Handle user cancelling on Google's consent screen
    if request.args.get("error"):
        db.collection("users").document(uid).set(
            {"google_calendar_connected": False}, merge=True
        )
        flash("Google Calendar connection was cancelled.", "error")
        return redirect(url_for("dashboard.dashboard"))

    try:
        flow = build_google_flow(state=state)
        flow.redirect_uri = Config.GOOGLE_REDIRECT_URI
        logger.debug(f"Generated redirect_uri for token exchange: {flow.redirect_uri}")
        
        # Cloud Run (behind a Load Balancer) often reports request.url as http.
        # Google requires the authorization_response to match the https redirect_uri exactly.
        authorization_response = request.url
        if not IS_DEV and authorization_response.startswith("http:"):
            authorization_response = authorization_response.replace("http:", "https:", 1)

        flow.fetch_token(authorization_response=authorization_response, code_verifier=verifier)
        creds = flow.credentials

        service   = build("calendar", "v3", credentials=creds)
        calendars = service.calendarList().list().execute().get("items", [])
        target    = calendar_name.strip().lower()

        matched = next(
            (c for c in calendars if (c.get("summary") or "").strip().lower() == target),
            None,
        )

        if not matched:
            # Calendar doesn't exist — create it
            new_cal = service.calendars().insert(body={
                "summary":     calendar_name,
                "description": "Managed by TennisBookingBot",
                "timeZone":    "America/Toronto",
            }).execute()
            service.calendarList().insert(body={"id": new_cal["id"]}).execute()
            calendar_id      = new_cal["id"]
            calendar_summary = new_cal["summary"]
            was_created      = True
            logger.info(f"Created calendar '{calendar_name}' uid={uid}")
        else:
            calendar_id      = matched["id"]
            calendar_summary = matched.get("summary")
            was_created      = False
            logger.info(f"Connected existing calendar '{calendar_summary}' uid={uid}")

        db.collection("users").document(uid).set({
            "google_calendar_connected":      True,
            "google_calendar_name":           calendar_summary,
            "google_calendar_id":             calendar_id,
            "google_refresh_token_encrypted": encrypt_string(creds.refresh_token) if creds.refresh_token else None,
        }, merge=True)

        msg = (f'No calendar named "{calendar_name}" was found. BookingBot created it for you!'
               if was_created else f'Google Calendar connected to "{calendar_summary}".')
        flash(msg, "success")

    except Exception as e:
        logger.error(f"OAuth callback failed uid={uid}: {e}")
        db.collection("users").document(uid).set({
            "google_calendar_connected": False,
            "google_calendar_id":        None,
        }, merge=True)
        flash("Google Calendar connection failed. Please try again.", "error")

    return redirect(url_for("dashboard.dashboard"))