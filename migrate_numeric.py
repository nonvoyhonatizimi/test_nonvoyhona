from app import app, db
from sqlalchemy import text

def update_numeric_columns():
    with app.app_context():
        print("Baza ma'lumotlari ustunlari turini yangilash boshlandi...")
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
        
        try:
            for query in queries:
                print(f"Bajarilmoqda: {query}")
                db.session.execute(text(query))
            
            db.session.commit()
            print("✅ Barcha maxsus ustunlar muvaffaqiyatli NUMERIC(18, 2) ga o'zgartirildi.")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Xatolik yuz berdi: {e}")
        
        print("Yangilash yakunlandi.")

if __name__ == '__main__':
    update_numeric_columns()
