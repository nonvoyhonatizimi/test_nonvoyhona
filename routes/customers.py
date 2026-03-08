from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from models import db, Customer, User
from datetime import datetime

customers_bp = Blueprint('customers', __name__, url_prefix='/customers')

@customers_bp.route('/')
@login_required
def list_customers():
    customers = Customer.query.all()
    return render_template('customers/list.html', customers=customers)

@customers_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_customer():
    if request.method == 'POST':
        nomi = request.form.get('nomi')
        telefon = request.form.get('telefon')
        manzil = request.form.get('manzil')
        turi = request.form.get('turi')
        limit = request.form.get('limit', 0)
        telegram_chat_id = request.form.get('telegram_chat_id', '').strip()
        
        new_customer = Customer(
            nomi=nomi,
            telefon=telefon,
            manzil=manzil,
            turi=turi,
            telegram_chat_id=telegram_chat_id if telegram_chat_id else None,
            kredit_limit=limit
        )
        db.session.add(new_customer)
        db.session.commit()
        flash('Mijoz muvaffaqiyatli qo\'shildi', 'success')
        return redirect(url_for('customers.list_customers'))
    
    return render_template('customers/add.html')

@customers_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_customer(id):
    customer = Customer.query.get_or_404(id)
    user = User.query.filter_by(customer_id=customer.id).first()
    
    if request.method == 'POST':
        customer.nomi = request.form.get('nomi')
        customer.telefon = request.form.get('telefon')
        customer.manzil = request.form.get('manzil')
        customer.turi = request.form.get('turi')
        customer.kredit_limit = request.form.get('limit', 0)
        customer.status = request.form.get('status', 'faol')
        telegram_chat_id = request.form.get('telegram_chat_id', '').strip()
        customer.telegram_chat_id = telegram_chat_id if telegram_chat_id else None
        
        # User account management
        login_id = request.form.get('login', '').strip()
        password = request.form.get('parol', '').strip()
        
        if login_id:
            if not user:
                # Create new user for customer
                existing = User.query.filter_by(login=login_id).first()
                if existing:
                    flash('Bu login allaqachon band!', 'error')
                else:
                    new_user = User(
                        login=login_id,
                        parol=password if password else "123456",
                        rol='customer',
                        ism=customer.nomi,
                        customer_id=customer.id
                    )
                    db.session.add(new_user)
            else:
                # Update existing user
                existing = User.query.filter_by(login=login_id).first()
                if existing and existing.id != user.id:
                    flash('Bu login allaqachon band!', 'error')
                else:
                    user.login = login_id
                    if password:
                        user.parol = password
        
        db.session.commit()
        flash('Mijoz ma\'lumotlari yangilandi', 'success')
        return redirect(url_for('customers.list_customers'))
    
    return render_template('customers/edit.html', customer=customer, user=user)
