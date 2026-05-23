from flask import Blueprint, jsonify
from flask_login import login_required
from models import QRSession
from datetime import datetime

attendance_bp = Blueprint('attendance', __name__, url_prefix='/api')

@attendance_bp.route('/qr/status/<string:session_id>')
@login_required
def qr_status(session_id):
    session = QRSession.query.filter_by(session_id=session_id).first()
    if not session:
        return jsonify({'active': False, 'message': 'Session not found'})
    if datetime.utcnow() > session.expires_at:
        session.is_active = False
        from models import db
        db.session.commit()
        return jsonify({'active': False, 'message': 'Session expired'})
    remaining = int((session.expires_at - datetime.utcnow()).total_seconds())
    return jsonify({'active': session.is_active, 'remaining_seconds': remaining})
