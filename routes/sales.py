from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Sale, Customer, Cash, BreadType, BreadTransfer, Employee, DriverPayment, DriverInventory, DayStatus, uz_datetime
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

@sales_bp.route('/')
@login_required
def list_sales():
    sales = Sale.query.order_by(Sale.sana.desc()).all()
    # Tandirchi o'tkazishlarini ham olish
    tandir_transfers = BreadTransfer.query.filter_by(from_turi='tandirchi').order_by(BreadTransfer.created_at.desc()).all()
    # Haydovchi o'tkazishlarini faqat admin uchun olish
    haydovchi_transfers = None
    if current_user.rol == 'admin':
        haydovchi_transfers = BreadTransfer.query.filter_by(from_turi='haydovchi').order_by(BreadTransfer.created_at.desc()).all()
    return render_template('sales/list.html', sales=sales, tandir_transfers=tandir_transfers, haydovchi_transfers=haydovchi_transfers)

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
        is_today = (sale.sana == today)
        
        # Agar bugun sotuv qilingan bo'lsa, kassaga qo'shish
        if is_today:
            last_cash = Cash.query.order_by(Cash.id.desc()).first()
            current_balance = last_cash.balans if last_cash else Decimal('0')
            new_cash = Cash(
                sana=datetime.now().date(),
                kirim=payment,
                balans=current_balance + payment,
                izoh=f"Qarz to'lovi: {customer.nomi if customer else 'Nomalum'} (bugun)",
                turi='Qarz to\'lovi'
            )
            db.session.add(new_cash)
        
        # Haydovchi to'lovini saqlash (faqat smena yopilgandan keyin olingan to'lovlar uchun)
        # Avvalgi to'lovni tekshirish
        driver_payment = DriverPayment.query.filter_by(sale_id=sale.id).first()
        
        # Oxirgi smenani aniqlash
        from datetime import date
        today = date.today()
        last_closed = DayStatus.query.filter_by(status='yopiq').order_by(DayStatus.yopilgan_vaqt.desc()).first()
        current_smena = last_closed.smena + 1 if last_closed else 1
        
        # Sale qaysi smenaga tegishli?
        sale_smena = sale.smena if sale.smena else 1
        
        # Faqat agar to'lov BOSHQA SMENADA olingan bo'lsa saqlash
        # (Shu smena da non berildi + Shunga smena da pul olindi = Bugungi sotuvlarda)
        # (Smena A da non berildi + Smena B da pul olindi = Qarz to'lovlari)
        if driver_payment and current_smena > sale_smena:
            # Boshqa smenada olingan to'lov - Qarz to'lovlari ga
            new_driver_payment = DriverPayment(
                sale_id=sale.id,
                driver_id=driver_payment.driver_id,
                mijoz_id=sale.mijoz_id,
                summa=payment,
                smena=current_smena,
                status='tolandi',
                collected_at=uz_datetime()
            )
            db.session.add(new_driver_payment)
        elif driver_payment and current_smena == sale_smena:
            # Shu smenada olingan to'lov - faqat status ni yangilash
            driver_payment.status = 'tolandi'
            driver_payment.collected_at = uz_datetime()
            driver_payment.summa = payment
        
        db.session.commit()
        
        flash(f'{float(payment):,.0f} so\'m qarz to\'landi', 'success')
        return redirect(url_for('sales.list_sales'))
    
    return render_template('sales/pay_debt.html', sale=sale)

