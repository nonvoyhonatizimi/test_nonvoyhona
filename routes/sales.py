from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Sale, Customer, Cash, BreadType, BreadTransfer, Employee, DriverPayment, DriverInventory, DayStatus, Eslatma, uz_datetime
from datetime import datetime, date
import requests
import json

sales_bp = Blueprint('sales', __name__, url_prefix='/sales')

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = "8443497785:AAG6UAJIzZv8HCSTKHqmYUe6dYRlIxu-Yn4"

# Customer to Telegram Group mapping
CUSTOMER_GROUPS = {
    "volidam": "-5191200114",
    "doston": "-5220067597",
    "sanjar patir": "-5119590423",
    "noilaxon": "-5136672687",
    "ziyo patir": "-5285503700",
    "turonboy": "-5210259696",
    "shirin patir": "-5189698467",
    "xojamboy": "-5176607925",
    "azizbek patir": "-5189297190",
    "akmal patir": "-5237628560",
    "shukurullo patir": "-5037602691",
    "abduqahor patir": "-5032698055",
    "milyon patir": "-5137038146",
    "ramshit patir": "-5226227796",
    "xusanboy patir": "-5282042883",
    "ishonch patir": "-5223718902",
    "soxib patir": "-4634207344",
    "sardor patir": "-5045869711",
    "lazzat patir": "-5191704673",
    "paxlavon patir": "-5125695734",
    "tanxo patir": "-5198380542",
    "alisher patir": "-5128082473",
    "asil patir": "-5051316785",
    "sarvar patir": "-5179819694",
    "javohir patir": "-5256511315",
    "kozim patir": "-5213481068",
    "klara opa": "-5052219586",
    "rashid patir": "-5036846652",
    "nodir patir": "-5283359473",
    "rokiya patir": "-5247807018",
    "xayotjon": "-5164251745",
    "shaxboz patir": "-5284778568",
    "osiyo patir": "-5156743302",
    "ozbegim": "-5273159369",
    "sadiya patir": "-5130791038",
    "ifor patir": "-5158654742",
    "diyor patir": "-5174351807",
    "lazzat patir2": "-5238995053",
    "mamura qirchin": "-5109056175",
    "dilafruz qirchin": "-5022506055",
    "saroy patir": "-5168265498",
    "abbosxon qirchin": "-5216949062",
    "nasiba qirchin": "-5235937864",
    "abdulatif": "-5189577253",
    "pungan baliq": "-5290608744",
    "tomchi dangara": "-5124985853",
    "benazir": "-5087901312"
}

