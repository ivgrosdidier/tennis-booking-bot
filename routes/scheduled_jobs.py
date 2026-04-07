import os
from flask import Blueprint, request, render_template, redirect, url_for, flash, session
from extensions import db, auth_required, get_current_uid, get_logger

logger = get_logger(__name__)
scheduled_jobs_bp = Blueprint('scheduled_jobs', __name__, url_prefix='/api/scheduled-jobs')

@scheduled_jobs_bp.route('/morning-run', methods=['POST'])
def morning_check():
    """Cloud Scheduler endpoint - called at 7:50AM daily"""
    
    logger.info("Morning check endpoint called")
    
    # Verify OIDC token from Cloud Scheduler
    try:
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            logger.warning("Missing Bearer token")
            return jsonify({'error': 'Unauthorized'}), 403
        
        token = auth_header.replace('Bearer ', '')
        cloud_run_url = os.environ.get('CLOUD_RUN_SERVICE_URL', 'https://your-app.run.app')
        
        claims = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            audience=cloud_run_url
        )
        
        logger.info(f"✓ Request authenticated from {claims.get('email')}")
    
    except Exception as e:
        logger.warning(f"✗ Token verification failed: {e}")
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Run the booking process
    result = run_booking_process()
    
    return jsonify({
        'status': 'success',
        'result': result
    }), 200
 
 
@scheduled_jobs_bp.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'}), 200