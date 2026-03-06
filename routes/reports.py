from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Customer, Sale, Employee, Dough, BreadMaking, Oven, BreadTransfer, DriverInventory, DayStatus, uz_datetime
from sqlalchemy import func
from decimal import Decimal
import requests
from datetime import datetime, timedelta

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

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

@reports_bp.route('/debts')
@login_required
def customer_debts():
    """Customer debts report with detailed breakdown"""
    # Get all customers with debts
    customers = Customer.query.filter(Customer.jami_qarz > 0).order_by(Customer.jami_qarz.desc()).all()
    
    # Build report data
    report_data = []
    for customer in customers:
        # Get sales breakdown by bread type
        sales_breakdown = db.session.query(
            Sale.non_turi,
            func.sum(Sale.miqdor).label('total_miqdor'),
            func.sum(Sale.jami_summa).label('total_summa'),
            func.sum(Sale.tolandi).label('total_tolandi'),
            func.sum(Sale.qoldiq_qarz).label('total_qarz')
        ).filter(
            Sale.mijoz_id == customer.id,
            Sale.qoldiq_qarz > 0
        ).group_by(Sale.non_turi).all()
        
        # Check if customer has telegram group
        has_telegram = False
        customer_lower = customer.nomi.lower().strip()
        for key in CUSTOMER_GROUPS.keys():
            if key.lower() in customer_lower or customer_lower in key.lower():
                has_telegram = True
                break
        
        report_data.append({
            'customer': customer,
            'breakdown': sales_breakdown,
            'has_telegram': has_telegram
        })
    
    return render_template('reports/debts.html', report_data=report_data)

@reports_bp.route('/send-debt-notification/<int:customer_id>')
@login_required
def send_debt_notification(customer_id):
    """Send debt notification to customer's Telegram group"""
    customer = Customer.query.get_or_404(customer_id)
    
    # Find matching chat ID
    chat_id = None
    customer_lower = customer.nomi.lower().strip()
    
    for key, value in CUSTOMER_GROUPS.items():
        if key.lower() in customer_lower or customer_lower in key.lower():
            chat_id = value
            break
    
    if not chat_id:
        flash(f'Telegram guruh topilmadi: {customer.nomi}')
        return redirect(url_for('reports.customer_debts'))
    
    # Get sales breakdown
    sales_breakdown = db.session.query(
        Sale.non_turi,
        func.sum(Sale.miqdor).label('total_miqdor'),
        func.sum(Sale.jami_summa).label('total_summa'),
        func.sum(Sale.tolandi).label('total_tolandi'),
        func.sum(Sale.qoldiq_qarz).label('total_qarz')
    ).filter(
        Sale.mijoz_id == customer.id,
        Sale.qoldiq_qarz > 0
    ).group_by(Sale.non_turi).all()
    
    # Build message
    message = f"""
QARZ ESLATMASI

Mijoz: {customer.nomi}
Umumiy qarz: {float(customer.jami_qarz):,.0f} so'm

Qarz tafsiloti:
"""
    
    for item in sales_breakdown:
        message += f"\n{item.non_turi}: {item.total_miqdor} dona"
        message += f"\n   Jami: {float(item.total_summa):,.0f} so'm"
        message += f"\n   To'landi: {float(item.total_tolandi):,.0f} so'm"
        message += f"\n   Qarz: {float(item.total_qarz):,.0f} so'm\n"
    
    message += f"\nIltimos, kassa qiling!"
    
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
            flash(f'Xabar yuborildi: {customer.nomi}')
        else:
            flash(f'Xatolik: {response.status_code} - {response.text}')
    except Exception as e:
        flash(f'Xatolik: {e}')
    
    return redirect(url_for('reports.customer_debts'))

