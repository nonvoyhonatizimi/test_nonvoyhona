#!/usr/bin/env python3
"""
Skrinshotlardagi sotuvlarni qo'shish
03.03.2026 - 40 ta sotuv
"""

from app import app
from models import db, Sale, Customer, BreadType, Employee, DriverPayment
from datetime import datetime, date
from decimal import Decimal

def get_or_create_customer(nomi, qarz=0):
    """Mijozni topish yoki yaratish"""
    mijoz = Customer.query.filter_by(nomi=nomi).first()
    if not mijoz:
        mijoz = Customer(nomi=nomi, telefon='', manzil='', status='faol', jami_qarz=qarz)
        db.session.add(mijoz)
        db.session.commit()
        print(f"[YANGI MIJOZ] {nomi} (Qarz: {float(qarz):,.0f} so'm)")
    else:
        # Mavjud mijozning qarzini yangilash
        if qarz > 0 and mijoz.jami_qarz != qarz:
            mijoz.jami_qarz = qarz
            db.session.commit()
            print(f"[YANGILANDI] {nomi} (Qarz: {float(qarz):,.0f} so'm)")
    return mijoz

def add_sale(sana, soat, mijoz_nomi, non_turi, miqdor, narx, tolandi, qarz, xodim, smena=1):
    """Bitta sotuv qo'shish"""
    
    # Mijozni olish/yaratish
    mijoz = get_or_create_customer(mijoz_nomi)
    
    # Sana va vaqtni yaratish
    sana_obj = datetime.strptime(sana, '%d.%m.%Y').date()
    vaqt_obj = datetime.strptime(soat, '%H:%M')
    created_at = datetime.combine(sana_obj, vaqt_obj.time())
    
    # Jami summa
    jami = Decimal(str(miqdor)) * Decimal(str(narx))
    
    # Sale yaratish
    sale = Sale(
        sana=sana_obj,
        smena=smena,
        mijoz_id=mijoz.id,
        non_turi=non_turi,
        miqdor=miqdor,
        narx_dona=Decimal(str(narx)),
        jami_summa=jami,
        tolandi=Decimal(str(tolandi)),
        qoldiq_qarz=Decimal(str(qarz)),
        xodim=xodim,
        created_at=created_at
    )
    db.session.add(sale)
    db.session.flush()  # ID olish uchun
    
    # Agar qarz bo'lsa, DriverPayment yaratish
    if qarz > 0:
        # Haydovchi topish (Abdulloh)
        driver = Employee.query.filter_by(ism='Abdulloh').first()
        driver_id = driver.id if driver else None
        
        driver_payment = DriverPayment(
            sale_id=sale.id,
            driver_id=driver_id,
            mijoz_id=mijoz.id,
            summa=Decimal(str(qarz)),
            smena=smena,
            status='kutilmoqda',
            created_at=created_at
        )
        db.session.add(driver_payment)
    
    db.session.commit()
    print(f"[QO'SHILDI] {soat} | {mijoz_nomi} | {non_turi} x{miqdor} | {float(jami):,.0f} so'm")
    return sale

def add_customers():
    """Yangi mijozlarni qo'shish"""
    with app.app_context():
        print("=" * 60)
        print("MIJOZLARNI QO'SHISH")
        print("=" * 60)
        
        customers_data = [
            ('Naqt sotuvlar', 0),
            ('Xadyalar', 0),
            ('Inomjon chag\'ali', 0),
            ('Yoquthon chag\'ali', 0),
            ('Xon choyxona', 260000),
            ('Mirzo patir', 48000),
        ]
        
        for nomi, qarz in customers_data:
            get_or_create_customer(nomi, qarz)
        
        print("=" * 60)

