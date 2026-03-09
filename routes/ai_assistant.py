from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from models import db, Sale, Customer, BreadMaking, uz_datetime
from sqlalchemy import func
import google.generativeai as genai

# Gemini API sozlamalari
API_KEY = "AIzaSyCDsTa_vFk3aEu4xCYO9oORO33K30v6Uyc"
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

ai_assistant_bp = Blueprint('ai_assistant', __name__, url_prefix='/ai')

@ai_assistant_bp.route('/')
@login_required
def chat():
    return render_template('ai_assistant/chat.html')

@ai_assistant_bp.route('/ask', methods=['POST'])
@login_required
def ask_ai():
    user_query = request.json.get('query', '')
    today = uz_datetime().date()

    # 1. Ma'lumotlarni yig'ish (Business Context)
    today_sales = Sale.query.filter(Sale.sana == today).all()
    total_sales_sum = sum(s.jami_summa for s in today_sales)
    total_paid = sum(s.tolandi for s in today_sales)
    total_debt_today = sum(s.qoldiq_qarz for s in today_sales)
    
    bread_analysis = {}
    for s in today_sales:
        bread_analysis[s.non_turi] = bread_analysis.get(s.non_turi, 0) + s.miqdor
    
    driver_stats = {}
    for s in today_sales:
        driver_name = s.xodim if s.xodim else "Admin"
        if driver_name not in driver_stats:
            driver_stats[driver_name] = {'count': 0, 'summa': 0}
        driver_stats[driver_name]['count'] += s.miqdor
        driver_stats[driver_name]['summa'] += s.jami_summa

    total_system_debt = db.session.query(func.sum(Customer.jami_qarz)).scalar() or 0
    top_debtors = Customer.query.filter(Customer.jami_qarz > 0).order_by(Customer.jami_qarz.desc()).limit(10).all()
    debtor_info = "\n".join([f"- {c.nomi}: {c.jami_qarz:,.0f} so'm" for c in top_debtors])

    total_produced = db.session.query(func.sum(BreadMaking.sof_non)).filter(BreadMaking.sana == today).scalar() or 0

    # Gemini uchun prompt tayyorlash
    system_prompt = f"""
    Siz 'Sanjar Patir' nonvoyhonasining aqlli biznes tahlilchisi va yordamchisisiz. 
    Sizning ismingiz: Bakery AI. Siz xushmuomala va professional muloqot qilasiz. Javoblarni HTML formatida (masalan, <b> bold </b> ishlatib) bering.
    
    Hozirgi holat bo'yicha ma'lumotlar:
    - Sana: {today.strftime('%d.%m.%Y')}
    - Bugungi jami savdo: {total_sales_sum:,.0f} so'm
    - Bugun kassa tushumi (naqd): {total_paid:,.0f} so'm
    - Bugun yozilgan yangi qarzlar: {total_debt_today:,.0f} so'm
    - Bugun jami {total_produced} dona non tayyorlandi.
    - Non turlari bo'yicha sotuv: {bread_analysis}
    - Haydovchilar ish natijasi: {driver_stats}
    - Tizimdagi umumiy qarzlar summasi: {total_system_debt:,.0f} so'm
    - Eng katta qarzdorlar: {debtor_info}
    
    Savollarga shu ma'lumotlar asosida javob bering. Agar ma'lumot bo'lmasa, 'Ma'lumot topilmadi' deng. 
    Foydalanuvchi savoli: {user_query}
    """

    try:
        response = model.generate_content(system_prompt)
        ai_response = response.text.replace('**', '<b>').replace('**', '</b>') # Markdown boldni HTMLga o'tkazish
        return jsonify({'answer': ai_response})
    except Exception as e:
        print(f"AI ERROR: {e}")
        return jsonify({'answer': "Kechirasiz, sun'iy intellekt bilan bog'lanishda xato yuz berdi. Iltimos, keyinroq kiring."})
