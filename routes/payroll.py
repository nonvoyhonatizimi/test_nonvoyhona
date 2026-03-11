from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
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
            ishchi_malumot['stavka'] = 600
        
        # Tandirchi bo'lsa - ishlatilgan un kg (har 1 kg = 1000 so'm)
        elif emp.lavozim == 'Tandirchi':
            tandirlar = Oven.query.filter_by(xodim_id=emp.id, sana=filter_date).all()
            jami_un_kg = sum([t.un_kg for t in tandirlar])
            ishchi_malumot['ish_soni'] = jami_un_kg
            ishchi_malumot['jami_ish_haqqi'] = jami_un_kg * 1000  # 1 kg = 1000 so'm
            ishchi_malumot['birlik'] = 'kg un'
            ishchi_malumot['stavka'] = 1000
        
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
            ishchi_malumot['stavka'] = 1500
        
        hisobot.append(ishchi_malumot)
    
    return render_template('payroll/index.html', 
                         hisobot=hisobot, 
                         sana=filter_date.strftime('%Y-%m-%d'))

@payroll_bp.route('/detail/<int:employee_id>')
@login_required
def detail(employee_id):
    from models import SalaryPayment, EmployeeNote
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
    jami_tolangan = 0
    
    # Get all payments and notes for this month
    payments = SalaryPayment.query.filter(
        SalaryPayment.xodim_id == emp.id,
        SalaryPayment.sana >= boshlanish,
        SalaryPayment.sana <= tugash
    ).all()
    
    notes = EmployeeNote.query.filter(
        EmployeeNote.xodim_id == emp.id,
        EmployeeNote.sana >= boshlanish,
        EmployeeNote.sana <= tugash
    ).all()
    
    payment_map = {p.sana: p for p in payments}
    
    # Create notes map where one date can have multiple notes
    note_map = {}
    for note in notes:
        if note.sana not in note_map:
            note_map[note.sana] = []
        note_map[note.sana].append(note)
    
    for kun in range(1, oxirgi_kun + 1):
        ish_kuni = date(yil, oy, kun)
        ish_soni = 0
        stavka = 0
        
        if emp.lavozim == 'Xamirchi':
            xamirlar = Dough.query.filter_by(xodim_id=emp.id, sana=ish_kuni).all()
            ish_soni = sum([x.un_kg for x in xamirlar])
            stavka = 600
        elif emp.lavozim == 'Tandirchi':
            tandirlar = Oven.query.filter_by(xodim_id=emp.id, sana=ish_kuni).all()
            ish_soni = sum([t.un_kg for t in tandirlar])
            stavka = 1000
        elif emp.lavozim == 'Yasovchi':
            from models import BreadMaking
            nonlar = BreadMaking.query.filter_by(xodim_id=emp.id, sana=ish_kuni).all()
            unique_xamir_ids = set()
            jami_hamir_kg = 0
            for n in nonlar:
                if n.xamir_id not in unique_xamir_ids:
                    unique_xamir_ids.add(n.xamir_id)
                    jami_hamir_kg += n.hamir_kg
            ish_soni = jami_hamir_kg
            stavka = 1500
        else:
            stavka = emp.ish_haqqi_stavka or 0
        
        day_notes = note_map.get(ish_kuni, [])
        payment = payment_map.get(ish_kuni)
        
        if ish_soni > 0 or payment:
            from decimal import Decimal
            ish_haqqi = Decimal(str(ish_soni)) * Decimal(str(stavka))
            jami_ish_haqqi += ish_haqqi
            
            is_paid = bool(payment)
            if is_paid:
                jami_tolangan += ish_haqqi
                payment_id = payment.id
                payment_izoh = payment.izoh
            else:
                payment_id = None
                payment_izoh = None
                
            kunlik_ish.append({
                'sana_obj': ish_kuni,
                'sana': ish_kuni.strftime('%d.%m.%Y'),
                'ish_soni': ish_soni,
                'ish_haqqi': ish_haqqi,
                'is_paid': is_paid,
                'payment_id': payment_id,
                'payment_izoh': payment_izoh,
                'notes': day_notes
            })
            
    # Kunlarni teskari tartibda, tepadagilar birinchi ko'rinishi uchun
    kunlik_ish.reverse()
    
    return render_template('payroll/detail.html',
                         employee=emp,
                         kunlik_ish=kunlik_ish,
                         jami_ish_haqqi=jami_ish_haqqi,
                         jami_tolangan=jami_tolangan,
                         yil=yil,
                         oy=oy,
                         notes=notes)

