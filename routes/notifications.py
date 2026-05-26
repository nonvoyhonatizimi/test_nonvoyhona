from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, Bildirishnoma

notifications_bp = Blueprint('notifications', __name__, url_prefix='/notifications')

@notifications_bp.route('/')
@login_required
def list_notifications():
    if current_user.rol != 'admin':
        flash('Sizga ruxsat yo\'q!', 'error')
        return redirect(url_for('index'))
    
    notifications = Bildirishnoma.query.order_by(Bildirishnoma.created_at.desc()).all()
    return render_template('notifications.html', notifications=notifications)

@notifications_bp.route('/read/<int:id>')
@login_required
def mark_read(id):
    if current_user.rol != 'admin':
        return redirect(url_for('index'))
    
    notif = Bildirishnoma.query.get_or_404(id)
    notif.is_read = True
    db.session.commit()
    
    return redirect(url_for('notifications.list_notifications'))

@notifications_bp.route('/read_all')
@login_required
def mark_all_read():
    if current_user.rol != 'admin':
        return redirect(url_for('index'))
    
    Bildirishnoma.query.filter_by(is_read=False).update({'is_read': True})
    db.session.commit()
    
    return redirect(url_for('notifications.list_notifications'))
