from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from models import db, BreadType

bread_types_bp = Blueprint('bread_types', __name__, url_prefix='/bread-types')

@bread_types_bp.route('/')
@login_required
def list_bread_types():
    """List all bread types"""
    bread_types = BreadType.query.order_by(BreadType.nomi).all()
    return render_template('bread_types/list.html', bread_types=bread_types)

@bread_types_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_bread_type():
    """Add new bread type"""
    if request.method == 'POST':
        nomi = request.form.get('nomi', '').strip()
        narx = request.form.get('narx', 0)
        
        if not nomi:
            flash('Non turining nomini kiriting!', 'error')
            return redirect(url_for('bread_types.add_bread_type'))
        
        # Check if already exists
        existing = BreadType.query.filter_by(nomi=nomi).first()
        if existing:
            flash(f'"{nomi}" allaqachon mavjud!', 'error')
            return redirect(url_for('bread_types.list_bread_types'))
        
        new_bread_type = BreadType(nomi=nomi, narx=narx)
        db.session.add(new_bread_type)
        db.session.commit()
        
        flash(f'"{nomi}" muvaffaqiyatli qo\'shildi!', 'success')
        return redirect(url_for('bread_types.list_bread_types'))
    
    return render_template('bread_types/add.html')

@bread_types_bp.route('/delete/<int:id>')
@login_required
def delete_bread_type(id):
    """Delete bread type"""
    bread_type = BreadType.query.get_or_404(id)
    nomi = bread_type.nomi
    
    db.session.delete(bread_type)
    db.session.commit()
    
    flash(f'"{nomi}" o\'chirildi!', 'success')
    return redirect(url_for('bread_types.list_bread_types'))
