from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from models import db, Employee, Dough, Oven
from datetime import datetime, date
from calendar import monthrange

payroll_bp = Blueprint('payroll', __name__, url_prefix='/payroll')

@payroll_bp.route('/')
@login_required
def index():
    # Bugungi sana
    today = date.today()
    sana = request.args.get('sana', today.strftime('%Y-%m-%d'))
    
    try:
        filter_date = datetime.strptime(sana, '%Y-%m-%d').date()
    except:
        filter_date = today
    
    # Barcha ishchilarni olish
    employees = Employee.query.filter_by(status='faol').all()
    
    # Har bir ishchi uchun hisobot
    hisobot = []
    
    for emp in employees:
        from decimal import Decimal
        ishchi_malumot = {
            'id': emp.id,
            'ism': emp.ism,
            'lavozim': emp.lavozim,
            'stavka': Decimal(str(emp.ish_haqqi_stavka)) if emp.ish_haqqi_stavka else Decimal('0'),
            'ish_soni': 0,
            'jami_ish_haqqi': 0
        }
        
        # Xamirchi bo'lsa - qilgan hamir kg (har 1 kg = 600 so'm)
        if emp.lavozim == 'Xamirchi':
            xamirlar = Dough.query.filter_by(xodim_id=emp.id, sana=filter_date).all()
            jami_kg = sum([x.un_kg for x in xamirlar])
            ishchi_malumot['ish_soni'] = jami_kg
            ishchi_malumot['jami_ish_haqqi'] = jami_kg * 600  # 1 kg = 600 so'm
            ishchi_malumot['birlik'] = 'kg hamir'
        
        # Tandirchi bo'lsa - ishlatilgan un kg (har 1 kg = 1000 so'm)
        elif emp.lavozim == 'Tandirchi':
            tandirlar = Oven.query.filter_by(xodim_id=emp.id, sana=filter_date).all()
            jami_un_kg = sum([t.un_kg for t in tandirlar])
            ishchi_malumot['ish_soni'] = jami_un_kg
            ishchi_malumot['jami_ish_haqqi'] = jami_un_kg * 1000  # 1 kg = 1000 so'm
            ishchi_malumot['birlik'] = 'kg un'
        
        # Yasovchi bo'lsa - ishlatilgan hamir kg (har 1 kg = 1500 so'm)
        elif emp.lavozim == 'Yasovchi':
            from models import BreadMaking
            # Faqat bitta xamir uchun ish haqqi (har bir xamir_id faqat bir marta)
            nonlar = BreadMaking.query.filter_by(xodim_id=emp.id, sana=filter_date).all()
            # Xamir ID larni unique qilish (bitta xamir uchun bir marta)
            unique_xamir_ids = set()
            jami_hamir_kg = 0
            for n in nonlar:
                if n.xamir_id not in unique_xamir_ids:
                    unique_xamir_ids.add(n.xamir_id)
                    jami_hamir_kg += n.hamir_kg
            ishchi_malumot['ish_soni'] = jami_hamir_kg
            ishchi_malumot['jami_ish_haqqi'] = jami_hamir_kg * 1500  # 1 kg = 1500 so'm
            ishchi_malumot['birlik'] = 'kg hamir'
        
        hisobot.append(ishchi_malumot)
    
    return render_template('payroll/index.html', 
                         hisobot=hisobot, 
                         sana=filter_date.strftime('%Y-%m-%d'))

@payroll_bp.route('/detail/<int:employee_id>')
@login_required
def detail(employee_id):
    emp = Employee.query.get_or_404(employee_id)
    
    # Oy va yil
    yil = int(request.args.get('yil', date.today().year))
    oy = int(request.args.get('oy', date.today().month))
    
    # Oyning birinchi va oxirgi kuni
    _, oxirgi_kun = monthrange(yil, oy)
    boshlanish = date(yil, oy, 1)
    tugash = date(yil, oy, oxirgi_kun)
    
    # Kunlik hisobot
    kunlik_ish = []
    jami_ish_haqqi = 0
    
    for kun in range(1, oxirgi_kun + 1):
        ish_kuni = date(yil, oy, kun)
        ish_soni = 0
        
        if emp.lavozim == 'Xamirchi':
            xamirlar = Dough.query.filter_by(xodim_id=emp.id, sana=ish_kuni).all()
            ish_soni = sum([x.un_kg for x in xamirlar])
        elif emp.lavozim == 'Tandirchi':
            tandirlar = Oven.query.filter_by(xodim_id=emp.id, sana=ish_kuni).all()
            ish_soni = sum([t.un_kg for t in tandirlar])
        elif emp.lavozim == 'Yasovchi':
            from models import BreadMaking
            nonlar = BreadMaking.query.filter_by(xodim_id=emp.id, sana=ish_kuni).all()
            ish_soni = sum([n.hamir_kg for n in nonlar])
        
        if ish_soni > 0:
            from decimal import Decimal
            ish_haqqi = Decimal(str(ish_soni)) * Decimal(str(emp.ish_haqqi_stavka or 0))
            jami_ish_haqqi += ish_haqqi
            kunlik_ish.append({
                'sana': ish_kuni.strftime('%d.%m.%Y'),
                'ish_soni': ish_soni,
                'ish_haqqi': ish_haqqi
            })
    
    return render_template('payroll/detail.html',
                         employee=emp,
                         kunlik_ish=kunlik_ish,
                         jami_ish_haqqi=jami_ish_haqqi,
                         yil=yil,
                         oy=oy)
