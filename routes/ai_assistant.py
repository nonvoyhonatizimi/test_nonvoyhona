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

import json
import requests
from datetime import datetime

def get_customer_debt_func(customer_name):
    customer = Customer.query.filter(Customer.nomi.ilike(f"%{customer_name}%")).first()
    if customer:
        return json.dumps({"mijoz": customer.nomi, "qarz": format_num(customer.jami_qarz) + " so'm"})
    return json.dumps({"xato": f"'{customer_name}' ismli mijoz topilmadi."})

def get_customer_sales_func(customer_name, date_str=None):
    if not date_str:
        target_date = uz_datetime().date()
    else:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except:
            target_date = uz_datetime().date()
            
    customer = Customer.query.filter(Customer.nomi.ilike(f"%{customer_name}%")).first()
    if not customer:
        return json.dumps({"xato": f"'{customer_name}' ismli mijoz topilmadi."})
        
    sales = Sale.query.filter(Sale.mijoz_id == customer.id, Sale.sana == target_date).all()
    if not sales:
        return json.dumps({"xabar": f"{customer.nomi} uchun {target_date} sanasida hech qanday savdo topilmadi."})
        
    total_sales = sum(s.jami_summa for s in sales)
    details = {}
    for s in sales:
        details[s.non_turi] = details.get(s.non_turi, 0) + s.miqdor
        
    return json.dumps({
        "mijoz": customer.nomi,
        "sana": str(target_date),
        "olgan_nonlari": details,
        "jami_summa": format_num(total_sales) + " so'm"
    })

def send_telegram_message_func(customer_name, message):
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    if not TELEGRAM_BOT_TOKEN:
        return json.dumps({"xato": "Telegram bot tokeni sozlanmagan."})
        
    customer = Customer.query.filter(Customer.nomi.ilike(f"%{customer_name}%")).first()
    if not customer:
        return json.dumps({"xato": f"'{customer_name}' ismli mijoz topilmadi."})
        
    chat_id = customer.telegram_chat_id
    if not chat_id:
        return json.dumps({"xato": f"'{customer.nomi}' uchun Telegram chat ID kiritilmagan. Uning raqami {customer.telefon}. O'zingiz aytib qo'ying."})
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            return json.dumps({"muvaffaqiyat": "Xabar muvaffaqiyatli yuborildi!"})
        else:
            return json.dumps({"xato": f"Telegram xatosi: {response.text}"})
    except Exception as e:
        return json.dumps({"xato": f"Tarmoq xatosi: {str(e)}"})

@ai_assistant_bp.route('/ask-voice-audio', methods=['POST'])
@login_required
def ask_voice_audio():
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
    if not OPENAI_API_KEY:
        return jsonify({'error': 'API kalitlar kiritilmagan. Iltimos, server sozlamalarini tekshiring.'}), 500

    if 'audio' not in request.files:
        return jsonify({'error': 'Audio fayl topilmadi'}), 400

    audio_file = request.files['audio']
    
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        # 1. Whisper STT
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=("voice.webm", audio_file.read())
        )
        user_query = transcript.text
    except Exception as e:
        return jsonify({'error': f"Ovozni tushunishda xatolik (Whisper): {str(e)}"}), 500

    if not user_query.strip():
        return jsonify({'error': 'Ovozingizni tushunib bo\'lmadi. Qaytadan gapiring.'}), 400

    # Boshlang'ich qisqacha ma'lumotlar (Kontekst)
    today = uz_datetime().date()
    today_sales = Sale.query.filter(Sale.sana == today).all()
    total_sales = sum(s.jami_summa for s in today_sales)

    prompt = f"""
    Sen "Sanjar Patir" nonvoyxonasining aqlli, chaqqon va xushmuomala yordamchi menejerisan. 
    Bugungi kun: {today}
    Bugungi jami savdo: {format_num(total_sales)} so'm.
    Foydalanuvchi quyidagi gapni gapirdi: "{user_query}"
    
    Qoidalar va tushunchalar:
    1. "Kassa qilish so'rovini jo'natish" yoki "qarzini eslatish" degani — mijozning telegramiga pul to'lashi kerakligi haqida xabar jo'natish degani. Buning uchun DOIM 'send_telegram_message' funksiyasini chaqir. Hech qachon o'zingcha "jo'natdim" deb aldamagin, albatta funksiyani ishlat!
    2. Agar kimgadir telegramdan xabar yoz desa ham, shu funksiyani chaqir.
    3. Agar kimningdir qarzini yoki bugungi savdosini so'rasa, 'get_customer_debt' yoki 'get_customer_sales' ni chaqir.
    4. JAVOBING JUDA TABIIY, INSONIY VA QISQA BO'LSIN. Xuddi tirik odamdek, ortiqcha rasmiyatchiliksiz, samimiy javob qaytar. 
    5. Agar funksiya xato qaytarsa (masalan telegram id yo'q desa), buni foydalanuvchiga tabiiy tilda "Uning telegrami ulanmagan ekan, nomeriga telefon qilaqolaylikmi?" kabi tushuntir.
    6. Raqamlarni so'zda chiroyli ayt. Keraksiz yulduzchalar (*), panjaralar (#) ishlatma.
    """

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_customer_debt",
                "description": "Bazada mijozning qarzi bor-yo'qligini tekshiradi.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "customer_name": {"type": "string", "description": "Mijoz ismi"}
                    },
                    "required": ["customer_name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_customer_sales",
                "description": "Mijoz ma'lum kunda (masalan bugun) nima olganini topadi.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "customer_name": {"type": "string", "description": "Mijoz ismi"},
                        "date_str": {"type": "string", "description": "Sana YYYY-MM-DD. Bo'sh bo'lsa bugun."}
                    },
                    "required": ["customer_name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "send_telegram_message",
                "description": "Mijozning Telegram guruhiga xabar yuboradi. Kassa qilish (pul so'rash) haqida so'ralganda ham shundan foydalaniladi.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "customer_name": {"type": "string", "description": "Mijoz ismi"},
                        "message": {"type": "string", "description": "Xabar matni"}
                    },
                    "required": ["customer_name", "message"]
                }
            }
        }
    ]

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": user_query}
    ]

    try:
        # GPT-4o-mini with tools
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
        
        response_message = completion.choices[0].message
        tool_calls = response_message.tool_calls
        
        if tool_calls:
            messages.append(response_message)
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                if function_name == "get_customer_debt":
                    res = get_customer_debt_func(function_args.get("customer_name"))
                elif function_name == "get_customer_sales":
                    res = get_customer_sales_func(function_args.get("customer_name"), function_args.get("date_str"))
                elif function_name == "send_telegram_message":
                    res = send_telegram_message_func(function_args.get("customer_name"), function_args.get("message"))
                else:
                    res = json.dumps({"error": "Unknown function"})
                    
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": res,
                })
                
            second_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages
            )
            ai_text = second_response.choices[0].message.content
        else:
            ai_text = response_message.content
            
        # TTS - Nova ovozi
        tts_response = client.audio.speech.create(
            model="tts-1-hd",
            voice="nova",
            input=ai_text
        )
        audio_io = io.BytesIO(tts_response.content)
        audio_io.seek(0)
        audio_base64 = base64.b64encode(audio_io.read()).decode('utf-8')
        
    except Exception as e:
        return jsonify({'error': f"AI xatoligi: {str(e)}"}), 500

    return jsonify({
        'user_query': user_query,
        'text': ai_text,
        'audio': audio_base64
    })
