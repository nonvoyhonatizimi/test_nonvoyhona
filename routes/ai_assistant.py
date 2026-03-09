from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from models import db, Sale, Customer, BreadMaking, uz_datetime
from sqlalchemy import func
import google.generativeai as genai

# Gemini API sozlamalari
API_KEY = "AIzaSyCDsTa_vFk3aEu4xCYO9oORO33K30v6Uyc"
genai.configure(api_key=API_KEY)
# Eng yangi va aqlli modelni tanlaymiz
model = genai.GenerativeModel('gemini-2.0-flash')

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

    # 1. Ma'lumotlarni yig'ish (Juda batafsil Business Context)
    today_sales = Sale.query.filter(Sale.sana == today).all()
    total_sales_sum = sum(s.jami_summa for s in today_sales)
    total_paid = sum(s.tolandi for s in today_sales)
    total_debt_today = sum(s.qoldiq_qarz for s in today_sales)
    
    # Non turlari bo'yicha batafsil
    bread_analysis = {}
    for s in today_sales:
        if s.non_turi not in bread_analysis:
            bread_analysis[s.non_turi] = {'miqdor': 0, 'summa': 0}
        bread_analysis[s.non_turi]['miqdor'] += s.miqdor
        bread_analysis[s.non_turi]['summa'] += s.jami_summa
    
    # Haydovchilar ish natijasi
    driver_stats = {}
    for s in today_sales:
        driver_name = s.xodim if s.xodim else "Admin"
        if driver_name not in driver_stats:
            driver_stats[driver_name] = {'count': 0, 'summa': 0, 'sales_count': 0}
        driver_stats[driver_name]['count'] += s.miqdor
        driver_stats[driver_name]['summa'] += s.jami_summa
        driver_stats[driver_name]['sales_count'] += 1

    # Qarzdorlik statistikasi
    total_system_debt = db.session.query(func.sum(Customer.jami_qarz)).scalar() or 0
    top_debtors = Customer.query.filter(Customer.jami_qarz > 0).order_by(Customer.jami_qarz.desc()).limit(15).all()
    debtor_info = "\n".join([f"- {c.nomi}: {c.jami_qarz:,.0f} so'm" for c in top_debtors])

    # Ishlab chiqarish
    total_produced = db.session.query(func.sum(BreadMaking.sof_non)).filter(BreadMaking.sana == today).scalar() or 0
    
    # Oxirgi 5 ta amal
    recent_actions = Sale.query.order_by(Sale.id.desc()).limit(5).all()
    recent_info = "\n".join([f"- {s.customer.nomi if s.customer else 'Noma`lum'}: {s.miqdor} dona {s.non_turi} ({s.jami_summa:,.0f} so'm)" for s in recent_actions])

    # Gemini uchun prompt tayyorlash
    system_prompt = f"""
    Siz 'Sanjar Patir' nonvoyhonasining eng aqlli va tajribali bosh tahlilchisisiz. 
    Ismingiz: Bakery AI. Sizning vazifangiz adminga biznesni boshqarishda yordam berish.
    
    MULOQOT QOIDALARI:
    1. O'zbek tilida juda tabiiy, ravon va xushmuomala gapiring.
    2. Javoblaringizni HTML formatida (<b>, <br>, <li> kabi) bering, shunda o'qish qulay bo'ladi.
    3. Savolga qarab, faqat raqam aytmasdan, ularni tahlil qiling (masalan: "Bugun savdo yaxshi emas, chunki..." yoki "Falonchi haydovchi juda faol").
    4. Ovozli o'qish uchun javobingizning birinchi qismini qisqa va mazmunli qiling.
    5. Agar sizdan umumiy holat so'ralsa, sotuvlar, qarzlar va haydovchilar haqida to'liq "svodka" bering.

    BIZNES MA'LUMOTLARI ({today.strftime('%d.%m.%Y')} holatiga):
    - JAMI SAVDO: {total_sales_sum:,.0f} so'm.
    - KASSA (NAQD): {total_paid:,.0f} so'm.
    - YANGI QARZLAR: {total_debt_today:,.0f} so'm.
    - ISHLAB CHIQARISH: Bugun {total_produced} dona non tayyorlandi.
    - NON TURLARI BO'YICHA: {bread_analysis}
    - HAYDOVCHILAR NATIJASI: {driver_stats}
    - UMUMIY TIZIM QARZI: {total_system_debt:,.0f} so'm.
    - ENG KATTA QARZDORLAR:
    {debtor_info}
    - OXIRGI SOTUVLAR:
    {recent_info}
    
    Foydalanuvchi savoli: {user_query}
    """

    try:
        response = model.generate_content(system_prompt)
        ai_response = response.text.replace('**', '<b>').replace('**', '</b>')
        return jsonify({'answer': ai_response})
    except Exception as e:
        print(f"AI ERROR: {e}")
        return jsonify({'answer': f"Kechirasiz, serverda muammo: {str(e)}. Modelni yangilash kutilmoqda."})
