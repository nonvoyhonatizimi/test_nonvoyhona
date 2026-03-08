from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from models import db, Expense, Cash, uz_datetime
from datetime import datetime, timedelta

finance_bp = Blueprint('finance', __name__, url_prefix='/finance')

@finance_bp.route('/expenses')
@login_required
def list_expenses():
    expenses = Expense.query.order_by(Expense.sana.desc()).all()
    return render_template('finance/expense_list.html', expenses=expenses)

@finance_bp.route('/expenses/add', methods=['GET', 'POST'])
@login_required
def add_expense():
    if request.method == 'POST':
        from decimal import Decimal
        turi = request.form.get('turi')
        miqdor = Decimal(str(request.form.get('miqdor', 0)))
        narx = Decimal(str(request.form.get('narx', 0)))
        izoh = request.form.get('izoh')
        
        jami = miqdor * narx
        
        new_expense = Expense(
            sana=datetime.now().date(),
            turi=turi,
            summa=jami,
            izoh=izoh
        )
        
        # Update cash
        last_cash = Cash.query.order_by(Cash.id.desc()).first()
        current_balance = last_cash.balans if last_cash else 0
        new_cash = Cash(
            sana=datetime.now().date(),
            chiqim=jami,
            balans=current_balance - jami,
            izoh=f"Xarajat: {turi}",
            turi='Xarajat'
        )
        
        db.session.add(new_expense)
        db.session.add(new_cash)
        db.session.commit()
        flash('Xarajat muvaffaqiyatli qo\'shildi', 'success')
        return redirect(url_for('finance.list_expenses'))
    
    return render_template('finance/expense_add.html')

@finance_bp.route('/cash')
@login_required
def list_cash():
    cash_entries = Cash.query.order_by(Cash.sana.desc(), Cash.id.desc()).all()
    current_balance = cash_entries[0].balans if cash_entries else 0
    return render_template('finance/cash_list.html', cash_entries=cash_entries, balance=current_balance, timedelta=timedelta)