@sales_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_sale():
    if request.method == 'POST':
        from decimal import Decimal
        
        mijoz_id = request.form.get('mijoz_id')
        non_turi = request.form.get('non_turi')
        miqdor = int(request.form.get('miqdor', 0))
        narx = Decimal(str(request.form.get('narx', 0)))
        tolandi_str = request.form.get('tolandi', '0')
        tolandi = Decimal(tolandi_str) if tolandi_str and tolandi_str.strip() else Decimal('0')
        
        jami = miqdor * narx
        qarz = jami - tolandi
        
        # Inventory tekshirish - haydovchida yetarli non bormi?
        if current_user.employee_id:
            inventory = DriverInventory.query.filter_by(
                driver_id=current_user.employee_id,
                non_turi=non_turi,
                sana=datetime.now().date()
            ).first()
            
            if not inventory or inventory.miqdor < miqdor:
                flash(f'Sizda yetarli {non_turi} yo\'q! Avval non oling.', 'error')
                return redirect(url_for('sales.add_sale'))
        
        # Oxirgi yopilgan smenani topish va yangi smena raqamini aniqlash
        today = date.today()
        last_closed = DayStatus.query.filter_by(sana=today, status='yopiq').order_by(DayStatus.smena.desc()).first()
        current_smena = last_closed.smena + 1 if last_closed else 1
        
        new_sale = Sale(
            sana=datetime.now().date(),
            smena=current_smena,
            mijoz_id=mijoz_id,
            non_turi=non_turi,
            miqdor=miqdor,
            narx_dona=narx,
            jami_summa=jami,
            tolandi=tolandi,
            qoldiq_qarz=qarz,
            xodim=current_user.ism,
            xodim_id=current_user.employee_id
        )
        
        # Update customer debt
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
                kirim=tolandi,
                balans=current_balance + tolandi,
                izoh=f"Sotuv: {customer.nomi if customer else 'Noma`lum'}",
                turi='Sotuv'
            )
            db.session.add(new_cash)
            
        db.session.add(new_sale)
        db.session.commit()
        
        # Inventorydan non ayirish
        if current_user.employee_id:
            inventory = DriverInventory.query.filter_by(
                driver_id=current_user.employee_id,
                non_turi=non_turi,
                sana=datetime.now().date()
            ).first()
            
            if inventory:
                inventory.miqdor -= miqdor
                inventory.updated_at = uz_datetime()
                db.session.commit()
        
        # Avtomatik Haydovchi to'lovi yaratish (agar qarz bo'lsa va haydovchi bo'lsa)
        if qarz > 0 and current_user.employee_id:
            driver_payment = DriverPayment(
                sale_id=new_sale.id,
                driver_id=current_user.employee_id,
                mijoz_id=mijoz_id,
                summa=qarz,
                smena=current_smena,
                status='kutilmoqda'
            )
            db.session.add(driver_payment)
            db.session.commit()
        
        # Send Telegram notification
        sale_info = {
            "sotuv_id": new_sale.id,
            "sana": new_sale.sana.strftime('%d.%m.%Y'),
            "vaqt": uz_datetime().strftime('%H:%M:%S'),
            "mijoz": customer.nomi if customer else "Noma'lum",
            "non_turi": non_turi,
            "miqdor": miqdor,
            "narx_dona": float(narx),
            "jami_summa": float(jami),
            "tolandi": float(tolandi),
            "qarz": float(qarz),
            "xodim": current_user.ism
        }
        # Telegram xabarini alohida thread da yuborish (tezroq bo'lishi uchun)
        import threading
        telegram_thread = threading.Thread(
            target=send_telegram_notification,
            args=(customer.nomi if customer else "Noma'lum", sale_info, customer.telegram_chat_id if customer else None)
        )
        telegram_thread.daemon = True
        telegram_thread.start()
        
        flash('Sotuv muvaffaqiyatli amalga oshirildi')
        return redirect(url_for('sales.list_sales'))
    
    customers = Customer.query.filter_by(status='faol').all()
    bread_types = BreadType.query.order_by(BreadType.nomi).all()
    return render_template('sales/add.html', customers=customers, bread_types=bread_types)

@sales_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_sale(id):
    from decimal import Decimal
    sale = Sale.query.get_or_404(id)
    
    if request.method == 'POST':
        # Calculate difference in debt
        old_qarz = sale.qoldiq_qarz
        old_tolandi = sale.tolandi
        
        sale.mijoz_id = request.form.get('mijoz_id')
        sale.non_turi = request.form.get('non_turi')
        sale.miqdor = int(request.form.get('miqdor', 0))
        narx = Decimal(str(request.form.get('narx', 0)))
        sale.narx_dona = narx
        sale.jami_summa = sale.miqdor * narx
        # Qarz qismi o'zgarmaydi (to'lov alohida)
        sale.qoldiq_qarz = sale.jami_summa - old_tolandi
        
        # Update customer debt
        customer = Customer.query.get(sale.mijoz_id)
        if customer:
            customer.jami_qarz = customer.jami_qarz - old_qarz + sale.qoldiq_qarz
        
        # Agar to'lov qilingan bo'lsa (tolandi o'zgargan), haydovchi to'lovini ham yangilash
        new_tolandi = Decimal(str(request.form.get('tolandi', 0)))
        if new_tolandi > old_tolandi:
            # Qancha to'langanini hisoblash
            tolangan_qism = new_tolandi - old_tolandi
            driver_payment = DriverPayment.query.filter_by(sale_id=sale.id).first()
            if driver_payment and driver_payment.status == 'kutilmoqda':
                driver_payment.status = 'tolandi'
                driver_payment.collected_at = uz_datetime()
                # To'langan summani yangilash (faqat to'langan qismi)
                driver_payment.summa = tolangan_qism
        
        db.session.commit()
        flash('Sotuv ma\'lumoti yangilandi', 'success')
        return redirect(url_for('sales.list_sales'))
    
    customers = Customer.query.filter_by(status='faol').all()
    bread_types = BreadType.query.order_by(BreadType.nomi).all()
    return render_template('sales/edit.html', sale=sale, customers=customers, bread_types=bread_types)