@payroll_bp.route('/pay/<int:employee_id>', methods=['POST'])
@login_required
def pay_salary(employee_id):
    if current_user.rol != 'admin':
        flash("Ish haqqini faqat admin to'lay oladi!", "error")
        return redirect(url_for('payroll.detail', employee_id=employee_id))
        
    from models import SalaryPayment, uz_datetime
    
    sana_str = request.form.get('sana')
    summa = float(request.form.get('summa', 0))
    izoh = request.form.get('izoh', '')
    
    if not sana_str or (summa <= 0 and not izoh):
        flash("Noto'g'ri ma'lumotlar!", "error")
        return redirect(url_for('payroll.detail', employee_id=employee_id))
        
    try:
        sana = datetime.strptime(sana_str, '%Y-%m-%d').date()
    except ValueError:
        flash("Noto'g'ri sana formati!", "error")
        return redirect(url_for('payroll.detail', employee_id=employee_id))
        
    # Tekshirib ko'ramiz oldin to'langanmi
    existing = SalaryPayment.query.filter_by(xodim_id=employee_id, sana=sana).first()
    if existing:
        flash("Bu kun uchun ish haqqi allaqachon to'langan!", "error")
    else:
        new_payment = SalaryPayment(
            xodim_id=employee_id,
            sana=sana,
            summa=summa,
            izoh=izoh,
            created_at=uz_datetime()
        )
        db.session.add(new_payment)
        db.session.commit()
        flash(f"{sana.strftime('%d.%m.%Y')} sanasi uchun to'lov saqlandi!", "success")
        
    # URL argumentlari orqali yil va oyni saqlab qolish
    yil = request.args.get('yil', date.today().year)
    oy = request.args.get('oy', date.today().month)
    return redirect(url_for('payroll.detail', employee_id=employee_id, yil=yil, oy=oy))

@payroll_bp.route('/add_note/<int:employee_id>', methods=['POST'])
@login_required
def add_note(employee_id):
    if current_user.rol != 'admin':
        flash("Izoh qoldirish faqat adminlar uchun!", "error")
        return redirect(url_for('payroll.detail', employee_id=employee_id))
        
    from models import EmployeeNote, uz_datetime
    
    sana_str = request.form.get('sana')
    izoh = request.form.get('izoh', '').strip()
    
    if not izoh:
        flash("Izoh kiritilishi shart!", "error")
        return redirect(url_for('payroll.detail', employee_id=employee_id))
        
    if sana_str:
        try:
            sana = datetime.strptime(sana_str, '%Y-%m-%d').date()
        except ValueError:
            flash("Noto'g'ri sana formati!", "error")
            return redirect(url_for('payroll.detail', employee_id=employee_id))
    else:
        sana = uz_datetime().date()
        
    new_note = EmployeeNote(
        xodim_id=employee_id,
        sana=sana,
        izoh=izoh,
        created_at=uz_datetime()
    )
    db.session.add(new_note)
    db.session.commit()
    
    flash("Izoh muvaffaqiyatli saqlandi!", "success")
    
    yil = request.args.get('yil', date.today().year)
    oy = request.args.get('oy', date.today().month)
    return redirect(url_for('payroll.detail', employee_id=employee_id, yil=yil, oy=oy))

@payroll_bp.route('/delete_note/<int:note_id>')
@login_required
def delete_note(note_id):
    if current_user.rol != 'admin':
        flash("Izohni o'chirish faqat adminlar uchun!", "error")
        return redirect(url_for('payroll.index'))
        
    from models import EmployeeNote
    note = EmployeeNote.query.get_or_404(note_id)
    emp_id = note.xodim_id
    
    db.session.delete(note)
    db.session.commit()
    
    flash("Izoh o'chirildi!", "success")
    
    yil = request.args.get('yil', date.today().year)
    oy = request.args.get('oy', date.today().month)
    return redirect(url_for('payroll.detail', employee_id=emp_id, yil=yil, oy=oy))
