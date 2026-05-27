from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from models import db, Sale, Customer, BreadMaking, uz_datetime
from sqlalchemy import func
import os
import io
import base64
from openai import OpenAI

ai_assistant_bp = Blueprint('ai_assistant', __name__, url_prefix='/ai')

def format_num(val):
    return f"{val:,.0f}".replace(',', ' ')

def generate_expert_report(data, query):
    """Mahalliy aqlli tahlilchi (Zero-API Expert System)"""
    q = query.lower()
    t = data['today']
    
    # 1. Umumiy hisobot yoki tahlil so'ralganda
    res = f"<b>Sanjar Patir - Batafsil Biznes Tahlili ({t.strftime('%d.%m.%Y')})</b><br><br>"
    
    # Sotuvlar
    if data['total_sales'] > 0:
        res += f"🚀 <b>Savdo Dinamikasi:</b> Bugungi kunda jami <b>{format_num(data['total_sales'])} so'm</b>lik savdo amalga oshirildi. "
        res += f"Kassa tushumi <b>{format_num(data['total_paid'])} so'm</b>ni tashkil etgan bo'lsa, <b>{format_num(data['new_debt'])} so'm</b> yangi qarzlar kiritildi.<br><br>"
        
        # Haydovchi tahlili
        if data['driver_stats']:
            best_driver = max(data['driver_stats'], key=lambda x: data['driver_stats'][x]['summa'])
            res += f"🌟 <b>Kunning eng faol xodimi:</b> Bugun <b>{best_driver}</b> eng yuqori natija ({format_num(data['driver_stats'][best_driver]['summa'])} so'm) ko'rsatdi. "
            res += f"U jami {data['driver_stats'][best_driver]['count']} dona non sotishga muvaffaq bo'ldi.<br><br>"
    else:
        res += "❕ Bugun hali sotuvlar kiritilmagan. Ishlab chiqarish va haydovchilar faoliyatini nazorat qilish tavsiya etiladi.<br><br>"

    # Non turlari
    if data['bread_analysis']:
        res += "🥖 <b>Non turlari bo'yicha sotuv:</b><br><ul>"
        for nt, d in data['bread_analysis'].items():
            res += f"<li>{nt}: {d['miqdor']} dona ({format_num(d['summa'])} so'm)</li>"
        res += "</ul><br>"

    # Qarzlar
    res += f"💳 <b>Qarzdorlik holati:</b> Tizimdagi jami qarzdorlik <b>{format_num(data['total_debt'])} so'm</b>ni tashkil etmoqda. "
    res += f"Moliya barqarorligini saqlash uchun quyidagi eng katta qarzdorlar bilan ishlash va to'lovlarni undirish maqsadga muvofiq:<br>"
    res += f"{data['debtor_info'].replace('\n', '<br>')}<br><br>"
    
    # Ishlab chiqarish
    res += "🏭 <b>Ishlab chiqarish:</b> Bugun jami " + (f"<b>{data['total_produced']} dona</b> tayyor non yasab chiqildi." if data['total_produced'] > 0 else "hali non yasash ma'lumotlari kiritilmagan.") + "<br><br>"
    
    res += "✅ <b>Xulosa va Maslahat:</b> Bugun savdo hajmini oshirish uchun yangi nuqtalar bilan ishlash va haydovchilar motivatsiyasiga e'tibor qaratish lozim. Shuningdek, qarzlarni o'z vaqtida undirish kassa aylanmasini yaxshilaydi."
    
    return res

@ai_assistant_bp.route('/')
@login_required
def chat():
    return render_template('ai_assistant/chat.html')

