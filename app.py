from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Product, Supplier, StockTransaction
from forms import LoginForm, ProductForm, SupplierForm, StockForm
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------- Create tables and default admin ----------
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', 
                     password=generate_password_hash('admin123'), 
                     role='admin')
        db.session.add(admin)
        # also create a staff user for testing
        staff = User(username='staff', 
                     password=generate_password_hash('staff123'), 
                     role='staff')
        db.session.add(staff)
        db.session.commit()

# ---------- Routes ----------
@app.route('/')
@login_required
def index():
    # Dashboard: show low stock products
    low_stock_products = Product.query.filter(Product.quantity <= Product.low_stock_threshold).all()
    total_products = Product.query.count()
    total_suppliers = Supplier.query.count()
    recent_transactions = StockTransaction.query.order_by(StockTransaction.timestamp.desc()).limit(10).all()
    return render_template('index.html', 
                           low_stock=low_stock_products,
                           total_products=total_products,
                           total_suppliers=total_suppliers,
                           recent=recent_transactions)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid username or password')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ---------- Product Management (Admin only) ----------
@app.route('/products', methods=['GET', 'POST'])
@login_required
def products():
    if current_user.role != 'admin':
        flash('Admin access required')
        return redirect(url_for('index'))
    form = ProductForm()
    # populate supplier choices
    form.supplier_id.choices = [(s.id, s.name) for s in Supplier.query.all()]
    if form.validate_on_submit():
        product = Product(
            name=form.name.data,
            category=form.category.data,
            unit_price=form.unit_price.data,
            low_stock_threshold=form.low_stock_threshold.data,
            supplier_id=form.supplier_id.data,
            quantity=0  # initial quantity
        )
        db.session.add(product)
        db.session.commit()
        flash('Product added successfully')
        return redirect(url_for('products'))
    all_products = Product.query.all()
    return render_template('products.html', products=all_products, form=form)

@app.route('/product/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_product(id):
    if current_user.role != 'admin':
        flash('Admin access required')
        return redirect(url_for('index'))
    product = Product.query.get_or_404(id)
    form = ProductForm(obj=product)
    form.supplier_id.choices = [(s.id, s.name) for s in Supplier.query.all()]
    if form.validate_on_submit():
        product.name = form.name.data
        product.category = form.category.data
        product.unit_price = form.unit_price.data
        product.low_stock_threshold = form.low_stock_threshold.data
        product.supplier_id = form.supplier_id.data
        db.session.commit()
        flash('Product updated')
        return redirect(url_for('products'))
    return render_template('product_edit.html', form=form, product=product)

# ---------- Supplier Management (Admin only) ----------
@app.route('/suppliers', methods=['GET', 'POST'])
@login_required
def suppliers():
    if current_user.role != 'admin':
        flash('Admin access required')
        return redirect(url_for('index'))
    form = SupplierForm()
    if form.validate_on_submit():
        supplier = Supplier(
            name=form.name.data,
            contact_person=form.contact_person.data,
            phone=form.phone.data,
            email=form.email.data
        )
        db.session.add(supplier)
        db.session.commit()
        flash('Supplier added')
        return redirect(url_for('suppliers'))
    all_suppliers = Supplier.query.all()
    return render_template('suppliers.html', suppliers=all_suppliers, form=form)

# ---------- Stock In / Stock Out (both roles) ----------
@app.route('/stock/in', methods=['GET', 'POST'])
@login_required
def stock_in():
    form = StockForm()
    form.product_id.choices = [(p.id, f"{p.name} (current: {p.quantity})") for p in Product.query.all()]
    if form.validate_on_submit():
        product = Product.query.get(form.product_id.data)
        qty = form.quantity.data
        product.quantity += qty
        transaction = StockTransaction(
            product_id=product.id,
            transaction_type='IN',
            quantity=qty,
            user_id=current_user.id,
            notes=form.notes.data
        )
        db.session.add(transaction)
        db.session.commit()
        flash(f'Added {qty} units of {product.name}')
        return redirect(url_for('index'))
    return render_template('stock_in.html', form=form)

@app.route('/stock/out', methods=['GET', 'POST'])
@login_required
def stock_out():
    form = StockForm()
    form.product_id.choices = [(p.id, f"{p.name} (available: {p.quantity})") for p in Product.query.all()]
    if form.validate_on_submit():
        product = Product.query.get(form.product_id.data)
        qty = form.quantity.data
        if qty > product.quantity:
            flash(f'Not enough stock! Available: {product.quantity}')
            return redirect(url_for('stock_out'))
        product.quantity -= qty
        transaction = StockTransaction(
            product_id=product.id,
            transaction_type='OUT',
            quantity=qty,
            user_id=current_user.id,
            notes=form.notes.data
        )
        db.session.add(transaction)
        db.session.commit()
        flash(f'Removed {qty} units of {product.name}')
        return redirect(url_for('index'))
    return render_template('stock_out.html', form=form)

# ---------- Stock History & Report ----------
@app.route('/history')
@login_required
def stock_history():
    transactions = StockTransaction.query.order_by(StockTransaction.timestamp.desc()).all()
    return render_template('stock_history.html', transactions=transactions)

@app.context_processor
def inject_now():
    from datetime import datetime
    return {'now': datetime.now}

@app.context_processor
def inject_now():
    from datetime import datetime
    return {'now': datetime.now}

@app.context_processor
def inject_now():
    from datetime import datetime
    return {'now': datetime.now}

@app.route('/report')
@login_required
def report():
    if current_user.role != 'admin':
        flash('Admin access required')
        return redirect(url_for('index'))
    products = Product.query.all()
    return render_template('report.html', products=products)

if __name__ == '__main__':
    app.run(debug=True)