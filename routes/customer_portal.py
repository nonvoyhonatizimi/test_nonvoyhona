from flask import Blueprint, render_template, redirect, url_for, flash, request
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
    
    from models import CustomerComment, Employee
    customer = Customer.query.get(current_user.customer_id)
    
    # Mijozning barcha sotuvlarini qat'iy tekshirish va olish
    sales = sorted(customer.sales, key=lambda s: s.id, reverse=True) if customer.sales else []
    
    # Izohlarni olish
    comments = CustomerComment.query.filter_by(customer_id=customer.id).order_by(CustomerComment.created_at.desc()).all()
    
    # Haydovchilar ro'yxatini olish (mijozga ko'rinishi uchun)
    drivers = Employee.query.filter(Employee.lavozim.ilike('%haydovchi%'), Employee.status == 'faol').all()
    
    return render_template('portal/dashboard.html', 
                           customer=customer, 
                           sales=sales,
                           comments=comments,
                           drivers=drivers)

@customer_portal_bp.route('/add_comment', methods=['POST'])
@login_required
def add_comment():
    if not current_user.customer_id:
        return redirect(url_for('index'))
    
    from models import CustomerComment
    matn = request.form.get('matn')
    if matn and matn.strip():
        comment = CustomerComment(
            customer_id=current_user.customer_id,
            is_from_admin=False,
            matn=matn.strip()
        )
        db.session.add(comment)
        db.session.commit()
        flash('Izohingiz adminga yuborildi', 'success')
        
    return redirect(url_for('customer_portal.dashboard'))

@customer_portal_bp.route('/delete_comment/<int:id>')
@login_required
def delete_comment(id):
    if not current_user.customer_id:
        return redirect(url_for('index'))
    
    from models import CustomerComment
    comment = CustomerComment.query.get_or_404(id)
    
    # Mijoz faqat o'zi yuborgan xabarni o'chirishi mumkin
    if comment.customer_id == current_user.customer_id and not comment.is_from_admin:
        db.session.delete(comment)
        db.session.commit()
        flash('Xabar o\'chirildi', 'success')
    else:
        flash("Bu xabarni o'chirishga ruxsatingiz yo'q", 'error')
        
    return redirect(url_for('customer_portal.dashboard'))

@customer_portal_bp.route('/sale/<int:id>')
@login_required
def sale_detail(id):
    if not current_user.customer_id:
        return redirect(url_for('index'))
    
    sale = Sale.query.filter_by(id=id, mijoz_id=current_user.customer_id).first_or_404()
    return render_template('portal/sale_detail.html', sale=sale)

@customer_portal_bp.route('/debug_sales/<int:cid>')
@login_required
def debug_sales(cid):
    if current_user.rol != 'admin':
        return "Must be admin"
    customer = Customer.query.get(cid)
    sales = Sale.query.filter_by(mijoz_id=cid).all()
    s_ids = [s.id for s in sales]
    
    return f"Customer {cid} debt {customer.jami_qarz if customer else 'None'} -> Sales ({len(s_ids)}): {s_ids}"
