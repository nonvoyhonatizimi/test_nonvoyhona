from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Dough, BreadMaking, Oven, OvenDetail, Employee, UnQoldiq, UnTuri, BreadType, BreadTransfer, DriverInventory, uz_datetime
from datetime import datetime, timedelta

production_bp = Blueprint('production', __name__, url_prefix='/production')

@production_bp.route('/dough')
@login_required
def list_dough():
    doughs = Dough.query.order_by(Dough.sana.desc()).all()
    return render_template('production/dough_list.html', doughs=doughs, timedelta=timedelta)

@production_bp.route('/dough/add', methods=['GET', 'POST'])
@login_required
def add_dough():
    # Mavjud un turlarini olish
    un_turlari = UnTuri.query.all()
    
    # Tanlangan un turi - GET da birinchi turini, POST da formadan olamiz
    if request.method == 'POST':
        tanlangan_un_turi = request.form.get('un_turi', 'Oddiy un')
    else:
        tanlangan_un_turi = un_turlari[0].nomi if un_turlari else 'Oddiy un'
    
    # Joriy un qoldigini olish (kg bo'yicha) - 1 qop = 50 kg
    un_qoldiq_kg = (db.session.query(db.func.sum(UnQoldiq.qop_soni)).filter_by(un_turi=tanlangan_un_turi).scalar() or 0) * 50
    ishlatilgan_un_kg = db.session.query(db.func.sum(Dough.un_kg)).filter_by(un_turi=tanlangan_un_turi).scalar() or 0
    mavjud_un_kg = un_qoldiq_kg - ishlatilgan_un_kg
    
    if request.method == 'POST':
        xodim_id = request.form.get('xodim_id')
        un_kg = int(request.form.get('un_kg', 0) or 0)  # Hamir kg
        
        # Un yetarli ekanligini tekshirish (kg bo'yicha)
        if un_kg > mavjud_un_kg:
            flash(f'Xatolik: {tanlangan_un_turi} dan faqat {mavjud_un_kg} kg mavjud! {un_kg} kg kerak.', 'error')
            employees = Employee.query.filter_by(lavozim='Xamirchi').all()
            return render_template('production/dough_add.html', employees=employees, un_turlari=un_turlari, 
                                 tanlangan_un_turi=tanlangan_un_turi, mavjud_un_kg=mavjud_un_kg)
        
        new_dough = Dough(
            sana=datetime.now().date(),
            xodim_id=xodim_id,
            un_turi=tanlangan_un_turi,
            un_kg=un_kg
        )
        db.session.add(new_dough)
        db.session.commit()
        ish_haqqi = un_kg * 600  # 1 kg = 600 so'm
        flash(f'Xamir ma\'lumoti qo\'shildi. {un_kg} kg hamir. Ish haqqi: {ish_haqqi:,} so\'m', 'success')
        return redirect(url_for('production.list_dough'))
    
    employees = Employee.query.filter_by(lavozim='Xamirchi').all()
    return render_template('production/dough_add.html', employees=employees, un_turlari=un_turlari, 
                         tanlangan_un_turi=tanlangan_un_turi, mavjud_un_kg=mavjud_un_kg)