def add_all_sales():
    """Barcha sotuvlarni qo'shish (mijozlar qo'shilgandan keyin)"""
    with app.app_context():
        # Sotuvlar ro'yxati (skrinshotlardan)
        sales_data = [
            # Skrinshot 1
            ('03.03.2026', '06:36', 'Doston', 'Domboq', 10, 8500, 85000, 0, 'Abdulloh'),
            ('03.03.2026', '06:36', 'Doston', 'Domboq', 5, 8500, 42500, 0, 'Abdulloh'),
            ('03.03.2026', '06:42', 'turonboy', 'Domboq', 5, 8500, 0, 42500, 'Abdulloh'),
            ('03.03.2026', '06:45', 'ziyo patir', 'Domboq', 5, 8500, 0, 42500, 'Abdulloh'),
            ('03.03.2026', '06:46', 'noilaxon', 'Domboq', 10, 8500, 0, 85000, 'Abdulloh'),
            ('03.03.2026', '06:47', 'Naqt sotuvlar', 'Domboq', 2, 8500, 17000, 0, 'Abdulloh'),
            ('03.03.2026', '07:03', 'Naqt sotuvlar', 'Domboq', 5, 8500, 42500, 0, 'Abdulloh'),
            ('03.03.2026', '08:16', 'noilaxon', 'Domboq', 10, 8500, 0, 85000, 'Abdulloh'),
            
            # Skrinshot 2
            ('03.03.2026', '10:21', 'Xon choyxona', 'Mayda non', 20, 4000, 0, 80000, 'Abdulloh'),
            ('03.03.2026', '10:27', 'Xon choyxona', 'Doltali', 10, 8000, 0, 80000, 'Abdulloh'),
            ('03.03.2026', '10:28', 'saroy patir', 'Domboq', 10, 8500, 0, 85000, 'Abdulloh'),
            ('03.03.2026', '10:28', 'abboxon qirchin', 'Domboq', 6, 8500, 0, 51000, 'Abdulloh'),
            ('03.03.2026', '10:29', 'Xon choyxona', "Yog'siz", 20, 5000, 0, 100000, 'Abdulloh'),
            ('03.03.2026', '10:30', 'pungan baliq', 'Mayda non', 60, 4000, 240000, 0, 'Abdulloh'),
            ('03.03.2026', '10:44', 'xojamboy', 'Domboq', 5, 8500, 0, 42500, 'Abdulloh'),
            ('03.03.2026', '10:45', 'Sanjar patir', 'Sanjar non', 50, 10000, 0, 500000, 'Abdulloh'),
            
            # Skrinshot 3
            ('03.03.2026', '11:26', 'Volidam', 'Novvot non', 20, 10000, 0, 200000, 'Abdulloh'),
            ('03.03.2026', '11:29', 'rashid patir', 'Domboq', 6, 8500, 0, 51000, 'Abdulloh'),
            ('03.03.2026', '11:32', 'tomchi dangara', 'Doltali', 10, 8000, 0, 80000, 'Abdulloh'),
            ('03.03.2026', '11:33', 'tomchi dangara', 'Kokli non', 10, 8000, 0, 80000, 'Abdulloh'),
            ('03.03.2026', '11:33', 'benazir', 'Kokli non', 10, 8000, 0, 80000, 'Abdulloh'),
            ('03.03.2026', '11:33', 'benazir', 'Doltali', 10, 8000, 0, 80000, 'Abdulloh'),
            ('03.03.2026', '11:40', 'benazir', '700 gramli', 10, 8500, 0, 85000, 'Abdulloh'),
            ('03.03.2026', '11:52', 'Xadyalar', '700 gramli', 2, 8500, 17000, 0, 'Abdulloh'),
            
            # Skrinshot 4
            ('03.03.2026', '11:56', 'noilaxon', 'Novvot non', 20, 10000, 0, 200000, 'Abdulloh'),
            ('03.03.2026', '11:56', 'noilaxon', 'Domboq', 10, 8500, 0, 85000, 'Abdulloh'),
            ('03.03.2026', '13:32', 'rashid patir', '700 gramli', 4, 8500, 0, 34000, 'Abdulloh'),
            ('03.03.2026', '13:35', 'xojamboy', 'Achchiq', 10, 8000, 0, 80000, 'Abdulloh'),
            ('03.03.2026', '13:37', 'diyor patir', 'Achchiq', 6, 8000, 0, 48000, 'Abdulloh'),
            ('03.03.2026', '13:53', 'shirin patir', 'Achchiq', 20, 8000, 0, 160000, 'Abdulloh'),
            ('03.03.2026', '13:53', 'ishonch patir', 'Achchiq', 20, 8000, 0, 160000, 'Abdulloh'),
            ('03.03.2026', '14:31', 'Naqt sotuvlar', 'Domboq', 2, 8500, 17000, 0, 'Abdulloh'),
            
            # Skrinshot 5
            ('03.03.2026', '15:11', 'Doston', 'Domboq', 10, 8500, 85000, 0, 'Abdulloh'),
            ('03.03.2026', '15:55', 'noilaxon', 'Domboq', 10, 8500, 0, 85000, 'Abdulloh'),
            ('03.03.2026', '16:12', 'noilaxon', 'Domboq', 10, 8500, 0, 85000, 'Abdulloh'),
            ('03.03.2026', '16:13', 'Sanjar patir', 'Sanjar non', 84, 10000, 0, 840000, 'Abdulloh'),
            ('03.03.2026', '17:15', 'shirin patir', 'Domboq', 10, 8500, 0, 85000, 'Abdulloh'),
            ('03.03.2026', '17:29', 'noilaxon', 'Domboq', 10, 8500, 0, 85000, 'Abdulloh'),
            ('03.03.2026', '17:30', 'lazzat patir', 'Achchiq', 10, 8000, 80000, 0, 'Abdulloh'),
            ('03.03.2026', '17:33', 'xojamboy', 'Domboq', 5, 8500, 0, 42500, 'Abdulloh'),
            
            # Skrinshot 6
            ('03.03.2026', '17:36', 'lazzat patir2', 'Achchiq', 4, 8000, 0, 32000, 'Abdulloh'),
            ('03.03.2026', '17:36', 'lazzat patir2', '700 gramli', 4, 8500, 0, 34000, 'Abdulloh'),
            ('03.03.2026', '17:50', 'xusanboy patir', 'Achchiq', 10, 8000, 0, 80000, 'Abdulloh'),
            ('03.03.2026', '17:58', 'Volidam', 'Domboq', 10, 8500, 0, 85000, 'Abdulloh'),
            ('03.03.2026', '20:36', 'Volidam', 'Domboq', 10, 8500, 0, 85000, 'Abdulloh'),
            ('03.03.2026', '21:21', 'Volidam', 'Domboq', 10, 8509, 0, 85090, 'Abdulloh'),
            ('03.03.2026', '21:47', 'Naqt sotuvlar', 'Domboq', 5, 9000, 45000, 0, 'Abdulloh'),
            ('03.03.2026', '21:47', 'Naqt sotuvlar', 'Domboq', 6, 8500, 51000, 0, 'Abdulloh'),
            
            # Skrinshot 7
            ('03.03.2026', '21:48', 'Naqt sotuvlar', 'Sanjar non', 2, 10000, 20000, 0, 'Abdulloh'),
            ('03.03.2026', '21:49', 'benazir', 'Achchiq', 20, 8000, 0, 160000, 'Abdulloh'),
            ('03.03.2026', '21:49', 'tomchi dangara', 'Achchiq', 10, 8000, 0, 80000, 'Abdulloh'),
            ('03.03.2026', '21:53', 'Mirzo patir', 'Achchiq', 6, 8000, 0, 48000, 'Abdulloh'),
            ('03.03.2026', '21:54', 'Xadyalar', 'Achchiq', 1, 8000, 8000, 0, 'Abdulloh'),
            ('03.03.2026', '21:59', 'Xadyalar', 'Domboq', 1, 8500, 8500, 0, 'Abdulloh'),
            ('03.03.2026', '22:57', 'shirin patir', 'Domboq', 6, 8500, 0, 51000, 'Abdulloh'),
            ('03.03.2026', '23:01', 'Sanjar patir', 'Sanjar non', 40, 10000, 0, 400000, 'Abdulloh'),
            
            # Skrinshot 8
            ('03.03.2026', '23:03', 'Doston', 'Domboq', 10, 8500, 0, 85000, 'Abdulloh'),
            ('03.03.2026', '23:14', 'saroy patir', 'Achchiq', 10, 8000, 0, 80000, 'Abdulloh'),
        ]
        
        print("=" * 60)
        print("SOTUVLARNI QO'SHISH BOSHLANDI")
        print("=" * 60)
        
        for i, data in enumerate(sales_data, 1):
            try:
                add_sale(*data)
            except Exception as e:
                print(f"[XATO] Sotuv #{i}: {e}")
                db.session.rollback()
        
        print("=" * 60)
        print("TAYYOR! Barcha sotuvlar qo'shildi.")
        print("=" * 60)

def main():
    """Barcha ma'lumotlarni qo'shish"""
    with app.app_context():
        # 1. Avval mijozlarni qo'shish
        add_customers()
        
        # 2. Keyin sotuvlarni qo'shish
        add_all_sales()

def main_customers_only():
    """Faqat mijozlarni qo'shish"""
    with app.app_context():
        add_customers()

def main_sales_only():
    """Faqat sotuvlarni qo'shish (mijozlar mavjud bo'lsa)"""
    with app.app_context():
        add_all_sales()

if __name__ == '__main__':
    # Default: barchasini qo'shish
    main()
