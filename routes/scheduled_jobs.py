import os
from flask import Blueprint, request, jsonify
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from booking.orchestrator import run_booking_process
from extensions import get_logger

logger = get_logger(__name__)
scheduled_jobs_bp = Blueprint('scheduled_jobs', __name__, url_prefix='/api/scheduled-jobs')


@scheduled_jobs_bp.route('/morning-run', methods=['POST'])
def morning_check():
    """
    Cloud Scheduler endpoint — triggered at 7:50 AM daily.

    Cloud Scheduler attaches an OIDC token to the request. We verify it
    to ensure the request comes from our own scheduler, not an external caller.

    The CLOUD_RUN_SERVICE_URL env var must match the URL you configured
    in Cloud Scheduler as the audience for the OIDC token.
    """
    logger.info("Morning booking run triggered")

    # Verify OIDC token from Cloud Scheduler
    try:
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            logger.warning("Missing or malformed Bearer token")
            return jsonify({'error': 'Unauthorized'}), 403

        token = auth_header.replace('Bearer ', '')
        audience = os.environ.get('CLOUD_RUN_SERVICE_URL', '')

        claims = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            audience=audience
        )
        logger.info(f"Request authenticated from {claims.get('email')}")

    except Exception as e:
        logger.warning(f"Token verification failed: {e}")
        return jsonify({'error': 'Unauthorized'}), 403

    # Run the full booking pipeline
    result = run_booking_process()

    return jsonify({'status': 'success', 'result': result}), 200


@scheduled_jobs_bp.route('/health', methods=['GET'])
def health():
    """Health check — used by Cloud Run / load balancer."""
    return jsonify({'status': 'healthy'}), 200
