from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Sale, Customer, BreadType
from sqlalchemy import func
from datetime import datetime

customer_portal_bp = Blueprint('customer_portal', __name__, url_prefix='/portal')

@customer_portal_bp.route('/')
@login_required
def dashboard():
    # Faqat mijozlar kirishi mumkin
    if not current_user.customer_id:
        flash('Bu sahifa faqat mijozlar uchun!', 'error')
        return redirect(url_for('index'))
    
    customer = Customer.query.get(current_user.customer_id)
    
    # Mijozning barcha sotuvlarini olish
    sales = Sale.query.filter_by(mijoz_id=customer.id).order_by(Sale.sana.desc(), Sale.created_at.desc()).all()
    
    # Qarz haqida umumiy ma'lumot
    total_spent = db.session.query(func.sum(Sale.jami_summa)).filter_by(mijoz_id=customer.id).scalar() or 0
    total_paid = db.session.query(func.sum(Sale.tolandi)).filter_by(mijoz_id=customer.id).scalar() or 0
    
    return render_template('portal/dashboard.html', 
                           customer=customer, 
                           sales=sales,
                           total_spent=total_spent,
                           total_paid=total_paid)

@customer_portal_bp.route('/sale/<int:id>')
@login_required
def sale_detail(id):
    if not current_user.customer_id:
        return redirect(url_for('index'))
    
    sale = Sale.query.filter_by(id=id, mijoz_id=current_user.customer_id).first_or_404()
    return render_template('portal/sale_detail.html', sale=sale)