def send_telegram_notification(customer_name, sale_data, customer_chat_id=None):
    """Send sale notification to customer's Telegram group"""
    # Find matching chat ID
    chat_id = None
    
    # Avval mijozning saqlangan chat_id sini tekshirish
    if customer_chat_id:
        chat_id = customer_chat_id
    else:
        # CUSTOMER_GROUPS dan qidirish
        customer_lower = customer_name.lower().strip()
        for key, value in CUSTOMER_GROUPS.items():
            if key.lower() in customer_lower or customer_lower in key.lower():
                chat_id = value
                break
    
    if not chat_id:
        print(f"Telegram group not found for: {customer_name}")
        return False
    
    # Format message
    message = f"""
YANGI SOTUV

Mijoz: {sale_data['mijoz']}
Sana: {sale_data['sana']} {sale_data['vaqt']}
Non turi: {sale_data['non_turi']}
Miqdor: {sale_data['miqdor']} dona
Narx: {sale_data['narx_dona']:,.0f} so'm
Jami: {sale_data['jami_summa']:,.0f} so'm
To'landi: {sale_data['tolandi']:,.0f} so'm
Qarz: {sale_data['qarz']:,.0f} so'm
Xodim: {sale_data['xodim']}
"""
    
    # Send to Telegram
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        response = requests.post(url, json=payload, timeout=5)
        
        if response.status_code == 200:
            print(f"[OK] Telegram sent to {customer_name}: {response.status_code}")
            return True
        else:
            print(f"[XATO] Telegram error for {customer_name}: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"[XATO] Telegram exception: {e}")
        return False

@sales_bp.route('/api/search_customers')
@login_required
def search_customers():
    q = request.args.get('q', '').lower().strip()
    if not q:
        return jsonify([])
    # Mijozlar ro'yxatini qidirish
    customers = Customer.query.filter(Customer.nomi.ilike(f'%{q}%')).limit(10).all()
    return jsonify([c.nomi for c in customers])

@sales_bp.route('/')
@login_required
def list_sales():
    customer_name = request.args.get('customer_name', '')
    filter_date = request.args.get('date', '')
    
    # Bugungi sanani olish
    today = uz_datetime().date()
    # Agar filtr berilmagan bo'lsa va qidiruv bo'lmasa, bugungi kunni tanlash
    if not filter_date and not customer_name:
        filter_date = today.strftime('%Y-%m-%d')
    
    query = Sale.query
    
    if customer_name:
        # Mijoz nomi bo'yicha qidirish
        query = query.join(Customer).filter(Customer.nomi.ilike(f'%{customer_name}%'))
    
    if filter_date:
        # Sana bo'yicha qidirish (stringni datega o'tkazamiz)
        try:
            date_obj = datetime.strptime(filter_date, '%Y-%m-%d').date()
            query = query.filter(Sale.sana == date_obj)
        except ValueError:
            pass
        
    sales = query.order_by(Sale.id.desc()).all()
    
    # Tarix uchun sanalarni guruhlab olish
    from sqlalchemy import func
    history_query = db.session.query(
        Sale.sana, 
        func.count(Sale.id).label('sotuv_soni'),
        func.sum(Sale.jami_summa).label('jami_summa')
    )
    
    if customer_name:
        history_query = history_query.join(Customer).filter(Customer.nomi.ilike(f'%{customer_name}%'))
    
    history_dates = history_query.group_by(Sale.sana).order_by(Sale.sana.desc()).limit(15).all()
    
    print(f"DEBUG: Jami sotuvlar soni: {len(sales)}, Tarix sanalari: {len(history_dates)}")  # Debug log
    
    # Tandirchi o'tkazishlarini ham olish (Faqat filter yo'q bo'lsa yoki kerak bo'lsa, lekin foydalanuvchi hozircha faqat sotuvlar haqida so'radi)
    tandir_transfers = BreadTransfer.query.filter_by(from_turi='tandirchi').order_by(BreadTransfer.created_at.desc()).limit(20).all()
    
    # Haydovchi o'tkazishlarini faqat admin uchun olish
    haydovchi_transfers = None
    if current_user.rol == 'admin':
        haydovchi_transfers = BreadTransfer.query.filter_by(from_turi='haydovchi').order_by(BreadTransfer.created_at.desc()).limit(20).all()
        
    # Haydovchi qoldiqlarini olish
    from models import DriverInventory, Employee
    from sqlalchemy import func
    
    inventory_grouped = db.session.query(
        DriverInventory.driver_id,
        DriverInventory.non_turi,
        func.sum(DriverInventory.miqdor).label('miqdor')
    ).group_by(
        DriverInventory.driver_id,
        DriverInventory.non_turi
    ).all()
    
    driver_inventory = []
    for item in inventory_grouped:
        driver = Employee.query.get(item.driver_id)
        driver_inventory.append({
            'non_turi': item.non_turi,
            'miqdor': item.miqdor,
            'driver': driver
        })
    
    # Jami hisoblar va Naqt sotuvlar
    naqt_sotuvlar = []
    jami_naqt = 0
    jami_qarz = 0
    
    for s in sales:
        if s.tolandi > 0:
            naqt_sotuvlar.append(s)
            jami_naqt += float(s.tolandi)
        jami_qarz += float(s.qoldiq_qarz)
    
    return render_template('sales/list.html', 
                         sales=sales, 
                         tandir_transfers=tandir_transfers, 
                         haydovchi_transfers=haydovchi_transfers, 
                         driver_inventory=driver_inventory,
                         naqt_sotuvlar=naqt_sotuvlar,
                         jami_naqt=jami_naqt,
                         jami_qarz=jami_qarz,
                         customer_name=customer_name,
                         filter_date=filter_date,
                         history_dates=history_dates,
                         today=today)

@sales_bp.route('/bulk-pay-debt', methods=['POST'])
@login_required
def bulk_pay_debt():
    from decimal import Decimal
    from models import Cash, DayStatus
    
    sale_ids_str = request.form.get('sale_ids', '')
    if not sale_ids_str:
        flash('Hech qanday qarz tanlanmagan!', 'error')
        return redirect(url_for('sales.list_sales'))
    
    sale_ids = [int(sid) for sid in sale_ids_str.split(',') if sid.isdigit()]
    if not sale_ids:
        flash('Noto\'g\'ri ma\'lumotlar!', 'error')
        return redirect(url_for('sales.list_sales'))
    
    total_paid = Decimal('0')
    count = 0
    
    # Hozirgi ochiq smenani aniqlash
    open_smena = DayStatus.query.filter_by(status='ochiq').order_by(DayStatus.id.desc()).first()
    current_smena = open_smena.smena if open_smena else 1
    today = datetime.now().date()
    
    for sid in sale_ids:
        sale = Sale.query.get(sid)
        if not sale or sale.qoldiq_qarz <= 0:
            continue
            
        payment = sale.qoldiq_qarz
        total_paid += payment
        count += 1
        
        # Update sale
        sale.tolandi += payment
        sale.qoldiq_qarz = 0
        
        # Update customer debt
        customer = Customer.query.get(sale.mijoz_id)
        if customer:
            customer.jami_qarz -= payment
            
        # Kassaga qo'shish (Xar doim qarz to'langanda)
        last_cash = Cash.query.order_by(Cash.id.desc()).first()
        current_balance = last_cash.balans if last_cash else Decimal('0')
        
        # Agar oldingi smenadagi qarz bo'lsa 'Qarz to'lovi', hozirgi smenada bo'lsa 'Sotuv' turi bilan yoziladi
        is_old_debt = (sale.smena < current_smena)
        cash_turi = 'Qarz to\'lovi' if is_old_debt else 'Sotuv'
        cash_izoh = f"Qarz to'lovi: {customer.nomi if customer else 'Nomalum'} ({'eski qarz' if is_old_debt else 'bugungi'})"
        
        new_cash = Cash(
            sana=today,
            smena=current_smena,
            kirim=payment,
            balans=current_balance + payment,
            izoh=cash_izoh,
            turi=cash_turi
        )
        db.session.add(new_cash)
            
        # Driver payment
        driver_payment = DriverPayment.query.filter_by(sale_id=sale.id).first()
        if driver_payment:
            driver_payment.status = 'tolandi'
            driver_payment.collected_at = uz_datetime()
            driver_payment.summa = payment
            driver_payment.smena = current_smena
            if current_user.employee_id:
                driver_payment.driver_id = current_user.employee_id
                
    db.session.commit()
    flash(f'{count} ta qarz uchun jami {float(total_paid):,.0f} so\'m to\'landi!', 'success')
    return redirect(url_for('sales.list_sales'))

@sales_bp.route('/pay-debt/<int:sale_id>', methods=['GET', 'POST'])
@login_required
def pay_debt(sale_id):
    from decimal import Decimal
    
    sale = Sale.query.get_or_404(sale_id)
    
    if request.method == 'POST':
        payment = Decimal(str(request.form.get('payment', 0)))
        
        if payment <= 0:
            flash('To\'lov miqdori 0 dan katta bo\'lishi kerak', 'error')
            return redirect(url_for('sales.pay_debt', sale_id=sale_id))
        
        if payment > sale.qoldiq_qarz:
            flash('To\'lov miqdori qarzdan katta bo\'lmasligi kerak', 'error')
            return redirect(url_for('sales.pay_debt', sale_id=sale_id))
        
        # Update sale
        sale.tolandi += payment
        sale.qoldiq_qarz -= payment
        
        # Update customer debt
        customer = Customer.query.get(sale.mijoz_id)
        if customer:
            customer.jami_qarz -= payment
        
        # Sana tekshirish - bugunmi yoki oldingi kunmi
        from datetime import date
        today = date.today()
        # Kassaga qo'shish (Xar doim qarz to'langanda)
        last_cash = Cash.query.order_by(Cash.id.desc()).first()
        current_balance = last_cash.balans if last_cash else Decimal('0')
        
        # Agar oldingi smenadagi qarz bo'lsa 'Qarz to'lovi', hozirgi smenada bo'lsa 'Sotuv' turi bilan yoziladi
        is_old_debt = (sale.smena < current_smena)
        cash_turi = 'Qarz to\'lovi' if is_old_debt else 'Sotuv'
        cash_izoh = f"Qarz to'lovi: {customer.nomi if customer else 'Nomalum'} ({'eski qarz' if is_old_debt else 'bugungi'})"
        
        new_cash = Cash(
            sana=datetime.now().date(),
            smena=current_smena,
            kirim=payment,
            balans=current_balance + payment,
            izoh=cash_izoh,
            turi=cash_turi
        )
        db.session.add(new_cash)
        
        # Haydovchi to'lovini saqlash
        driver_payment = DriverPayment.query.filter_by(sale_id=sale.id).first()
        
        # Hozirgi ochiq smenani aniqlash
        open_smena = DayStatus.query.filter_by(status='ochiq').order_by(DayStatus.id.desc()).first()
        current_smena = open_smena.smena if open_smena else 1
        
        print(f"[DEBUG pay_debt] Sale.smena={sale.smena}, current_smena={current_smena}")
        
        if driver_payment:
            # Mavjud to'lovni yangilash - MUHIM: smena ni ham yangilaymiz!
            driver_payment.status = 'tolandi'
            driver_payment.collected_at = uz_datetime()
            driver_payment.summa = payment
            driver_payment.smena = current_smena  # To'lov qilingan smena
            if current_user.employee_id:
                driver_payment.driver_id = current_user.employee_id
            print(f"[DEBUG pay_debt] Yangilandi: Sale.smena={sale.smena}, Payment.smena={current_smena}")
        
        db.session.commit()
        
        flash(f'{float(payment):,.0f} so\'m qarz to\'landi', 'success')
        return redirect(url_for('sales.list_sales'))
    
    return render_template('sales/pay_debt.html', sale=sale)

@sales_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_sale():
    if request.method == 'POST':
        from decimal import Decimal
        
        adashilgan = request.form.get('adashilgan')
        non_turi = request.form.get('non_turi')
        miqdor = int(request.form.get('miqdor', 0))
        
        if adashilgan == 'yes':
            mijoz_id = None
            narx = Decimal('0')
            jami = Decimal('0')
            tolandi = Decimal('0')
            qarz = Decimal('0')
            non_turi_saqlash = f"{non_turi} (Adashilgan)"
        else:
            mijoz_id = request.form.get('mijoz_id')
            narx = Decimal(str(request.form.get('narx', 0)))
            tolandi_str = request.form.get('tolandi', '0')
            tolandi = Decimal(tolandi_str) if tolandi_str and tolandi_str.strip() else Decimal('0')
            jami = miqdor * narx
            qarz = jami - tolandi
            non_turi_saqlash = non_turi
        
        # Inventory tekshirish - haydovchida yetarli non bormi? (original non turi bilan tekshiriladi)
        # Agar admin o'zi uchun sotayotgan bo'lsa (va xodim emas bo'lsa), tekshirmaydi
        check_xodim_id_str = request.form.get('xodim_id')
        check_xodim_id = None
        if check_xodim_id_str and check_xodim_id_str.isdigit():
            check_xodim_id = int(check_xodim_id_str)
        elif not check_xodim_id_str and current_user.employee_id:
            check_xodim_id = current_user.employee_id
            
        if check_xodim_id:
            from sqlalchemy import func
            total_miqdor = db.session.query(
                func.sum(DriverInventory.miqdor)
            ).filter(
                DriverInventory.driver_id == check_xodim_id,
                func.lower(func.trim(DriverInventory.non_turi)) == func.lower(func.trim(non_turi))
            ).scalar() or 0
            
            if total_miqdor < miqdor:
                flash(f'Tanlangan haydovchida yetarli {non_turi} yo\'q! (Mavjud: {total_miqdor} dona, Kerak: {miqdor} dona)', 'error')
                return redirect(url_for('sales.add_sale'))
        
        # Oxirgi ochiq smenani topish
        open_smena = DayStatus.query.filter_by(status='ochiq').order_by(DayStatus.id.desc()).first()
        if open_smena:
            current_smena = open_smena.smena
        else:
            current_smena = 1
        
        # Xodimni aniqlash
        form_xodim_id = request.form.get('xodim_id')
        if form_xodim_id and form_xodim_id.isdigit():
            xodim_id = int(form_xodim_id)
            selected_employee = Employee.query.get(xodim_id)
            xodim_nomi = selected_employee.ism if selected_employee else current_user.ism
        else:
            xodim_id = current_user.employee_id
            xodim_nomi = current_user.ism

        new_sale = Sale(
            sana=datetime.now().date(),
            smena=current_smena,
            mijoz_id=mijoz_id,
            non_turi=non_turi_saqlash,
            miqdor=miqdor,
            narx_dona=narx,
            jami_summa=jami,
            tolandi=tolandi,
            qoldiq_qarz=qarz,
            xodim=xodim_nomi,
            xodim_id=xodim_id
        )
        
        # Update customer debt and cash if not adashilgan
        customer = None
        if mijoz_id:
            customer = Customer.query.get(mijoz_id)
            if customer:
                customer.jami_qarz += qarz
                customer.oxirgi_sana = datetime.now().date()
        
            # Add to cash
            if tolandi > 0:
                last_cash = Cash.query.order_by(Cash.id.desc()).first()
                current_balance = last_cash.balans if last_cash else 0
                new_cash = Cash(
                    sana=datetime.now().date(),
                    smena=current_smena,
                    kirim=tolandi,
                    balans=current_balance + tolandi,
                    izoh=f"Sotuv: {customer.nomi if customer else 'Noma`lum'}",
                    turi='Sotuv'
                )
                db.session.add(new_cash)
            
        db.session.add(new_sale)
        db.session.commit()
        
        # Inventorydan non ayirish (original non_turi orqali)
        if xodim_id:
            remaining = miqdor
            inventories = DriverInventory.query.filter(
                DriverInventory.driver_id == xodim_id,
                func.lower(func.trim(DriverInventory.non_turi)) == func.lower(func.trim(non_turi))
            ).order_by(DriverInventory.sana.desc()).all()
            
            for inv in inventories:
                if remaining <= 0:
                    break
                if inv.miqdor >= remaining:
                    inv.miqdor -= remaining
                    inv.updated_at = uz_datetime()
                    remaining = 0
                else:
                    remaining -= inv.miqdor
                    inv.miqdor = 0
                    inv.updated_at = uz_datetime()
            
            if remaining > 0:
                flash(f'Xatolik: {remaining} dona {non_turi} ayirib bo\'lmadi!', 'error')
            else:
                db.session.commit()
        
        # Avtomatik Haydovchi to'lovi yaratish
        if qarz > 0 and xodim_id and mijoz_id:
            driver_payment = DriverPayment(
                sale_id=new_sale.id,
                driver_id=xodim_id,
                mijoz_id=mijoz_id,
                summa=qarz,
                smena=current_smena,
                status='kutilmoqda'
            )
            db.session.add(driver_payment)
            db.session.commit()
        
        # Send Telegram notification (faqat sotuv bo'lsa)
        if adashilgan != 'yes' and customer:
            sale_info = {
                "sotuv_id": new_sale.id,
                "sana": new_sale.sana.strftime('%d.%m.%Y'),
                "vaqt": uz_datetime().strftime('%H:%M:%S'),
                "mijoz": customer.nomi if customer else "Noma'lum",
                "non_turi": non_turi,
                "miqdor": miqdor,
                "narx_dona": Decimal(str(narx)),
                "jami_summa": Decimal(str(jami)),
                "tolandi": Decimal(str(tolandi)),
                "qarz": Decimal(str(qarz)),
                "xodim": current_user.ism
            }
            import threading
            telegram_thread = threading.Thread(
                target=send_telegram_notification,
                args=(customer.nomi if customer else "Noma'lum", sale_info, customer.telegram_chat_id if customer else None)
            )
            telegram_thread.daemon = True
            telegram_thread.start()
        
        if adashilgan == 'yes':
            flash(f"Brak (adashilgan) qayd etildi: {miqdor} ta {non_turi} qoldiqdan o'chirildi.", 'success')
        else:
            flash('Sotuv muvaffaqiyatli amalga oshirildi', 'success')
            
        return redirect(url_for('sales.list_sales'))
    
    customers = Customer.query.filter_by(status='faol').all()
    bread_types = BreadType.query.order_by(BreadType.nomi).all()
    haydovchilar = Employee.query.filter_by(lavozim='Haydovchi', status='faol').all()
    return render_template('sales/add.html', 
                         customers=customers, 
                         bread_types=bread_types, 
                         haydovchilar=haydovchilar)

@sales_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_sale(id):
    from decimal import Decimal
    from datetime import datetime
    sale = Sale.query.get_or_404(id)
    
    if request.method == 'POST':
        # Calculate difference in debt
        old_qarz = sale.qoldiq_qarz
        old_tolandi = sale.tolandi
        old_mijoz_id = sale.mijoz_id
        old_xodim_id = sale.xodim_id
        
        # Inventoryni yangilash
        new_xodim_id_str = request.form.get('xodim_id')
        new_xodim_id = int(new_xodim_id_str) if new_xodim_id_str and new_xodim_id_str.isdigit() else None
        new_mijoz_id_str = request.form.get('mijoz_id')
        new_mijoz_id = int(new_mijoz_id_str) if new_mijoz_id_str and new_mijoz_id_str.isdigit() else None
        new_miqdor = int(request.form.get('miqdor', 0))
        new_non_turi = request.form.get('non_turi')


        # Agar xodim yoki miqdor yoki non turi o'zgargan bo'lsa
        if old_xodim_id != new_xodim_id or sale.miqdor != new_miqdor or sale.non_turi != new_non_turi:
            # 1. Eski xodimga nonni qaytarish (agar bo'lsa)
            if old_xodim_id:
                old_inv = DriverInventory.query.filter_by(
                    driver_id=old_xodim_id,
                    non_turi=sale.non_turi,
                    sana=sale.sana
                ).first()
                if old_inv:
                    old_inv.miqdor += sale.miqdor
                else:
                    new_old_inv = DriverInventory(
                        driver_id=old_xodim_id,
                        non_turi=sale.non_turi,
                        miqdor=sale.miqdor,
                        sana=sale.sana
                    )
                    db.session.add(new_old_inv)

            # 2. Yangi xodimdan nonni ayirish (agar bo'lsa)
            if new_xodim_id:
                # Inventory yetarliligini tekshirish (ixtiyoriy, lekin yaxshi)
                remaining = new_miqdor
                inventories = DriverInventory.query.filter_by(
                    driver_id=new_xodim_id,
                    non_turi=new_non_turi
                ).order_by(DriverInventory.sana.desc()).all()
                
                for inv in inventories:
                    if remaining <= 0: break
                    if inv.miqdor >= remaining:
                        inv.miqdor -= remaining
                        remaining = 0
                    else:
                        remaining -= inv.miqdor
                        inv.miqdor = 0
                
                if remaining > 0:
                    flash(f"Ogohlantirish: Yangi xodimda {remaining} ta non yetishmadi, lekin sotuv saqlandi.", "warning")

        # Update sale fields
        sale.mijoz_id = new_mijoz_id
        sale.xodim_id = new_xodim_id
        if new_xodim_id:
            emp = Employee.query.get(new_xodim_id)
            if emp: sale.xodim = emp.ism
        
        sale.non_turi = new_non_turi
        sale.miqdor = new_miqdor
        narx = Decimal(str(request.form.get('narx', 0)))
        sale.narx_dona = narx
        sale.jami_summa = sale.miqdor * narx
        # Qarz qismi o'zgarmaydi (to'lov alohida)
        sale.qoldiq_qarz = sale.jami_summa - old_tolandi
        
        # SOATNI YANGILASH (admin uchun)
        if current_user.rol == 'admin':
            soat_str = request.form.get('soat')
            if soat_str:
                try:
                    # HH:MM formatida soatni olish
                    soat_parts = soat_str.split(':')
                    if len(soat_parts) == 2:
                        hour = int(soat_parts[0])
                        minute = int(soat_parts[1])
                        # created_at ni yangilash
                        old_created_at = sale.created_at
                        sale.created_at = old_created_at.replace(hour=hour, minute=minute)
                        print(f"[DEBUG] Soat yangilandi: {old_created_at} -> {sale.created_at}")
                except Exception as e:
                    print(f"[DEBUG] Soat yangilashda xato: {e}")
        
        # Update customer debt correctly
        if old_mijoz_id == new_mijoz_id and new_mijoz_id is not None:
            customer = Customer.query.get(new_mijoz_id)
            if customer:
                customer.jami_qarz = customer.jami_qarz - old_qarz + sale.qoldiq_qarz
                db.session.add(customer)
        else:
            if old_mijoz_id is not None:
                old_customer = Customer.query.get(old_mijoz_id)
                if old_customer:
                    old_customer.jami_qarz -= old_qarz
                    db.session.add(old_customer)
                    
            if new_mijoz_id is not None:
                new_customer = Customer.query.get(new_mijoz_id)
                if new_customer:
                    new_customer.jami_qarz += sale.qoldiq_qarz
                    db.session.add(new_customer)
        
        # Agar to'lov qilingan bo'lsa (tolandi o'zgargan), haydovchi to'lovini ham yangilash
        # (Template-da tahrirlab bo'lmaydi deyilibdi, lekin har ehtimolga qarshi qoldiramiz)
        new_tolandi = Decimal(str(request.form.get('tolandi', old_tolandi)))
        if new_tolandi > old_tolandi:
            # Qancha to'langanini hisoblash
            tolangan_qism = new_tolandi - old_tolandi
            driver_payment = DriverPayment.query.filter_by(sale_id=sale.id).first()
            if driver_payment and driver_payment.status == 'kutilmoqda':
                driver_payment.status = 'tolandi'
                driver_payment.collected_at = uz_datetime()
                # To'langan summani yangilash (faqat to'langan qismi)
                driver_payment.summa = tolangan_qism
        
        # Haydovchi to'lovi xodimini ham yangilash
        driver_payment = DriverPayment.query.filter_by(sale_id=sale.id).first()
        if driver_payment and new_xodim_id:
            driver_payment.driver_id = new_xodim_id
        
        db.session.commit()
        flash('Sotuv ma\'lumoti yangilandi', 'success')
        return redirect(url_for('sales.list_sales'))
    
    customers = Customer.query.filter_by(status='faol').all()
    bread_types = BreadType.query.order_by(BreadType.nomi).all()
    haydovchilar = Employee.query.filter_by(lavozim='Haydovchi', status='faol').all()
    return render_template('sales/edit.html', 
                         sale=sale, 
                         customers=customers, 
                         bread_types=bread_types, 
                         haydovchilar=haydovchilar)

@sales_bp.route('/delete/<int:id>')
@login_required
def delete_sale(id):
    from decimal import Decimal
    from models import DriverPayment
    sale = Sale.query.get_or_404(id)
    
    # Haydovchi to'lovini o'chirish
    driver_payments = DriverPayment.query.filter_by(sale_id=sale.id).all()
    for dp in driver_payments:
        db.session.delete(dp)
    
    # Update customer debt safely
    if sale.mijoz_id:
        customer = Customer.query.get(sale.mijoz_id)
        if customer:
            customer.jami_qarz -= sale.qoldiq_qarz
            db.session.add(customer)
    
    # Delete related cash entry if exists
    if sale.tolandi > 0 and sale.mijoz_id and customer:
        cash_entry = Cash.query.filter(
            Cash.izoh.like(f'%Sotuv: {customer.nomi}%'),
            Cash.kirim == sale.tolandi
        ).order_by(Cash.id.desc()).first()
        if cash_entry:
            db.session.delete(cash_entry)
            
    # Nonni haydovchi inventorysiga qaytarish
    if sale.xodim_id:
        inventory = DriverInventory.query.filter_by(
            driver_id=sale.xodim_id, 
            non_turi=sale.non_turi,
            sana=sale.sana
        ).first()
        
        if inventory:
            inventory.miqdor += sale.miqdor
            inventory.updated_at = uz_datetime()
        else:
            new_inv = DriverInventory(
                driver_id=sale.xodim_id,
                non_turi=sale.non_turi,
                miqdor=sale.miqdor,
                sana=sale.sana
            )
            db.session.add(new_inv)

    db.session.delete(sale)
    db.session.commit()
    flash('Sotuv ma\'lumoti o\'chirildi va mijoz qarzi yangilandi', 'success')
    return redirect(url_for('sales.list_sales'))

# ========== HAYDOVCHI → HAYDOVCHI NON O'TKAZISH ==========
@sales_bp.route('/transfer', methods=['GET', 'POST'])
@login_required
def add_transfer():
    """Haydovchi smena almashuvi - non o'tkazish (faqat admin)"""
    if current_user.rol != 'admin':
        flash('Bu funksiya faqat admin uchun!', 'error')
        return redirect(url_for('sales.list_sales'))
    
    if request.method == 'POST':
        from_xodim_id = request.form.get('from_xodim_id')
        to_xodim_id = request.form.get('to_xodim_id')
        
        # 4 ta non turini olish
        non_turlar = []
        for i in range(1, 5):
            non_turi = request.form.get(f'non_turi_{i}', '')
            non_miqdor = int(request.form.get(f'non_miqdor_{i}', 0) or 0)
            if non_turi and non_miqdor > 0:
                non_turlar.append((non_turi, non_miqdor))
        
        if not non_turlar:
            flash('Kamida bitta non turi va miqdor kiriting!', 'error')
            return redirect(url_for('sales.add_transfer'))
        
        # Oxirgi ochiq smenani topish
        open_smena = DayStatus.query.filter_by(status='ochiq').order_by(DayStatus.id.desc()).first()
        if open_smena:
            current_smena = open_smena.smena
        else:
            # Ochiq smena yo'q - yangi smena yaratish kerak
            current_smena = 1
            
        # Yangi o'tkazish yaratish
        new_transfer = BreadTransfer(
            sana=datetime.now().date(),
            smena=current_smena,
            from_xodim_id=from_xodim_id,
            to_xodim_id=to_xodim_id,
            from_turi='haydovchi'
        )
        
        # Non turlarini qo'shish
        for i, (turi, miqdor) in enumerate(non_turlar[:4], 1):
            setattr(new_transfer, f'non_turi_{i}', turi)
            setattr(new_transfer, f'non_miqdor_{i}', miqdor)
        
        db.session.add(new_transfer)
        db.session.commit()
        
        # Kimdan (from) inventorydan ayirish va kimga (to) qo'shish
        for i, (turi, miqdor) in enumerate(non_turlar[:4], 1):
            if turi and miqdor > 0:
                # Kimdan ayirish
                from_inventory = DriverInventory.query.filter_by(
                    driver_id=from_xodim_id,
                    non_turi=turi,
                    sana=datetime.now().date()
                ).first()
                
                if from_inventory:
                    from_inventory.miqdor -= miqdor
                    from_inventory.updated_at = uz_datetime()
                
                # Kimga qo'shish
                to_inventory = DriverInventory.query.filter_by(
                    driver_id=to_xodim_id,
                    non_turi=turi,
                    sana=datetime.now().date()
                ).first()
                
                if to_inventory:
                    to_inventory.miqdor += miqdor
                    to_inventory.updated_at = uz_datetime()
                else:
                    new_inventory = DriverInventory(
                        driver_id=to_xodim_id,
                        non_turi=turi,
                        miqdor=miqdor,
                        sana=datetime.now().date()
                    )
                    db.session.add(new_inventory)
        
        db.session.commit()
        flash('Non o\'tkazish muvaffaqiyatli saqlandi!', 'success')
        return redirect(url_for('sales.list_transfers'))
    
    # Faqat haydovchilarni olish
    haydovchilar = Employee.query.filter_by(lavozim='Haydovchi', status='faol').all()
    non_turlari = BreadType.query.order_by(BreadType.nomi).all()
    
    return render_template('sales/transfer_add.html', 
                         haydovchilar=haydovchilar, 
                         non_turlari=non_turlari)

@sales_bp.route('/transfers')
@login_required
def list_transfers():
    """Barcha o'tkazishlar ro'yxati (faqat admin)"""
    if current_user.rol != 'admin':
        flash('Bu funksiya faqat admin uchun!', 'error')
        return redirect(url_for('sales.list_sales'))
    
    transfers = BreadTransfer.query.filter_by(from_turi='haydovchi').order_by(BreadTransfer.created_at.desc()).all()
    return render_template('sales/transfer_list.html', transfers=transfers)

@sales_bp.route('/my-transfers')
@login_required
def my_transfers():
    """Haydovchining o'ziga o'tkazilgan nonlari"""
    # Faqat haydovchi o'ziga o'tkazilgan nonlarni ko'rsin
    if not current_user.employee_id:
        flash('Bu funksiya faqat haydovchilar uchun!', 'error')
        return redirect(url_for('sales.list_sales'))
    
    # Bugun o'ziga o'tkazilgan nonlar (tandirchidan yoki boshqa haydovchidan)
    transfers = BreadTransfer.query.filter(
        BreadTransfer.to_xodim_id == current_user.employee_id,
        BreadTransfer.sana == datetime.now().date()
    ).order_by(BreadTransfer.created_at.desc()).all()
    
    return render_template('sales/my_transfers.html', transfers=transfers)

@sales_bp.route('/transfer/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_transfer(id):
    """O'tkazishni tahrirlash (faqat admin)"""
    if current_user.rol != 'admin':
        flash('Bu funksiya faqat admin uchun!', 'error')
        return redirect(url_for('sales.list_sales'))
    
    transfer = BreadTransfer.query.get_or_404(id)
    
    if request.method == 'POST':
        transfer.from_xodim_id = request.form.get('from_xodim_id')
        transfer.to_xodim_id = request.form.get('to_xodim_id')
        
        # 4 ta non turini yangilash
        for i in range(1, 5):
            non_turi = request.form.get(f'non_turi_{i}', '')
            non_miqdor = int(request.form.get(f'non_miqdor_{i}', 0) or 0)
            setattr(transfer, f'non_turi_{i}', non_turi if non_turi else None)
            setattr(transfer, f'non_miqdor_{i}', non_miqdor)
        
        db.session.commit()
        flash('O\'tkazish ma\'lumoti yangilandi!', 'success')
        return redirect(url_for('sales.list_transfers'))
    
    haydovchilar = Employee.query.filter_by(lavozim='Haydovchi', status='faol').all()
    non_turlari = BreadType.query.order_by(BreadType.nomi).all()
    
    return render_template('sales/transfer_edit.html', 
                         transfer=transfer,
                         haydovchilar=haydovchilar, 
                         non_turlari=non_turlari)

@sales_bp.route('/transfer/delete/<int:id>')
@login_required
def delete_transfer(id):
    """O'tkazishni o'chirish (faqat admin)"""
    if current_user.rol != 'admin':
        flash('Bu funksiya faqat admin uchun!', 'error')
        return redirect(url_for('sales.list_sales'))
    
    transfer = BreadTransfer.query.get_or_404(id)
    # Inventoryni to'g'irlash
    from_id = transfer.from_xodim_id
    to_id = transfer.to_xodim_id
    
    for i in range(1, 5):
        turi = getattr(transfer, f'non_turi_{i}')
        miqdor = getattr(transfer, f'non_miqdor_{i}')
        if turi and miqdor > 0:
            # 1. Kimga berilgan bo'lsa o'shandan ayirish
            to_inv = DriverInventory.query.filter_by(driver_id=to_id, non_turi=turi, sana=transfer.sana).first()
            if to_inv:
                to_inv.miqdor -= miqdor
                if to_inv.miqdor < 0: to_inv.miqdor = 0
            
            # 2. Kimdan olingan bo'lsa o'shanga qaytarish
            from_inv = DriverInventory.query.filter_by(driver_id=from_id, non_turi=turi, sana=transfer.sana).first()
            if from_inv:
                from_inv.miqdor += miqdor
            else:
                new_from_inv = DriverInventory(
                    driver_id=from_id,
                    non_turi=turi,
                    miqdor=miqdor,
                    sana=transfer.sana
                )
                db.session.add(new_from_inv)

    db.session.delete(transfer)

    db.session.commit()
    flash('O\'tkazish o\'chirildi!', 'success')
    return redirect(url_for('sales.list_transfers'))

# ========== HAYDOVCHI TO'LOVLARI ==========
@sales_bp.route('/driver-payments')
@login_required
def driver_payments():
    """Haydovchi to'lovlari - to'langan qarzlar ro'yxati"""
    from datetime import date, datetime, timedelta
    from models import uz_datetime
    from sqlalchemy.orm import joinedload
    
    # Haydovchi filter
    driver_id = request.args.get('driver_id', '')
    
    # Barcha to'langan qarzlarni olish (status = 'tolandi')
    query = DriverPayment.query.options(
        joinedload(DriverPayment.driver),
        joinedload(DriverPayment.sale),
        joinedload(DriverPayment.mijoz)
    ).filter(
        DriverPayment.status == 'tolandi'
    )
    
    if driver_id:
        query = query.filter(DriverPayment.driver_id == driver_id)
    
    payments = query.order_by(DriverPayment.collected_at.desc()).all()
    
    # Faqat Sale.smena != DriverPayment.smena bo'lganlarni ajratish (Python da)
    # Ya'ni: turli smenada sotilgan va to'langan
    qarz_tolovlari = []
    for p in payments:
        if p.sale and p.sale.smena != p.smena:
            qarz_tolovlari.append(p)
    
    print(f"[DEBUG] Jami to'langan: {len(payments)}, Qarz to'lovlari: {len(qarz_tolovlari)}")
    
    # Barcha haydovchilar (filter uchun)
    drivers = Employee.query.filter_by(lavozim='Haydovchi', status='faol').all()
    
    # Jami hisoblar
    jami_tolangan = sum([p.summa for p in qarz_tolovlari])
    
    return render_template('sales/driver_payments.html',
                         payments=qarz_tolovlari,
                         drivers=drivers,
                         driver_id=driver_id,
                         status='tolandi',
                         jami_kutilmoqda=0,
                         jami_tolandan=jami_tolangan)

@sales_bp.route('/driver-payments/refresh', methods=['POST'])
@login_required
def refresh_driver_payments():
    """Qarz to'lovlari ro'yxatini TO'LIQ tozalash"""
    if current_user.rol != 'admin':
        flash('Bu funksiya faqat admin uchun!', 'error')
        return redirect(url_for('sales.driver_payments'))
    
    from models import DriverPayment
    
    # BARCHA to'langan qarzlarni o'chirish - hech qanday shart yo'q!
    deleted_count = DriverPayment.query.filter(DriverPayment.status == 'tolandi').delete()
    
    db.session.commit()
    
    print(f"[DEBUG refresh] {deleted_count} ta qarz to'lovi tozalandi")
    flash(f'{deleted_count} ta qarz to\'lovi tozalandi! Ro\'yxat bo\'sh.', 'success')
    return redirect(url_for('sales.driver_payments'))

@sales_bp.route('/driver-payment/collect/<int:id>')
@login_required
def collect_payment(id):
    """Haydovchi to'lovini 'to'landi' deb belgilash"""
    payment = DriverPayment.query.get_or_404(id)
    
    if payment.status == 'tolandi':
        flash('Bu to\'lov allaqachon to\'langan!', 'warning')
        return redirect(url_for('sales.driver_payments'))
    
    # Status ni yangilash
    payment.status = 'tolandi'
    payment.collected_at = datetime.now()
    
    # Mijoz qarzidan ayrish
    customer = Customer.query.get(payment.mijoz_id)
    if customer:
        customer.jami_qarz -= payment.summa
    
    # Kassaga qo'shish
    last_cash = Cash.query.order_by(Cash.id.desc()).first()
    current_balance = last_cash.balans if last_cash else 0
    new_cash = Cash(
        sana=datetime.now().date(),
        kirim=payment.summa,
        balans=current_balance + payment.summa,
        izoh=f"Haydovchi to'lovi: {payment.driver.ism if payment.driver else 'Noma`lum'} - {customer.nomi if customer else 'Noma`lum'}",
        turi='Haydovchi to\'lovi'
    )
    db.session.add(new_cash)
    db.session.commit()
    
    flash(f'To\'lov to\'landi: {payment.summa:,.0f} so\'m', 'success')
    return redirect(url_for('sales.driver_payments'))

# ========== ESLATMALAR ==========
@sales_bp.route('/notes')
@login_required
def list_notes():
    """Eslatmalar ro'yxati (Barcha xodimlar va admin uchun)"""
    notes = Eslatma.query.order_by(Eslatma.sana.desc()).all()
    return render_template('sales/notes.html', notes=notes)

@sales_bp.route('/notes/add', methods=['POST'])
@login_required
def add_note():
    """Yangi eslatma qo'shish"""
    matn = request.form.get('matn')
    if not matn or not matn.strip():
        flash('Eslatma matnini kiriting!', 'error')
        return redirect(url_for('sales.list_notes'))
    
    isim = current_user.ism if current_user.ism else "Noma'lum"
    rol = 'Admin' if current_user.rol == 'admin' else current_user.employee.lavozim if current_user.employee else 'Xodim'
    
    new_note = Eslatma(
        matn=matn.strip(),
        sana=uz_datetime(),
        muallif_ismi=isim,
        muallif_roli=rol,
        user_id=current_user.id
    )
    db.session.add(new_note)
    db.session.commit()
    
    flash('Eslatma muvaffaqiyatli qo\'shildi!', 'success')
    return redirect(url_for('sales.list_notes'))

@sales_bp.route('/notes/delete/<int:id>')
@login_required
def delete_note(id):
    """Eslatmani o'chirish"""
    note = Eslatma.query.get_or_404(id)
    
    if current_user.rol == 'admin' or note.user_id == current_user.id:
        db.session.delete(note)
        db.session.commit()
        flash('Eslatma o\'chirildi!', 'success')
    else:
        flash('Sizda bu eslatmani o\'chirish huquqi yo\'q!', 'error')
        
    return redirect(url_for('sales.list_notes'))
