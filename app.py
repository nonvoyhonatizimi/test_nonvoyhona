import os
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate
from models import db, User, Log, Sale, BreadMaking, Customer, Employee
from sqlalchemy import func
from datetime import datetime

# Load environment variables from .env file for local development
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'nonvoyhona-secret-key-123')

# Database configuration - uses DATABASE_URL environment variable
# Render Internal Database (PostgreSQL with pg8000 driver)
DATABASE_URL = os.environ.get('DATABASE_URL', 
    'postgresql+pg8000://nonvoyhonatizimi_user:JIPK1bBsLGGiQI04QfCG70cVbPT2VvDb@dpg-d6juhpntskes73b5drl0-a/nonvoyhonatizimi')

# Fix Render's postgres:// to postgresql+pg8000://
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql+pg8000://', 1)
elif DATABASE_URL.startswith('postgresql://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+pg8000://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def log_action(harakat, maumot=""):
    log = Log(
        foydalanuvchi=current_user.login if current_user.is_authenticated else "tizim",
        harakat=harakat,
        maumot=maumot
    )
    db.session.add(log)
    db.session.commit()

@app.route('/')
@login_required
def index():
    # Redirect based on role/lavozim
    if current_user.rol != 'admin' and current_user.employee:
        lavozim = current_user.employee.lavozim.lower() if current_user.employee.lavozim else ''
        if 'xamir' in lavozim:
            return redirect(url_for('production.list_dough'))
        elif 'yasovchi' in lavozim or 'yashovchi' in lavozim:
            return redirect(url_for('production.list_bread'))
        elif 'tandir' in lavozim:
            return redirect(url_for('production.list_oven'))
        elif 'haydovchi' in lavozim:
            return redirect(url_for('sales.list_sales'))
    
    # If it is a customer
    if current_user.rol == 'customer' or current_user.customer_id:
        return redirect(url_for('customer_portal.dashboard'))
    
    # For admin and operator, redirect to Daily Sales as requested
    if current_user.rol == 'admin' or (current_user.employee and current_user.employee.lavozim == 'Operator'):
        return redirect(url_for('reports.daily_sales'))

    today = datetime.now().date()
    
    # Stats (Keep as fallback or for other roles if any)
    daily_sales = db.session.query(func.sum(Sale.tolandi)).filter(Sale.sana == today).scalar() or 0
    daily_production = db.session.query(func.sum(BreadMaking.sof_non)).filter(BreadMaking.sana == today).scalar() or 0
    total_debt = db.session.query(func.sum(Customer.jami_qarz)).scalar() or 0
    employee_count = Employee.query.filter_by(status='faol').count()
    
    recent_sales = Sale.query.order_by(Sale.id.desc()).limit(5).all()
    recent_logs = Log.query.order_by(Log.id.desc()).limit(10).all()
    
    return render_template('dashboard.html', 
                           daily_sales=daily_sales, 
                           daily_production=daily_production,
                           total_debt=total_debt,
                           employee_count=employee_count,
                           recent_sales=recent_sales,
                           recent_logs=recent_logs)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(login=username).first()
        
        if user and user.parol == password: # In real app use hash
            login_user(user)
            log_action("Kirish", "Foydalanuvchi tizimga kirdi")
            return redirect(url_for('index'))
        else:
            flash('Login yoki parol xato!')
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    log_action("Chiqish", "Foydalanuvchi tizimdan chiqdi")
    logout_user()
    return redirect(url_for('login'))

# Import and register blueprints for other modules
from routes.employees import employees_bp
from routes.customers import customers_bp
from routes.production import production_bp
from routes.sales import sales_bp
from routes.finance import finance_bp
from routes.reports import reports_bp
from routes.bread_types import bread_types_bp
from routes.payroll import payroll_bp
from routes.customer_portal import customer_portal_bp
from routes.ai_assistant import ai_assistant_bp
from routes.comments import comments_bp

app.register_blueprint(employees_bp)
app.register_blueprint(customers_bp)
app.register_blueprint(production_bp)
app.register_blueprint(sales_bp)
app.register_blueprint(finance_bp)
app.register_blueprint(reports_bp)
app.register_blueprint(bread_types_bp)
app.register_blueprint(payroll_bp)
app.register_blueprint(customer_portal_bp)
app.register_blueprint(ai_assistant_bp)
app.register_blueprint(comments_bp)

@app.route('/sw.js')
def serve_sw():
    return app.send_static_file('sw.js')

@app.route('/manifest.json')
def serve_manifest():
    return app.send_static_file('manifest.json')

# Create database tables on startup
def init_db():
    with app.app_context():
        # First, try to add missing columns manualy (Migration)
        from sqlalchemy import text
        try:
            db.session.execute(text("ALTER TABLE foydalanuvchilar ADD COLUMN IF NOT EXISTS customer_id INTEGER REFERENCES mijozlar(id)"))
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Migration backup: {e}")

        db.create_all()
        
        # Create default admin if not exists
        if not User.query.filter_by(login='rovshanbek').first():
            admin = User(login='rovshanbek', parol='admin0257', rol='admin', ism='Rovshanbek')
            db.session.add(admin)
            db.session.commit()
        
        # Add all customers from Telegram groups if not exist
        customers_to_add = [
            "volidam", "doston", "sanjar patir", "noilaxon", "ziyo patir",
            "turonboy", "shirin patir", "xojamboy", "azizbek patir", "akmal patir",
            "shukurullo patir", "abduqahor patir", "milyon patir", "ramshit patir",
            "xusanboy patir", "ishonch patir", "soxib patir", "sardor patir",
            "lazzat patir", "paxlavon patir", "tanxo patir", "alisher patir",
            "asil patir", "sarvar patir", "javohir patir", "kozim patir",
            "klara opa", "rashid patir", "nodir patir", "rokiya patir",
            "xayotjon", "shaxboz patir", "osiyo patir", "ozbegim",
            "sadiya patir", "ifor patir", "diyor patir", "lazzat patir2",
            "mamura qirchin", "dilafruz qirchin", "saroy patir", "abbosxon qirchin",
            "nasiba qirchin", "abdulatif", "pungan baliq", "tomchi dangara", "benazir"
        ]
        
        for customer_name in customers_to_add:
            if not Customer.query.filter_by(nomi=customer_name).first():
                new_customer = Customer(
                    nomi=customer_name,
                    turi='dokon',
                    telefon='',
                    manzil='',
                    kredit_limit=0,
                    jami_qarz=0
                )
                db.session.add(new_customer)
        
        db.session.commit()
        print(f"[OK] {len(customers_to_add)} ta mijoz bazaga qo'shildi")

# Initialize database on startup
init_db()

# Production ready - v1.0
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Create default admin if not exists
        if not User.query.filter_by(login='rovshanbek').first():
            admin = User(login='rovshanbek', parol='admin0257', rol='admin', ism='Rovshanbek')
            db.session.add(admin)
            db.session.commit()
        
        # Add all customers from Telegram groups if not exist
        customers_to_add = [
            "volidam", "doston", "sanjar patir", "noilaxon", "ziyo patir",
            "turonboy", "shirin patir", "xojamboy", "azizbek patir", "akmal patir",
            "shukurullo patir", "abduqahor patir", "milyon patir", "ramshit patir",
            "xusanboy patir", "ishonch patir", "soxib patir", "sardor patir",
            "lazzat patir", "paxlavon patir", "tanxo patir", "alisher patir",
            "asil patir", "sarvar patir", "javohir patir", "kozim patir",
            "klara opa", "rashid patir", "nodir patir", "rokiya patir",
            "xayotjon", "shaxboz patir", "osiyo patir", "ozbegim",
            "sadiya patir", "ifor patir", "diyor patir", "lazzat patir2",
            "mamura qirchin", "dilafruz qirchin", "saroy patir", "abbosxon qirchin",
            "nasiba qirchin", "abdulatif", "pungan baliq", "tomchi dangara", "benazir"
        ]
        
        for customer_name in customers_to_add:
            if not Customer.query.filter_by(nomi=customer_name).first():
                new_customer = Customer(
                    nomi=customer_name,
                    turi='dokon',
                    telefon='',
                    manzil='',
                    kredit_limit=0,
                    jami_qarz=0
                )
                db.session.add(new_customer)
        
        db.session.commit()
        print(f"[OK] {len(customers_to_add)} ta mijoz bazaga qo'shildi")
    
    # Get port from environment variable (Render uses PORT)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
