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
    if val is None:
        return "0"
    try:
        return f"{float(val):,.0f}".replace(',', ' ')
    except:
        return str(val)

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

import json
import requests
from datetime import datetime

def get_customer_debt_func(customer_name):
    customer = Customer.query.filter(Customer.nomi.ilike(f"%{customer_name}%")).first()
    if customer:
        return json.dumps({"mijoz": customer.nomi, "qarz": format_num(customer.jami_qarz) + " so'm", "telefon": customer.telefon})
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
        return json.dumps({"xabar": f"{customer.nomi} uchun {target_date} sanasida savdo topilmadi."})
        
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
    payload = {"chat_id": chat_id, "text": message}
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            return json.dumps({"muvaffaqiyat": "Xabar muvaffaqiyatli yuborildi!"})
        else:
            return json.dumps({"xato": f"Telegram xatosi: {response.text}"})
    except Exception as e:
        return json.dumps({"xato": f"Tarmoq xatosi: {str(e)}"})

def get_daily_summary_func():
    today = uz_datetime().date()
    today_sales = Sale.query.filter(Sale.sana == today).all()
    total_sales = sum(s.jami_summa for s in today_sales)
    total_paid = sum(s.tolandi for s in today_sales)
    new_debt = sum(s.qoldiq_qarz for s in today_sales)
    total_produced = db.session.query(func.sum(BreadMaking.sof_non)).filter(BreadMaking.sana == today).scalar() or 0
    
    return json.dumps({
        "sana": str(today),
        "jami_sotuv_summasi": format_num(total_sales) + " so'm",
        "kassaga_tushgan_naqd": format_num(total_paid) + " so'm",
        "yangi_qarzlar": format_num(new_debt) + " so'm",
        "ishlab_chiqarilgan_non": f"{total_produced} dona"
    })

def process_ai_query(user_query, is_voice=False):
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
    if not OPENAI_API_KEY:
        return "Kechirasiz, OpenAI API kaliti kiritilmagan.", None

    client = OpenAI(api_key=OPENAI_API_KEY)
    today = uz_datetime().date()
    
    prompt = f"""Sen "Sanjar Patir" nonvoyxonasining aqlli, chaqqon va xushmuomala bosh menejerisan (Sun'iy Intellekt).
Bugungi sana: {today}.

Qoidalar:
1. FAQAT sof o'zbek tilida, xuddi insondek tabiiy va qisqa javob ber.
2. Mijoz qarzini bilish uchun 'get_customer_debt' dan foydalan.
3. Mijoz nima olganini bilish uchun 'get_customer_sales' dan foydalan.
4. Mijozga pul to'lashini eslatish yoki xabar yuborish so'ralsa 'send_telegram_message' dan foydalan. (O'zingcha jo'natdim dema, albatta funksiyani chaqir).
5. Bugungi umumiy holat, jami savdo, jami qarz, qancha non yasaldiligi so'ralsa 'get_daily_summary' dan foydalan.
6. Hech qachon "Ma'lumot yo'q" deb o'zingcha xulosa qilma, kerakli funksiyani ishlatib bazani tekshir.
7. Ovozli o'qilishi uchun qulay bo'lishi kerak, keraksiz belgilar (*, #) ishlatma.
"""

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_customer_debt",
                "description": "Bazada mijozning qarzi bor-yo'qligini tekshiradi.",
                "parameters": {
                    "type": "object",
                    "properties": {"customer_name": {"type": "string"}},
                    "required": ["customer_name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_customer_sales",
                "description": "Mijoz ma'lum kunda nima olganini topadi.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "customer_name": {"type": "string"},
                        "date_str": {"type": "string"}
                    },
                    "required": ["customer_name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "send_telegram_message",
                "description": "Mijozning Telegram guruhiga xabar yuboradi.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "customer_name": {"type": "string"},
                        "message": {"type": "string"}
                    },
                    "required": ["customer_name", "message"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_daily_summary",
                "description": "Bugungi jami sotuv, kassa, qarz va ishlab chiqarish bo'yicha hisobotni beradi.",
                "parameters": {"type": "object", "properties": {}}
            }
        }
    ]

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": user_query}
    ]

    try:
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
                elif function_name == "get_daily_summary":
                    res = get_daily_summary_func()
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

        audio_base64 = None
        if is_voice:
            tts_response = client.audio.speech.create(
                model="tts-1-hd",
                voice="nova",
                input=ai_text
            )
            audio_io = io.BytesIO(tts_response.content)
            audio_io.seek(0)
            audio_base64 = base64.b64encode(audio_io.read()).decode('utf-8')
            
        return ai_text, audio_base64

    except Exception as e:
        print(f"AI Error: {str(e)}")
        return f"Kechirasiz, xatolik yuz berdi: {str(e)}", None

@ai_assistant_bp.route('/ask', methods=['POST'])
@login_required
def ask_ai():
    user_query = request.json.get('query', '').strip()
    ai_text, _ = process_ai_query(user_query, is_voice=False)
    return jsonify({'text': ai_text})

@ai_assistant_bp.route('/ask-voice', methods=['POST'])
@login_required
def ask_voice():
    user_query = request.json.get('query', '').strip()
    if not user_query:
        return jsonify({'error': 'Savol kiritilmadi'}), 400
        
    ai_text, audio_base64 = process_ai_query(user_query, is_voice=True)
    return jsonify({
        'text': ai_text,
        'audio': audio_base64
    })

@ai_assistant_bp.route('/ask-voice-audio', methods=['POST'])
@login_required
def ask_voice_audio():
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
    if not OPENAI_API_KEY:
        return jsonify({'error': 'API kalitlar kiritilmagan.'}), 500

    if 'audio' not in request.files:
        return jsonify({'error': 'Audio fayl topilmadi'}), 400

    audio_file = request.files['audio']
    
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=("voice.webm", audio_file.read()),
            prompt="Bu xabar toza O'zbek tilida."
        )
        user_query = transcript.text
    except Exception as e:
        return jsonify({'error': f"Ovozni tushunishda xatolik: {str(e)}"}), 500

    if not user_query.strip():
        return jsonify({'error': 'Ovozingizni tushunib bo\'lmadi.'}), 400

    ai_text, audio_base64 = process_ai_query(user_query, is_voice=True)
    
    return jsonify({
        'user_query': user_query,
        'text': ai_text,
        'audio': audio_base64
    })
