from app import app, db
from models import User
from werkzeug.security import generate_password_hash

def hash_all_passwords():
    with app.app_context():
        users = User.query.all()
        count = 0
        for user in users:
            # Agar parol allaqachon hash qilingan bo'lsa (pbkdf2:sha256: bilan boshlanadi), tegmaymiz
            if not user.parol.startswith('pbkdf2:sha256:'):
                user.parol = generate_password_hash(user.parol)
                count += 1
        
        db.session.commit()
        print(f"[OK] {count} ta foydalanuvchi paroli xavfsiz holatga (hash) o'tkazildi.")

if __name__ == '__main__':
    hash_all_passwords()
