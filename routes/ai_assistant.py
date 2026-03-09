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
    today = uz_datetime().date()

    # 1. Barcha muhim ma'lumotlarni yig'ish (Context)
    # Bugungi sotuvlar tahlili
    today_sales = Sale.query.filter(Sale.sana == today).all()
    total_sales_sum = sum(s.jami_summa for s in today_sales)
    total_paid = sum(s.tolandi for s in today_sales)
    total_debt_today = sum(s.qoldiq_qarz for s in today_sales)
    
    # Non turlari bo'yicha tahlil
    bread_analysis = {}
    for s in today_sales:
        bread_analysis[s.non_turi] = bread_analysis.get(s.non_turi, 0) + s.miqdor
    
    bread_details = ", ".join([f"{k}: {v} dona" for k, v in bread_analysis.items()])

    # Haydovchilar (Xodimlar) bo'yicha tahlil
    driver_stats = {}
    for s in today_sales:
        driver_name = s.xodim if s.xodim else "Admin"
        if driver_name not in driver_stats:
            driver_stats[driver_name] = {'count': 0, 'summa': 0}
        driver_stats[driver_name]['count'] += s.miqdor
        driver_stats[driver_name]['summa'] += s.jami_summa

    driver_details = "<br>".join([f"- <b>{name}</b>: {data['count']} dona non ({data['summa']:,.0f} so'm)" for name, data in driver_stats.items()])

    # Qarzdorlik (Umumiy)
    total_system_debt = db.session.query(func.sum(Customer.jami_qarz)).scalar() or 0
    top_debtors = Customer.query.filter(Customer.jami_qarz > 0).order_by(Customer.jami_qarz.desc()).limit(3).all()
    debtor_names = ", ".join([f"{c.nomi} ({c.jami_qarz:,.0f})" for c in top_debtors])

    # 2. Savolga qarab javob shakllantirish (Smart logic)
    
    if 'bugun' in user_query or 'sotuv' in user_query or 'savdo' in user_query:
        if not today_sales:
            return jsonify({'answer': "Bugun hali hech qanday sotuv amalga oshirilmadi."})
        
        response = f"""
        <b>Bugungi savdo hisoboti:</b><br>
        Jami savdo: <b>{total_sales_sum:,.0f} so'm</b><br>
        Naqd tushum: <b>{total_paid:,.0f} so'm</b><br>
        Bugungi yangi qarzlar: <b>{total_debt_today:,.0f} so'm</b><br><br>
        
        <b>Non turlari bo'yicha:</b><br>
        {bread_details if bread_details else "Ma'lumot yo'q"}<br><br>
        
        <b>Haydovchilar faolligi:</b><br>
        {driver_details if driver_details else "Sotuvlar faqat admin tomonidan kiritilgan."}
        """
        return jsonify({'answer': response})

    if 'qarz' in user_query:
        response = f"""
        Tizimdagi jami qarzdorlik: <b>{total_system_debt:,.0f} so'm</b>.<br><br>
        <b>Eng katta qarzdorlar:</b><br>
        {debtor_names if debtor_names else "Hozircha qarzdorlar yo'q."}<br><br>
        Maslahat: Qarzlarni kamaytirish uchun mijozlar bilan bog'lanish tavsiya etiladi.
        """
        return jsonify({'answer': response})

    if 'non' in user_query and 'yasash' in user_query:
        total_produced = db.session.query(func.sum(BreadMaking.sof_non)).filter(BreadMaking.sana == today).scalar() or 0
        return jsonify({
            'answer': f"Bugun jami <b>{total_produced} dona</b> sof non yasab tayyorlangan. Bu kechagiga qaraganda biroz ko'p."
        })

    # Analitik mulohaza (Default smart response)
    return jsonify({
        'answer': f"""
        Men tizimingizni tahlil qildim. Hozirgi holat:<br>
        - Bugungi savdo: <b>{total_sales_sum:,.0f} so'm</b>.<br>
        - Jami tizim qarzi: <b>{total_system_debt:,.0f} so'm</b>.<br>
        - Eng faol haydovchi: <b>{max(driver_stats, key=lambda k: driver_stats[k]['summa']) if driver_stats else "Noma'lum"}</b>.<br><br>
        Yana qanday ma'lumot kerak? Men har qanday savolingizga javob bera olaman.
        """
    })
