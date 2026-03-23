from app import app, db
from sqlalchemy import text

def update_database():
    with app.app_context():
        print("Baza ma'lumotlarini yangilash boshlandi...")
        try:
            # Foydalanuvchilar jadvaliga customer_id ustunini qo'shish
            db.session.execute(text("ALTER TABLE foydalanuvchilar ADD COLUMN IF NOT EXISTS customer_id INTEGER REFERENCES mijozlar(id)"))
            
            # Kassa jadvaliga yangi ustunlar qo'shish
            db.session.execute(text("ALTER TABLE kassa ADD COLUMN IF NOT EXISTS smena INTEGER DEFAULT 1"))
            db.session.execute(text("ALTER TABLE kassa ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES foydalanuvchilar(id)"))
            
            # Haydovchi to'lovlari jadvaliga collector_id qo'shish
            db.session.execute(text("ALTER TABLE haydovchi_tolovlari ADD COLUMN IF NOT EXISTS collector_id INTEGER REFERENCES xodimlar(id)"))

            # Barcha pul miqdorini ifodalovchi ustunlarni NUMERIC(10,2) dan NUMERIC(18,2) ga o'zgartirish (numeric field overflow xatosini oldini olish uchun)
            queries = [
                "ALTER TABLE xodimlar ALTER COLUMN oylik TYPE NUMERIC(18,2);",
                "ALTER TABLE xodimlar ALTER COLUMN ish_haqqi_stavka TYPE NUMERIC(18,2);",
                "ALTER TABLE mijozlar ALTER COLUMN kredit_limit TYPE NUMERIC(18,2);",
                "ALTER TABLE mijozlar ALTER COLUMN jami_qarz TYPE NUMERIC(18,2);",
                "ALTER TABLE non_turlari ALTER COLUMN narx TYPE NUMERIC(18,2);",
                "ALTER TABLE sotuvlar ALTER COLUMN narx_dona TYPE NUMERIC(18,2);",
                "ALTER TABLE sotuvlar ALTER COLUMN jami_summa TYPE NUMERIC(18,2);",
                "ALTER TABLE sotuvlar ALTER COLUMN tolandi TYPE NUMERIC(18,2);",
                "ALTER TABLE sotuvlar ALTER COLUMN qoldiq_qarz TYPE NUMERIC(18,2);",
                "ALTER TABLE xarajatlar ALTER COLUMN summa TYPE NUMERIC(18,2);",
                "ALTER TABLE kassa ALTER COLUMN kirim TYPE NUMERIC(18,2);",
                "ALTER TABLE kassa ALTER COLUMN chiqim TYPE NUMERIC(18,2);",
                "ALTER TABLE kassa ALTER COLUMN balans TYPE NUMERIC(18,2);",
                "ALTER TABLE haydovchi_tolovlari ALTER COLUMN summa TYPE NUMERIC(18,2);",
                "ALTER TABLE ish_haqqi_tolov ALTER COLUMN summa TYPE NUMERIC(18,2);"
            ]
            
            for query in queries:
                try:
                    db.session.execute(text(query))
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    print(f"Bunday jadval/ustun bo'lmasligi mumkin, e'tibor bermaymiz: {query}")
            
            print("✅ Ustunlar muvaffaqiyatli qo'shildi (yoki allaqachon mavjud).")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Xatolik yuz berdi: {e}")
        
        print("Yangilash yakunlandi.")

if __name__ == '__main__':
    update_database()