@reports_bp.route('/edit-debt/<int:customer_id>', methods=['GET', 'POST'])
@login_required
def edit_debt(customer_id):
    """Mijoz qarzini tahrirlash (faqat admin)"""
    if current_user.rol != 'admin':
        flash('Bu funksiya faqat admin uchun!', 'error')
        return redirect(url_for('reports.customer_debts'))
    
    customer = Customer.query.get_or_404(customer_id)
    
    if request.method == 'POST':
        from decimal import Decimal
        new_debt = Decimal(str(request.form.get('new_debt', 0)))
        
        # Eski qarzni hisobga olib, yangilash
        old_debt = customer.jami_qarz
        customer.jami_qarz = new_debt
        
        db.session.commit()
        flash(f'{customer.nomi} qarzi {float(old_debt):,.0f} dan {float(new_debt):,.0f} so\'m ga yangilandi!', 'success')
        return redirect(url_for('reports.customer_debts'))
    
    return render_template('reports/edit_debt.html', customer=customer)

@reports_bp.route('/daily-production')
@login_required
def daily_production():
    """Kunlik ishlab chiqarish hisoboti"""
    # Sana parametri
    filter_date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    filter_date = datetime.strptime(filter_date, '%Y-%m-%d').date()
    
    # Xamir ma'lumotlari
    xamirlar = Dough.query.filter_by(sana=filter_date).all()
    jami_xamir_kg = sum([x.un_kg for x in xamirlar])
    
    # Non yasash ma'lumotlari
    nonlar = BreadMaking.query.filter_by(sana=filter_date).all()
    jami_non = sum([n.chiqqan_non for n in nonlar])
    jami_brak = sum([n.brak for n in nonlar])
    
    # Non turlari bo'yicha
    non_turlari = db.session.query(
        BreadMaking.non_turi,
        func.sum(BreadMaking.chiqqan_non).label('jami'),
        func.sum(BreadMaking.brak).label('brak')
    ).filter_by(sana=filter_date).group_by(BreadMaking.non_turi).all()
    
    # Tandir ma'lumotlari
    tandirlar = Oven.query.filter_by(sana=filter_date).all()
    jami_tandir_kg = sum([t.un_kg for t in tandirlar])
    jami_kirdi = sum([t.kirdi for t in tandirlar])
    jami_chiqdi = sum([t.chiqdi for t in tandirlar])
    
    return render_template('reports/daily_production.html',
                         filter_date=filter_date,
                         xamirlar=xamirlar,
                         jami_xamir_kg=jami_xamir_kg,
                         nonlar=nonlar,
                         jami_non=jami_non,
                         jami_brak=jami_brak,
                         non_turlari=non_turlari,
                         tandirlar=tandirlar,
                         jami_tandir_kg=jami_tandir_kg,
                         jami_kirdi=jami_kirdi,
                         jami_chiqdi=jami_chiqdi)

