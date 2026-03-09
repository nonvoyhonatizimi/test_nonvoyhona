from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, CustomerComment, Customer, User
from sqlalchemy import desc

comments_bp = Blueprint('comments', __name__, url_prefix='/comments')

@comments_bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    if current_user.rol != 'admin':
        flash("Bu sahifa faqat adminlar uchun!", "error")
        return redirect(url_for('index'))
    
    # POST bo'lsa (yangi izoh yuborilsa)
    if request.method == 'POST':
        customer_id = request.form.get('customer_id')
        matn = request.form.get('matn')
        
        if customer_id and matn and matn.strip():
            comment = CustomerComment(
                customer_id=customer_id,
                admin_id=current_user.id,
                is_from_admin=True,
                matn=matn.strip()
            )
            db.session.add(comment)
            db.session.commit()
            flash("Izoh muvaffaqiyatli yuborildi", "success")
        else:
            flash("Mijoz va izoh matni kiritilishi shart", "error")
            
        return redirect(url_for('comments.index', customer_id=customer_id))
        
    # GET bo'lsa
    selected_customer_id = request.args.get('customer_id', type=int)
    
    # Mijozlar ro'yxatini olish (Alfavit bo'yicha)
    customers = Customer.query.order_by(Customer.nomi).all()
    
    chat_history = []
    selected_customer = None
    
    if selected_customer_id:
        selected_customer = Customer.query.get(selected_customer_id)
        if selected_customer:
            # Izohlarni olish (eng eskisi tepadadan boshlanib yangisi pastga tushishi uchun ascending, 
            # Lekin descending qilib eng yangilarini chiqarish ham mumkin, displayda hal qilamiz)
            chat_history = CustomerComment.query.filter_by(customer_id=selected_customer_id)\
                            .order_by(CustomerComment.created_at.asc()).all()
                            
            # Adminga kelgan (mijoz yozgan) o'qilmagan xabarlarni o'qilgan deb belgilash
            unread_comments = CustomerComment.query.filter_by(
                customer_id=selected_customer_id, 
                is_from_admin=False, 
                is_read=False
            ).all()
            if unread_comments:
                for c in unread_comments:
                    c.is_read = True
                db.session.commit()
                
    # O'qilmagan xabarlar sonini hisoblab chiqish (faqat yon tomondagi mijozlar ruyxati uchun yordamchi bo'lishi mumkin)
    # Hozircha oddiy select qilinadi.
    
    return render_template('comments/index.html', 
                           customers=customers, 
                           selected_customer=selected_customer, 
                           chat_history=chat_history)

@comments_bp.route('/delete/<int:id>')
@login_required
def delete_comment(id):
    if current_user.rol != 'admin':
        flash("Ruxsat berilmagan", "error")
        return redirect(url_for('index'))
    
    comment = CustomerComment.query.get_or_404(id)
    customer_id = comment.customer_id
    
    db.session.delete(comment)
    db.session.commit()
    flash("Xabar o'chirildi", "success")
    
    return redirect(url_for('comments.index', customer_id=customer_id))
