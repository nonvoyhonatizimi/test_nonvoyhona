from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from models import db, Sale, Customer, BreadMaking, Dough, BreadTransfer, Employee, Cash, uz_datetime
from sqlalchemy import func
import os
from datetime import datetime, date

ai_assistant_bp = Blueprint('ai_assistant', __name__, url_prefix='/ai')

# AI logic will be expanded here
@ai_assistant_bp.route('/')
@login_required
def chat():
    return render_template('ai_assistant/chat.html')

@ai_assistant_bp.route('/ask', methods=['POST'])
@login_required
def ask_ai():
    user_query = request.json.get('query', '').lower()
    
    # Bugungi sanani tizim bo'yicha olish
    today = uz_datetime().date()

    # 1. Bugungi sotuvlar haqida
    if ('bugun' in user_query or 'hozir' in user_query) and 'sotuv' in user_query:
        total_sales = db.session.query(func.sum(Sale.jami_summa)).filter(Sale.sana == today).scalar() or 0
        sale_count = Sale.query.filter(Sale.sana == today).count()
        return jsonify({
            'answer': f"Bugungi jami savdo: <b>{total_sales:,.0f} so'm</b>. Jami <b>{sale_count} ta</b> sotuv amalga oshirilgan."
        })

    # 2. Qarzlar haqida
    if 'qarz' in user_query:
        if 'mijoz' in user_query or 'kim' in user_query:
            # Eng ko'p qarzi bor mijozlar
            top_debtors = Customer.query.filter(Customer.jami_qarz > 0).order_by(Customer.jami_qarz.desc()).limit(5).all()
            if not top_debtors:
                return jsonify({'answer': "Hozirda hech bir mijozning qarzi yo'q."})
            
            debt_list = "<br>".join([f"- {c.nomi}: {c.jami_qarz:,.0f} so'm" for c in top_debtors])
            return jsonify({
                'answer': f"Eng ko'p qarzi bor mijozlar:<br>{debt_list}"
            })
        else:
            total_debt = db.session.query(func.sum(Customer.jami_qarz)).scalar() or 0
            return jsonify({
                'answer': f"Tizimdagi jami mijozlar qarzi: <b>{total_debt:,.0f} so'm</b>."
            })

    # 3. Ishlab chiqarish haqida
    if 'non' in user_query and ('yasash' in user_query or 'chiqdi' in user_query):
        today = date.today()
        total_bread = db.session.query(func.sum(BreadMaking.sof_non)).filter(BreadMaking.sana == today).scalar() or 0
        if total_bread == 0:
            return jsonify({'answer': "Bugun hali non yasash bo'yicha ma'lumotlar kiritilmagan."})
        return jsonify({
            'answer': f"Bugun jami <b>{total_bread} dona</b> tayyor non yasab chiqildi."
        })

    # 4. Xodimlar haqida
    if 'xodim' in user_query or 'ishchi' in user_query:
        count = Employee.query.filter_by(status='faol').count()
        return jsonify({
            'answer': f"Hozirda tizimda <b>{count} ta</b> faol xodim ishlamoqda."
        })

    # Standart javob (Gemini ulanmagan holat uchun structured logic)
    return jsonify({
        'answer': "Kechirasiz, bu savol bo'yicha tahlil bera olmayman. Hozircha men bugungi sotuvlar, jami qarzlar va ishlab chiqarish haqida ma'lumot bera olaman."
    })