@reports_bp.route('/employee-stats')
@login_required
def employee_stats():
    """Xodimlar ishi hisoboti"""
    # Sana parametrlari
    start_date = request.args.get('start_date', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Barcha xodimlar
    employees = Employee.query.all()
    
    # Har bir xodimning ishi
    xodimlar_ishi = []
    for emp in employees:
        ish_malumot = {
            'xodim': emp,
            'lavozim': emp.lavozim,
            'ish_soni': 0,
            'jami_ish_haqqi': 0
        }
        
        if emp.lavozim == 'Xamirchi':
            xamirlar = Dough.query.filter(
                Dough.xodim_id == emp.id,
                Dough.sana >= start_date,
                Dough.sana <= end_date
            ).all()
            jami_kg = sum([x.un_kg for x in xamirlar])
            ish_malumot['ish_soni'] = jami_kg
            ish_malumot['jami_ish_haqqi'] = jami_kg * 600
            ish_malumot['birlik'] = 'kg hamir'
            
        elif emp.lavozim == 'Yasovchi':
            nonlar = BreadMaking.query.filter(
                BreadMaking.xodim_id == emp.id,
                BreadMaking.sana >= start_date,
                BreadMaking.sana <= end_date
            ).all()
            # Har bir non yozuvi uchun ish haqqi
            jami_haqqi = sum([n.hamir_kg * 1500 for n in nonlar])
            ish_malumot['ish_soni'] = len(nonlar)
            ish_malumot['jami_ish_haqqi'] = jami_haqqi
            ish_malumot['birlik'] = 'ta yozuv'
            
        elif emp.lavozim == 'Tandirchi':
            tandirlar = Oven.query.filter(
                Oven.xodim_id == emp.id,
                Oven.sana >= start_date,
                Oven.sana <= end_date
            ).all()
            jami_kg = sum([t.un_kg for t in tandirlar])
            ish_malumot['ish_soni'] = jami_kg
            ish_malumot['jami_ish_haqqi'] = jami_kg * 1000
            ish_malumot['birlik'] = 'kg un'
        
        xodimlar_ishi.append(ish_malumot)
    
    return render_template('reports/employee_stats.html',
                         start_date=start_date,
                         end_date=end_date,
                         xodimlar_ishi=xodimlar_ishi)

@reports_bp.route('/daily-transfers')
@login_required
def daily_transfers():
    """Bugungi barcha o'tkazishlar hisoboti"""
    if current_user.rol != 'admin':
        flash('Bu funksiya faqat admin uchun!', 'error')
        return redirect(url_for('index'))
    
    # Sana parametri
    filter_date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    filter_date = datetime.strptime(filter_date, '%Y-%m-%d').date()
    
    # Haydovchi → Haydovchi o'tkazishlari
    haydovchi_transfers = BreadTransfer.query.filter(
        BreadTransfer.from_turi == 'haydovchi',
        BreadTransfer.sana == filter_date
    ).order_by(BreadTransfer.created_at.desc()).all()
    
    # Tandirchi → Haydovchi o'tkazishlari
    tandirchi_transfers = BreadTransfer.query.filter(
        BreadTransfer.from_turi == 'tandirchi',
        BreadTransfer.sana == filter_date
    ).order_by(BreadTransfer.created_at.desc()).all()
    
    # Jami nonlar hisoboti
    jami_nonlar = {}
    for t in list(haydovchi_transfers) + list(tandirchi_transfers):
        for i in range(1, 5):
            turi = getattr(t, f'non_turi_{i}')
            miqdor = getattr(t, f'non_miqdor_{i}')
            if turi and miqdor > 0:
                if turi not in jami_nonlar:
                    jami_nonlar[turi] = 0
                jami_nonlar[turi] += miqdor
    
    return render_template('reports/daily_transfers.html',
                         filter_date=filter_date,
                         haydovchi_transfers=haydovchi_transfers,
                         tandirchi_transfers=tandirchi_transfers,
                         jami_nonlar=jami_nonlar)

@reports_bp.route('/daily-sales')
@login_required
def daily_sales():
    """Bugungi sotuvlar - haydovchi hisoboti (faqat smena bo'yicha)"""
    from datetime import date, datetime, timedelta
    from models import uz_datetime
    
    # SANA FILTRI OLIB TASHILANDI - faqat smena bo'yicha ishlaydi
    # Ertalabki 5 da avtomatik yangilanish O'CHIRILDI
    
    # Oxirgi ochiq smenani topish
    open_smena = DayStatus.query.filter_by(status='ochiq').order_by(DayStatus.id.desc()).first()
    
    # Agar ochiq smena bo'lsa, shu smenadan boshlab olish
    if open_smena:
        current_smena = open_smena.smena
    else:
        # Ochiq smena yo'q - barcha sotuvlarni ko'rsatish
        current_smena = 1
    
    # Haydovchi filter
    driver_id = request.args.get('driver_id', '')
    
    # Barcha haydovchilar
    drivers = Employee.query.filter_by(lavozim='Haydovchi', status='faol').all()
    
    # Sotuvlarni olish (faqat smena bo'yicha, SANA FILTRISIZ)
    query = Sale.query.filter(Sale.smena >= current_smena)
    if driver_id:
        # Agar haydovchi tanlangan bo'lsa, faqat o'sha haydovchining sotuvlari
        # (Hozircha barcha sotuvlarni olamiz, keyin filtrlaymiz)
        pass
    
    sales = query.order_by(Sale.sana.desc()).all()
    
    # Haydovchi bo'yicha guruhlash
    driver_sales = {}
    for sale in sales:
        # Bu yerda haydovchi aniqlanishi kerak (hozircha mijoz nomidan)
        driver_name = "Admin"  # Vaqtinchalik
        if driver_name not in driver_sales:
            driver_sales[driver_name] = {
                'qarz_sotuvlar': [],
                'naqt_sotuvlar': [],
                'jami_qarz': 0,
                'jami_naqt': 0
            }
        
        if sale.qoldiq_qarz > 0:
            driver_sales[driver_name]['qarz_sotuvlar'].append(sale)
            driver_sales[driver_name]['jami_qarz'] += sale.qoldiq_qarz
        else:
            driver_sales[driver_name]['naqt_sotuvlar'].append(sale)
            driver_sales[driver_name]['jami_naqt'] += sale.tolandi
    
    # O'tkazishlarni olish (sana filtrisiz)
    tandirchi_transfers = BreadTransfer.query.filter(
        BreadTransfer.from_turi == 'tandirchi'
    ).all()
    
    haydovchi_transfers = BreadTransfer.query.filter(
        BreadTransfer.from_turi == 'haydovchi'
    ).all()
    
    # Jami hisobot
    jami_sotuvlar = len(sales)
    jami_qarz = sum([s.qoldiq_qarz for s in sales])
    jami_naqt = sum([s.tolandi for s in sales])
    
    # Non turlari bo'yicha
    non_turlari = {}
    for sale in sales:
        if sale.non_turi not in non_turlari:
            non_turlari[sale.non_turi] = {'miqdor': 0, 'summa': 0}
        non_turlari[sale.non_turi]['miqdor'] += sale.miqdor
        non_turlari[sale.non_turi]['summa'] += sale.jami_summa
    
    # Haydovchi inventory (non qoldig'i) - guruhlash va jamlash
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
    
    # Kun holatini tekshirish - oxirgi smena
    day_status = DayStatus.query.order_by(DayStatus.id.desc()).first()
    
    # Ko'rsatish uchun sana (hozirgi vaqt)
    from datetime import date
    filter_date = date.today()
    
    return render_template('reports/daily_sales.html',
                         filter_date=filter_date,
                         driver_id=driver_id,
                         drivers=drivers,
                         driver_sales=driver_sales,
                         tandirchi_transfers=tandirchi_transfers,
                         haydovchi_transfers=haydovchi_transfers,
                         jami_sotuvlar=jami_sotuvlar,
                         jami_qarz=jami_qarz,
                         jami_naqt=jami_naqt,
                         non_turlari=non_turlari,
                         driver_inventory=driver_inventory,
                         day_status=day_status)

@reports_bp.route('/close-day', methods=['POST'])
@login_required
def close_day():
    """Smenani yopish - Bugungi sotuvlarni 0 dan boshlash (faqat admin)"""
    if current_user.rol != 'admin':
        flash('Bu funksiya faqat admin uchun!', 'error')
        return redirect(url_for('reports.daily_sales'))
    
    from datetime import date
    today = date.today()
    
    # Oxirgi smena raqamini aniqlash
    last_smena = DayStatus.query.filter_by(sana=today).order_by(DayStatus.smena.desc()).first()
    current_smena = last_smena.smena + 1 if last_smena else 1
    
    # Eski smenani yopish (agar ochiq bo'lsa)
    open_smena = DayStatus.query.filter_by(status='ochiq').first()
    if open_smena:
        open_smena.status = 'yopiq'
        open_smena.yopilgan_vaqt = uz_datetime()
        open_smena.yopgan_admin = current_user.ism
    
    # Yangi smena yaratish (ochiq)
    new_smena = DayStatus(
        sana=today,
        smena=current_smena,
        status='ochiq',
        yopilgan_vaqt=None,
        yopgan_admin=None
    )
    db.session.add(new_smena)
    
    # Haydovchi qoldiqlarini tozalash (smena yopilganda 0 dan boshlanadi)
    DriverInventory.query.filter(DriverInventory.sana == today).delete()
    
    # Haydovchi to'lovlarini tozalash (smena yopilganda 0 dan boshlanadi)
    from models import DriverPayment
    DriverPayment.query.filter(
        db.func.date(DriverPayment.created_at) == today,
        DriverPayment.smena < current_smena
    ).delete()
    
    db.session.commit()
    
    flash('Smena yopildi! Bugungi sotuvlar va Qarz to\'lovlari yangi hisobotdan boshlandi.', 'success')
    # Bugungi sotuvlar sahifasiga qaytadi (Qarz to'lovlari ham yangilandi)
    return redirect(url_for('reports.daily_sales'))
