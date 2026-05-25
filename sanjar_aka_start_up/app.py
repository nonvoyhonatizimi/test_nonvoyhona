import os
from flask import Flask, render_template, request, redirect, url_for, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from sqlalchemy import func
from datetime import datetime

app = Flask(__name__)
# Yangi ma'lumotlar bazasi (Sotuvga tayyor sxema)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///premium_cars.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'commercial-grade-secret-key-2026'
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# --- ENTERPRISE DATABASE MODEL ---
class Car(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    brand = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    fuel_type = db.Column(db.String(20), nullable=False)
    transmission = db.Column(db.String(30), nullable=False, default="Avtomat")
    mileage = db.Column(db.Integer, nullable=False, default=0)
    color = db.Column(db.String(30), nullable=False, default="Oq")
    description = db.Column(db.Text, nullable=True)
    image = db.Column(db.String(100), nullable=False, default='default.jpg')
    views = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

# --- ROUTES ---

@app.route('/')
def index():
    brand = request.args.get('brand')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    transmission = request.args.get('transmission')
    fuel_type = request.args.get('fuel_type')

    query = Car.query

    if brand:
        query = query.filter(Car.brand.ilike(f'%{brand}%'))
    if min_price is not None:
        query = query.filter(Car.price >= min_price)
    if max_price is not None:
        query = query.filter(Car.price <= max_price)
    if transmission:
        query = query.filter(Car.transmission == transmission)
    if fuel_type:
        query = query.filter(Car.fuel_type == fuel_type)

    cars = query.order_by(Car.created_at.desc()).all()
    return render_template('index.html', cars=cars)

@app.route('/car/<int:car_id>')
def car_detail(car_id):
    car = Car.query.get_or_404(car_id)
    # Ko'rishlar sonini oshirish
    car.views += 1
    db.session.commit()
    
    # O'xshash mashinalar (Ayni shu markadagi boshqa mashinalar)
    similar_cars = Car.query.filter(Car.brand == car.brand, Car.id != car.id).limit(4).all()
    return render_template('car_detail.html', car=car, similar_cars=similar_cars)

@app.route('/admin')
def admin():
    cars = Car.query.order_by(Car.created_at.desc()).all()
    total_views = db.session.query(func.sum(Car.views)).scalar() or 0
    return render_template('admin.html', cars=cars, total_views=total_views)

@app.route('/admin/add', methods=['POST'])
def add_car():
    image_file = request.files.get('image')
    filename = 'default.jpg'
    if image_file and image_file.filename:
        filename = secure_filename(image_file.filename)
        image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    new_car = Car(
        brand=request.form.get('brand'),
        model=request.form.get('model'),
        year=request.form.get('year', type=int),
        price=request.form.get('price', type=float),
        fuel_type=request.form.get('fuel_type'),
        transmission=request.form.get('transmission'),
        mileage=request.form.get('mileage', type=int),
        color=request.form.get('color'),
        description=request.form.get('description'),
        image=filename
    )
    db.session.add(new_car)
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/admin/delete/<int:car_id>', methods=['POST'])
def delete_car(car_id):
    car = Car.query.get_or_404(car_id)
    if car.image != 'default.jpg':
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], car.image)
        if os.path.exists(image_path):
            os.remove(image_path)
    db.session.delete(car)
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/compare')
def compare():
    return render_template('compare.html')

@app.route('/api/cars')
def api_cars():
    ids = request.args.get('ids')
    if not ids:
        return jsonify([])
    car_ids = [int(i) for i in ids.split(',') if i.isdigit()]
    cars = Car.query.filter(Car.id.in_(car_ids)).all()
    car_list = [{
        'id': c.id, 'brand': c.brand, 'model': c.model, 
        'year': c.year, 'price': c.price, 'fuel_type': c.fuel_type,
        'transmission': c.transmission, 'mileage': c.mileage,
        'image': url_for('static', filename=f'uploads/{c.image}')
    } for c in cars]
    return jsonify(car_list)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