@production_bp.route('/dough/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_dough(id):
    dough = Dough.query.get_or_404(id)
    
    if request.method == 'POST':
        dough.xodim_id = request.form.get('xodim_id')
        dough.un_kg = int(request.form.get('un_kg', 0))
        dough.un_turi = request.form.get('un_turi')
        
        db.session.commit()
        flash('Xamir ma\'lumoti yangilandi', 'success')
        return redirect(url_for('production.list_dough'))
    
    employees = Employee.query.filter_by(lavozim='Xamirchi').all()
    un_turlari = UnTuri.query.all()
    return render_template('production/dough_edit.html', dough=dough, employees=employees, un_turlari=un_turlari)

@production_bp.route('/dough/delete/<int:id>')
@login_required
def delete_dough(id):
    dough = Dough.query.get_or_404(id)
    
    # Delete related bread making records first
    BreadMaking.query.filter_by(xamir_id=dough.id).delete()
    
    db.session.delete(dough)
    db.session.commit()
    flash('Xamir ma\'lumoti o\'chirildi', 'success')
    return redirect(url_for('production.list_dough'))

@production_bp.route('/bread')
@login_required
def list_bread():
    breads = BreadMaking.query.order_by(BreadMaking.created_at.desc()).all()
    
    # Bir xil vaqt va xodimga ega yozuvlarni guruhlash
    grouped = {}
    for b in breads:
        # Guruh kaliti: created_at + xodim_id
        key = f"{(b.created_at.strftime('%Y%m%d%H%M') if b.created_at else b.sana.strftime('%Y%m%d'))}_{b.xodim_id}"
        if key not in grouped:
            grouped[key] = {
                'items': [],
                'created_at': b.created_at,
                'sana': b.sana,
                'first_id': b.id
            }
        grouped[key]['items'].append(b)
    
    return render_template('production/bread_list.html', grouped_breads=grouped.values(), timedelta=timedelta)

@production_bp.route('/bread/add', methods=['GET', 'POST'])
@login_required
def add_bread():
    if request.method == 'POST':
        xamir_id = request.form.get('xamir_id')
        xodim_id = request.form.get('xodim_id')
        
        # Tanlangan xamir ma'lumotlarini olish
        dough = Dough.query.get(xamir_id)
        hamir_kg = dough.un_kg if dough else 0
        
        # 4 ta non turini qayta ishlash
        non_turlari_saqlangan = []
        for i in range(1, 5):
            non_turi = request.form.get(f'non_turi_{i}', '')
            chiqqan_non = int(request.form.get(f'chiqqan_non_{i}', 0) or 0)
            brak_non = int(request.form.get(f'brak_non_{i}', 0) or 0)
            
            # Faqat tanlangan non turlarini saqlash
            if non_turi and chiqqan_non > 0:
                new_bread = BreadMaking(
                    sana=datetime.now().date(),
                    xamir_id=xamir_id,
                    xodim_id=xodim_id,
                    hamir_kg=hamir_kg,  # Barcha turlar uchun bir xil hamir kg
                    non_turi=non_turi,
                    chiqqan_non=chiqqan_non,
                    brak=brak_non,
                    sof_non=chiqqan_non - brak_non
                )
                db.session.add(new_bread)
                non_turlari_saqlangan.append(f"{non_turi} ({chiqqan_non} dona)")
        
        db.session.commit()
        
        if non_turlari_saqlangan:
            ish_haqqi = hamir_kg * 1500  # 1 kg = 1500 so'm (bitta xamir uchun)
            flash(f"Non yasash: {', '.join(non_turlari_saqlangan)}. Xamir: {hamir_kg} kg. Ish haqqi: {ish_haqqi:,} so'm (bir marta)", 'success')
        else:
            flash('Hech qanday non turi tanlanmadi!', 'warning')
        
        return redirect(url_for('production.list_bread'))
    
    doughs = Dough.query.order_by(Dough.sana.desc()).all()
    employees = Employee.query.filter_by(lavozim='Yasovchi').all()
    non_turlari = BreadType.query.order_by(BreadType.nomi).all()
    return render_template('production/bread_add.html', doughs=doughs, employees=employees, non_turlari=non_turlari, timedelta=timedelta)

@production_bp.route('/bread/delete/<int:id>')
@login_required
def delete_bread(id):
    """Guruhlangan nonlarni o'chirish - bir vaqtda qo'shilganlarni hammasini o'chiradi"""
    target = BreadMaking.query.get_or_404(id)
    
    # Shu xodim va shu vaqtda qo'shilgan barcha nonlarni topish
    if target.created_at:
        key_time = target.created_at.strftime('%Y%m%d%H%M')
        all_to_delete = BreadMaking.query.filter(
            BreadMaking.xodim_id == target.xodim_id,
            db.func.strftime('%Y%m%d%H%M', BreadMaking.created_at) == key_time
        ).all()
    else:
        # created_at bo'lmasa, faqat shu ID ni o'chirish
        all_to_delete = [target]
    
    count = len(all_to_delete)
    for b in all_to_delete:
        db.session.delete(b)
    db.session.commit()
    flash(f'{count} ta non yozuvi o\'chirildi!', 'success')
    return redirect(url_for('production.list_bread'))

@production_bp.route('/bread/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_bread(id):
    bread = BreadMaking.query.get_or_404(id)
    
    if request.method == 'POST':
        bread.non_turi = request.form.get('non_turi')
        bread.chiqqan_non = int(request.form.get('chiqqan_non', 0))
        bread.brak = int(request.form.get('brak_non', 0))
        bread.sof_non = bread.chiqqan_non - bread.brak
        
        db.session.commit()
        flash('Non yasash ma\'lumoti yangilandi', 'success')
        return redirect(url_for('production.list_bread'))
    
    non_turlari = BreadType.query.order_by(BreadType.nomi).all()
    return render_template('production/bread_edit.html', bread=bread, non_turlari=non_turlari)

@production_bp.route('/oven')
@login_required
def list_oven():
    ovens = Oven.query.order_by(Oven.sana.desc()).all()
    return render_template('production/oven_list.html', ovens=ovens)

@production_bp.route('/oven/add', methods=['GET', 'POST'])
@login_required
def add_oven():
    if request.method == 'POST':
        tandirchi_id = request.form.get('tandirchi_id')
        yopilgan_non_kg = float(request.form.get('yopilgan_non_kg', 0) or 0)
        
        # Asosiy Oven yozuvi
        new_oven = Oven(
            sana=datetime.now().date(),
            xodim_id=tandirchi_id,
            un_kg=yopilgan_non_kg
        )
        db.session.add(new_oven)
        db.session.commit()
        
        # 4 ta non turini alohida saqlash
        jami_chiqqan = 0
        jami_brak = 0
        
        for i in range(1, 5):
            non_turi = request.form.get(f'non_turi_{i}', '').strip()
            chiqqan = int(request.form.get(f'chiqqan_{i}', 0) or 0)
            brak = int(request.form.get(f'brak_{i}', 0) or 0)
            
            if non_turi and chiqqan > 0:
                detail = OvenDetail(
                    oven_id=new_oven.id,
                    non_turi=non_turi,
                    chiqqan=chiqqan,
                    brak=brak,
                    sof=chiqqan - brak
                )
                db.session.add(detail)
                jami_chiqqan += chiqqan
                jami_brak += brak
        
        db.session.commit()
        ish_haqqi = int(yopilgan_non_kg * 1000)
        flash(f'Tandir ma\'lumoti qo\'shildi. Chiqqan: {jami_chiqqan}, Brak: {jami_brak}. Ish haqqi: {ish_haqqi:,} so\'m', 'success')
        return redirect(url_for('production.list_oven'))
    
    employees = Employee.query.filter_by(lavozim='Tandirchi').all()
    bread_types = BreadType.query.order_by(BreadType.nomi).all()
    return render_template('production/oven_add.html', employees=employees, bread_types=bread_types)

# ========== TANDIRCHI → HAYDOVCHI NON O'TKAZISH ==========
@production_bp.route('/oven/transfer', methods=['GET', 'POST'])
@login_required
def add_oven_transfer():
    """Tandirchi haydovchiga non o'tkazish"""
    import traceback
    
    # Faqat tandirchi yoki admin qila oladi
    if current_user.rol != 'admin' and (not current_user.employee or current_user.employee.lavozim != 'Tandirchi'):
        flash('Bu funksiya faqat tandirchi uchun!', 'error')
        return redirect(url_for('production.list_oven'))
    
    if request.method == 'POST':
        try:
            from_xodim_id = int(request.form.get('from_xodim_id', 0))
            to_xodim_id = int(request.form.get('to_xodim_id', 0))
            
            # 4 ta non turini olish
            non_turlar = []
            for i in range(1, 5):
                non_turi = request.form.get(f'non_turi_{i}', '')
                non_miqdor = int(request.form.get(f'non_miqdor_{i}', 0) or 0)
                if non_turi and non_miqdor > 0:
                    non_turlar.append((non_turi, non_miqdor))
            
            if not non_turlar:
                flash('Kamida bitta non turi va miqdor kiriting!', 'error')
                return redirect(url_for('production.add_oven_transfer'))
            
            # Yangi o'tkazish yaratish
            new_transfer = BreadTransfer(
                sana=datetime.now().date(),
                from_xodim_id=from_xodim_id,
                to_xodim_id=to_xodim_id,
                from_turi='tandirchi'
            )
            
            # Non turlarini qo'shish
            for i, (turi, miqdor) in enumerate(non_turlar[:4], 1):
                setattr(new_transfer, f'non_turi_{i}', turi)
                setattr(new_transfer, f'non_miqdor_{i}', miqdor)
            
            db.session.add(new_transfer)
            db.session.commit()
            
            # Haydovchi inventoryga non qo'shish
            for i, (turi, miqdor) in enumerate(non_turlar[:4], 1):
                if turi and miqdor > 0:
                    # Mavjud inventoryni tekshirish
                    inventory = DriverInventory.query.filter_by(
                        driver_id=to_xodim_id,
                        non_turi=turi,
                        sana=datetime.now().date()
                    ).first()
                    
                    if inventory:
                        inventory.miqdor += miqdor
                        inventory.updated_at = uz_datetime()
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
            return redirect(url_for('production.list_oven'))
            
        except Exception as e:
            db.session.rollback()
            error_msg = f"Xato: {str(e)}"
            print(f"[ERROR] Oven transfer: {error_msg}")
            print(traceback.format_exc())
            flash(error_msg, 'error')
            return redirect(url_for('production.add_oven_transfer'))
    
    # Tandirchilar va haydovchilarni olish
    tandirchilar = Employee.query.filter_by(lavozim='Tandirchi', status='faol').all()
    haydovchilar = Employee.query.filter_by(lavozim='Haydovchi', status='faol').all()
    non_turlari = BreadType.query.order_by(BreadType.nomi).all()
    
    return render_template('production/oven_transfer_add.html', 
                         tandirchilar=tandirchilar,
                         haydovchilar=haydovchilar, 
                         non_turlari=non_turlari)

@production_bp.route('/oven/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_oven(id):
    oven = Oven.query.get_or_404(id)
    
    if request.method == 'POST':
        oven.xodim_id = request.form.get('tandirchi_id')
        
        # Eski detallarni o'chirish
        OvenDetail.query.filter_by(oven_id=oven.id).delete()
        
        # Yangi detallarni qo'shish
        for i in range(1, 5):
            non_turi = request.form.get(f'non_turi_{i}', '').strip()
            chiqqan = int(request.form.get(f'chiqqan_{i}', 0) or 0)
            brak = int(request.form.get(f'brak_{i}', 0) or 0)
            
            if non_turi and chiqqan > 0:
                detail = OvenDetail(
                    oven_id=oven.id,
                    non_turi=non_turi,
                    chiqqan=chiqqan,
                    brak=brak,
                    sof=chiqqan - brak
                )
                db.session.add(detail)
        
        db.session.commit()
        flash('Tandir ma\'lumoti yangilandi', 'success')
        return redirect(url_for('production.list_oven'))
    
    employees = Employee.query.filter_by(lavozim='Tandirchi').all()
    bread_types = BreadType.query.order_by(BreadType.nomi).all()
    details = OvenDetail.query.filter_by(oven_id=oven.id).all()
    return render_template('production/oven_edit.html', oven=oven, employees=employees, bread_types=bread_types, details=details)

@production_bp.route('/oven/delete/<int:id>')
@login_required
def delete_oven(id):
    oven = Oven.query.get_or_404(id)
    db.session.delete(oven)
    db.session.commit()
    flash('Tandir ma\'lumoti o\'chirildi', 'success')
    return redirect(url_for('production.list_oven'))

# Un qoldigini boshqarish
@production_bp.route('/un-qoldiq')
@login_required
def un_qoldiq_list():
    # Har bir un turi bo'yicha qoldiqni hisoblash (kg bo'yicha)
    un_turlari = UnTuri.query.all()
    un_statistika = []
    
    for un_turi in un_turlari:
        kelgan_qop = db.session.query(db.func.sum(UnQoldiq.qop_soni)).filter_by(un_turi=un_turi.nomi).scalar() or 0
        kelgan_kg = kelgan_qop * 50  # 1 qop = 50 kg
        ishlatilgan_kg = db.session.query(db.func.sum(Dough.un_kg)).filter_by(un_turi=un_turi.nomi).scalar() or 0
        mavjud_kg = kelgan_kg - ishlatilgan_kg
        un_statistika.append({
            'turi': un_turi.nomi,
            'kelgan_kg': kelgan_kg,
            'ishlatilgan_kg': ishlatilgan_kg,
            'mavjud_kg': mavjud_kg
        })
    
    records = UnQoldiq.query.order_by(UnQoldiq.sana.desc()).all()
    return render_template('production/un_qoldiq_list.html', records=records, un_statistika=un_statistika, un_turlari=un_turlari)

@production_bp.route('/un-qoldiq/add', methods=['GET', 'POST'])
@login_required
def add_un_qoldiq():
    un_turlari = UnTuri.query.all()
    
    if request.method == 'POST':
        un_turi = request.form.get('un_turi')
        qop_soni = int(request.form.get('qop_soni', 0))
        izoh = request.form.get('izoh', '')
        
        new_un = UnQoldiq(
            un_turi=un_turi,
            qop_soni=qop_soni,
            izoh=izoh,
            xodim_id=current_user.employee_id if current_user.employee_id else 1
        )
        db.session.add(new_un)
        db.session.commit()
        flash(f'{qop_soni} qop {un_turi} qo\'shildi', 'success')
        return redirect(url_for('production.un_qoldiq_list'))
    
    return render_template('production/un_qoldiq_add.html', un_turlari=un_turlari)

# Un turlarini boshqarish
@production_bp.route('/un-turlari')
@login_required
def un_turlari_list():
    turlar = UnTuri.query.all()
    return render_template('production/un_turlari_list.html', turlar=turlar)

@production_bp.route('/un-turlari/add', methods=['GET', 'POST'])
@login_required
def add_un_turi():
    if request.method == 'POST':
        nomi = request.form.get('nomi')
        
        if UnTuri.query.filter_by(nomi=nomi).first():
            flash(f'{nomi} allaqachon mavjud', 'error')
            return redirect(url_for('production.un_turlari_list'))
        
        new_turi = UnTuri(nomi=nomi)
        db.session.add(new_turi)
        db.session.commit()
        flash(f'{nomi} qo\'shildi', 'success')
        return redirect(url_for('production.un_turlari_list'))
    
    return render_template('production/un_turi_add.html')

# ========== TANDIRCHI O'TKAZISH TAHIRLASH/O'CHIRISH ==========
@production_bp.route('/oven/transfer/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_oven_transfer(id):
    """Tandirchi o'tkazishini tahrirlash (admin va tandirchi)"""
    transfer = BreadTransfer.query.get_or_404(id)
    
    # Faqat admin yoki o'zi yaratgan tandirchi tahrirlay oladi
    if current_user.rol != 'admin' and (not current_user.employee or current_user.employee.id != transfer.from_xodim_id):
        flash('Bu o\'tkazishni tahrirlash huquqingiz yo\'q!', 'error')
        return redirect(url_for('production.list_oven'))
    
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
        return redirect(url_for('production.list_oven'))
    
    tandirchilar = Employee.query.filter_by(lavozim='Tandirchi', status='faol').all()
    haydovchilar = Employee.query.filter_by(lavozim='Haydovchi', status='faol').all()
    non_turlari = BreadType.query.order_by(BreadType.nomi).all()
    
    return render_template('production/oven_transfer_edit.html',
                         transfer=transfer,
                         tandirchilar=tandirchilar,
                         haydovchilar=haydovchilar,
                         non_turlari=non_turlari)

@production_bp.route('/oven/transfer/delete/<int:id>')
@login_required
def delete_oven_transfer(id):
    """Tandirchi o'tkazishini o'chirish (admin va tandirchi)"""
    transfer = BreadTransfer.query.get_or_404(id)
    
    # Faqat admin yoki o'zi yaratgan tandirchi o'chira oladi
    if current_user.rol != 'admin' and (not current_user.employee or current_user.employee.id != transfer.from_xodim_id):
        flash('Bu o\'tkazishni o\'chirish huquqingiz yo\'q!', 'error')
        return redirect(url_for('production.list_oven'))
    
    db.session.delete(transfer)
    db.session.commit()
    flash('O\'tkazish o\'chirildi!', 'success')
    return redirect(url_for('production.list_oven'))