@sales_bp.route('/delete/<int:id>')
@login_required
def delete_sale(id):
    from decimal import Decimal
    sale = Sale.query.get_or_404(id)
    
    # Update customer debt
    customer = Customer.query.get(sale.mijoz_id)
    if customer:
        customer.jami_qarz -= sale.qoldiq_qarz
    
    # Delete related cash entry if exists (for the payment part)
    if sale.tolandi > 0:
        cash_entry = Cash.query.filter(
            Cash.izoh.like(f'%Sotuv: {customer.nomi if customer else ""}%'),
            Cash.kirim == sale.tolandi
        ).order_by(Cash.id.desc()).first()
        if cash_entry:
            db.session.delete(cash_entry)
    
    # Delete related driver payment if exists
    driver_payment = DriverPayment.query.filter_by(sale_id=sale.id).first()
    if driver_payment:
        db.session.delete(driver_payment)
    
    db.session.delete(sale)
    db.session.commit()
    flash('Sotuv ma\'lumoti o\'chirildi', 'success')
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
        
        # Yangi o'tkazish yaratish
        new_transfer = BreadTransfer(
            sana=datetime.now().date(),
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
    db.session.delete(transfer)
    db.session.commit()
    flash('O\'tkazish o\'chirildi!', 'success')
    return redirect(url_for('sales.list_transfers'))

# ========== HAYDOVCHI TO'LOVLARI ==========
@sales_bp.route('/driver-payments')
@login_required
def driver_payments():
    """Haydovchi to'lovlari - faqat oldingi smenalar qarz to'lovlari"""
    from datetime import date, datetime, timedelta
    
    # MUHIM: Faqat "Smena yopish" bosilganda yangilanadi
    # Avtomatik yangilanish O'CHIRILDI - ertalabki 5 da ham yangilanmaydi
    
    # Oxirgi yopilgan smenani topish (faqat admin "Smena yopish" bosganda yopiladi)
    # Bu yerda avtomatik vaqt tekshiruvi YO'Q - faqat bazadagi smena holati asosida
    last_closed_smena = DayStatus.query.filter_by(status='yopiq').order_by(DayStatus.yopilgan_vaqt.desc()).first()
    
    # Bugungi sana
    today = date.today()
    
    # Haydovchi filter
    driver_id = request.args.get('driver_id', '')
    
    # Status filter (default: tolandi)
    status = request.args.get('status', 'tolandi')
    
    # Query - QARZ TO'LOVLARI (boshqa smenada olingan to'lovlar)
    # Qoida: Non berilgan smena < Pul olingan smena
    # Yani: Smena A da non berildi, Smena B da pul olindi → Qarz to'lovlari
    if last_closed_smena:
        # Faqat sale.smena < payment.smena bo'lgan to'lovlarni ko'rsatish
        # (Shu smenada non berildi + shu smenada pul olindi = Bugungi sotuvlarda)
        query = DriverPayment.query.filter(
            DriverPayment.sale.has(Sale.smena < DriverPayment.smena),
            DriverPayment.status == 'tolandi'
        )
    else:
        # Smena hali yopilmagan - hech narsa ko'rsatilmaydi
        query = DriverPayment.query.filter(False)
    
    if driver_id:
        query = query.filter(DriverPayment.driver_id == driver_id)
    
    if status:
        query = query.filter(DriverPayment.status == status)
    
    payments = query.order_by(DriverPayment.created_at.desc()).all()
    
    # Barcha haydovchilar (filter uchun)
    drivers = Employee.query.filter_by(lavozim='Haydovchi', status='faol').all()
    
    # Jami hisoblar
    jami_kutilmoqda = sum([p.summa for p in payments if p.status == 'kutilmoqda'])
    jami_tolandan = sum([p.summa for p in payments if p.status == 'tolandi'])
    
    return render_template('sales/driver_payments.html',
                         payments=payments,
                         drivers=drivers,
                         driver_id=driver_id,
                         status=status,
                         jami_kutilmoqda=jami_kutilmoqda,
                         jami_tolandan=jami_tolandan)

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