@ai_assistant_bp.route('/ask', methods=['POST'])
@login_required
def ask_ai():
    user_query = request.json.get('query', '').strip()
    today = uz_datetime().date()

    # Ma'lumotlarni yig'ish
    today_sales = Sale.query.filter(Sale.sana == today).all()
    total_sales = sum(s.jami_summa for s in today_sales)
    total_paid = sum(s.tolandi for s in today_sales)
    new_debt = sum(s.qoldiq_qarz for s in today_sales)
    
    bread_analysis = {}
    for s in today_sales:
        if s.non_turi not in bread_analysis: bread_analysis[s.non_turi] = {'miqdor': 0, 'summa': 0}
        bread_analysis[s.non_turi]['miqdor'] += s.miqdor
        bread_analysis[s.non_turi]['summa'] += s.jami_summa
    
    driver_stats = {}
    for s in today_sales:
        name = s.xodim if s.xodim else "Admin"
        if name not in driver_stats: driver_stats[name] = {'count': 0, 'summa': 0}
        driver_stats[name]['count'] += s.miqdor
        driver_stats[name]['summa'] += s.jami_summa

    total_debt = db.session.query(func.sum(Customer.jami_qarz)).scalar() or 0
    top_debtors = Customer.query.filter(Customer.jami_qarz > 0).order_by(Customer.jami_qarz.desc()).limit(10).all()
    debtor_info = "\n".join([f"- {c.nomi} ({format_num(c.jami_qarz)} so'm)" for c in top_debtors])
    total_produced = db.session.query(func.sum(BreadMaking.sof_non)).filter(BreadMaking.sana == today).scalar() or 0

    data_package = {
        'today': today, 'total_sales': total_sales, 'total_paid': total_paid, 
        'new_debt': new_debt, 'bread_analysis': bread_analysis, 
        'driver_stats': driver_stats, 'total_debt': total_debt, 
        'debtor_info': debtor_info, 'total_produced': total_produced
    }

    # Expert tizim orqali javobni tayyorlash (Hech qanday 403 xatosisiz)
    expert_answer = generate_expert_report(data_package, user_query)
    
    return jsonify({'answer': expert_answer})

@ai_assistant_bp.route('/ask-voice', methods=['POST'])
@login_required
def ask_voice():
    user_query = request.json.get('query', '').strip()
    if not user_query:
        return jsonify({'error': 'Savol kiritilmadi'}), 400

    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')

    # Agar kamida OpenAI kaliti bo'lsa ishlayveradi (GPT-4o-mini va TTS uchun)
    if not OPENAI_API_KEY:
        return jsonify({'error': 'API kalitlar kiritilmagan. Iltimos, server sozlamalarini tekshiring.'}), 500

    today = uz_datetime().date()

    customers = Customer.query.filter(Customer.status == 'faol', Customer.jami_qarz > 0).all()
    debtors_text = ", ".join([f"{c.nomi}: {format_num(c.jami_qarz)} so'm" for c in customers])
    
    today_sales = Sale.query.filter(Sale.sana == today).all()
    total_sales = sum(s.jami_summa for s in today_sales)
    sales_info = {}
    for s in today_sales:
        mijoz_nomi = s.customer.nomi if s.customer else "Noma'lum"
        if mijoz_nomi not in sales_info:
            sales_info[mijoz_nomi] = {}
        if s.non_turi not in sales_info[mijoz_nomi]:
            sales_info[mijoz_nomi][s.non_turi] = 0
        sales_info[mijoz_nomi][s.non_turi] += s.miqdor

    sales_text = ""
    for mijoz, nonlar in sales_info.items():
        sales_text += f"{mijoz} bugun oldi: "
        for nt, mq in nonlar.items():
            sales_text += f"{mq} ta {nt}, "
        sales_text += "; "

    prompt = f"""
    Sen Sanjar Patir nonvoyxonasining aqlli ovozli yordamchisisan.
    Foydalanuvchi quyidagi savolni berdi: "{user_query}"
    
    Ma'lumotlar bazasidagi joriy qisqacha ma'lumotlar:
    - Mijozlarning umumiy qarzlari: {debtors_text}
    - Bugungi sotuvlar tafsiloti (kim nima oldi): {sales_text}
    - Bugungi jami savdo: {format_num(total_sales)} so'm
    
    Qoidalar:
    1. Savolga aniq, londa va qisqa javob ber. Ovozli yordamchi bo'lganing uchun xuddi odamdek gaplash.
    2. Keraksiz so'zlarni, belgilarni (*, #) ishlatma.
    3. Agar ma'lumot topilmasa, "Kechirasiz, ma'lumot topilmadi" deb ayt.
    4. Raqamlarni chiroyli va tushunarli o'qilishi uchun imlo va uslubga e'tibor ber.
    """

    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # 1. Matnli javobni tayyorlash (GPT-4o-mini)
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt}
            ]
        )
        ai_text = completion.choices[0].message.content
        
        # 2. Matnni Ovozga aylantirish (TTS)
        tts_response = client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=ai_text
        )
        audio_io = io.BytesIO(tts_response.content)
        audio_io.seek(0)
        audio_base64 = base64.b64encode(audio_io.read()).decode('utf-8')
        
    except Exception as e:
        return jsonify({'error': f"OpenAI xatoligi: {str(e)}"}), 500

    return jsonify({
        'text': ai_text,
        'audio': audio_base64
    })
