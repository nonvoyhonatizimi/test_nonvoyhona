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
            
            db.session.commit()
            print("✅ Ustunlar muvaffaqiyatli qo'shildi (yoki allaqachon mavjud).")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Xatolik yuz berdi: {e}")
        
        print("Yangilash yakunlandi.")

if __name__ == '__main__':
    update_database()
