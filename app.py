"""
Small Business Inventory Management System
ITS205 Software Engineering – Assessment B Prototype

Implements all 8 functional requirements from the SRS:
  FR1  – Secure user authentication & RBAC
  FR2  – Admin product CRUD
  FR3  – Product fields: name, category, quantity, unit_price, supplier, min_stock_level
  FR4  – Record stock-in transactions
  FR5  – Record stock-out transactions
  FR6  – Automatic quantity recalculation after every transaction
  FR7  – Admin supplier/vendor CRUD
  FR8  – Dashboard with low-stock alerts, stock history, inventory report
"""

import os
from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Supplier, Product, StockMovement
from forms import LoginForm, ProductForm, SupplierForm, StockInForm, StockOutForm

# ── Application factory ───────────────────────────────────────────────────────

def create_app():
    app = Flask(__name__)

    # Security & DB config  (override via environment variables in production)
    app.config["SECRET_KEY"]                   = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-prod")
    app.config["SQLALCHEMY_DATABASE_URI"]      = os.environ.get("DATABASE_URL", "sqlite:///database.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Initialise extensions
    db.init_app(app)

    login_manager = LoginManager(app)
    login_manager.login_view    = "login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # ── Seed admin account on first run ──────────────────────────────────────
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username="admin").first():
            admin = User(username="admin", email="admin@inventory.local", role="admin")
            admin.set_password("admin123")
            db.session.add(admin)

            staff = User(username="staff", email="staff@inventory.local", role="staff")
            staff.set_password("staff123")
            db.session.add(staff)

            db.session.commit()

    # ── Helper: admin-only guard ──────────────────────────────────────────────
    def admin_required(f):
        from functools import wraps
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.is_authenticated or not current_user.is_admin():
                abort(403)
            return f(*args, **kwargs)
        return decorated

    # =========================================================================
    # FR1 – Authentication
    # =========================================================================

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()
            if user and user.check_password(form.password.data):
                login_user(user)
                flash(f"Welcome back, {user.username}!", "success")
                next_page = request.args.get("next")
                return redirect(next_page or url_for("dashboard"))
            flash("Invalid username or password.", "danger")
        return render_template("login.html", form=form)

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("You have been logged out.", "info")
        return redirect(url_for("login"))

    # =========================================================================
    # FR8 – Dashboard (low-stock alerts, summary)
    # =========================================================================

    @app.route("/")
    @login_required
    def dashboard():
        total_products  = Product.query.count()
        total_suppliers = Supplier.query.count()
        total_movements = StockMovement.query.count()

        low_stock_items = Product.query.filter(
            Product.quantity <= Product.min_stock_level
        ).order_by(Product.quantity.asc()).all()

        recent_movements = (StockMovement.query
                            .order_by(StockMovement.created_at.desc())
                            .limit(10)
                            .all())

        return render_template(
            "index.html",
            total_products=total_products,
            total_suppliers=total_suppliers,
            total_movements=total_movements,
            low_stock_items=low_stock_items,
            recent_movements=recent_movements,
        )

    # =========================================================================
    # FR2, FR3 – Product management
    # =========================================================================

    @app.route("/products")
    @login_required
    def products():
        search = request.args.get("search", "").strip()
        query  = Product.query
        if search:
            query = query.filter(
                Product.name.ilike(f"%{search}%") |
                Product.category.ilike(f"%{search}%")
            )
        all_products = query.order_by(Product.name).all()
        form = ProductForm()
        suppliers = Supplier.query.order_by(Supplier.name).all()
        form.supplier_id.choices = [(0, "— None —")] + [(s.id, s.name) for s in suppliers]
        return render_template("products.html", products=all_products, search=search, form=form)

    @app.route("/products/add", methods=["GET", "POST"])
    @login_required
    def add_product():
        if not current_user.is_admin():
            abort(403)
        form = ProductForm()
        suppliers = Supplier.query.order_by(Supplier.name).all()
        form.supplier_id.choices = [(0, "— None —")] + [(s.id, s.name) for s in suppliers]

        if form.validate_on_submit():
            supplier_id = form.supplier_id.data if form.supplier_id.data != 0 else None
            product = Product(
                name            = form.name.data.strip(),
                category        = form.category.data.strip(),
                quantity        = form.quantity.data,
                unit_price      = form.unit_price.data,
                min_stock_level = form.min_stock_level.data,
                supplier_id     = supplier_id,
            )
            db.session.add(product)
            db.session.commit()
            flash(f"Product '{product.name}' added successfully.", "success")
            return redirect(url_for("products"))

        return render_template("products.html",
                               form=form,
                               products=Product.query.order_by(Product.name).all(),
                               show_form=True,
                               search="")

    @app.route("/products/edit/<int:product_id>", methods=["GET", "POST"])
    @login_required
    def edit_product(product_id):
        if not current_user.is_admin():
            abort(403)
        product   = Product.query.get_or_404(product_id)
        suppliers = Supplier.query.order_by(Supplier.name).all()
        form      = ProductForm(obj=product)
        form.supplier_id.choices = [(0, "— None —")] + [(s.id, s.name) for s in suppliers]

        if form.validate_on_submit():
            product.name            = form.name.data.strip()
            product.category        = form.category.data.strip()
            product.quantity        = form.quantity.data
            product.unit_price      = form.unit_price.data
            product.min_stock_level = form.min_stock_level.data
            product.supplier_id     = form.supplier_id.data if form.supplier_id.data != 0 else None
            db.session.commit()
            flash(f"Product '{product.name}' updated.", "success")
            return redirect(url_for("products"))

        form.supplier_id.data = product.supplier_id or 0
        return render_template("products.html",
                               form=form,
                               products=Product.query.order_by(Product.name).all(),
                               show_form=True,
                               edit_product=product,
                               search="")

    @app.route("/products/delete/<int:product_id>", methods=["POST"])
    @login_required
    def delete_product(product_id):
        if not current_user.is_admin():
            abort(403)
        product = Product.query.get_or_404(product_id)
        db.session.delete(product)
        db.session.commit()
        flash(f"Product '{product.name}' deleted.", "warning")
        return redirect(url_for("products"))

    # =========================================================================
    # FR7 – Supplier / vendor management
    # =========================================================================

    @app.route("/suppliers")
    @login_required
    def suppliers():
        all_suppliers = Supplier.query.order_by(Supplier.name).all()
        form = SupplierForm()   # always passed so csrf_token is available in template
        return render_template("suppliers.html", suppliers=all_suppliers, form=form)

    @app.route("/suppliers/add", methods=["GET", "POST"])
    @login_required
    def add_supplier():
        if not current_user.is_admin():
            abort(403)
        form = SupplierForm()
        if form.validate_on_submit():
            supplier = Supplier(
                name         = form.name.data.strip(),
                contact_name = form.contact_name.data.strip() if form.contact_name.data else None,
                phone        = form.phone.data.strip() if form.phone.data else None,
                email        = form.email.data.strip() if form.email.data else None,
                address      = form.address.data.strip() if form.address.data else None,
            )
            db.session.add(supplier)
            db.session.commit()
            flash(f"Supplier '{supplier.name}' added successfully.", "success")
            return redirect(url_for("suppliers"))
        return render_template("suppliers.html",
                               suppliers=Supplier.query.order_by(Supplier.name).all(),
                               form=form,
                               show_form=True)

    @app.route("/suppliers/edit/<int:supplier_id>", methods=["GET", "POST"])
    @login_required
    def edit_supplier(supplier_id):
        if not current_user.is_admin():
            abort(403)
        supplier = Supplier.query.get_or_404(supplier_id)
        form     = SupplierForm(obj=supplier)
        if form.validate_on_submit():
            supplier.name         = form.name.data.strip()
            supplier.contact_name = form.contact_name.data.strip() if form.contact_name.data else None
            supplier.phone        = form.phone.data.strip() if form.phone.data else None
            supplier.email        = form.email.data.strip() if form.email.data else None
            supplier.address      = form.address.data.strip() if form.address.data else None
            db.session.commit()
            flash(f"Supplier '{supplier.name}' updated.", "success")
            return redirect(url_for("suppliers"))
        return render_template("suppliers.html",
                               suppliers=Supplier.query.order_by(Supplier.name).all(),
                               form=form,
                               show_form=True,
                               edit_supplier=supplier)

    @app.route("/suppliers/delete/<int:supplier_id>", methods=["POST"])
    @login_required
    def delete_supplier(supplier_id):
        if not current_user.is_admin():
            abort(403)
        supplier = Supplier.query.get_or_404(supplier_id)
        db.session.delete(supplier)
        db.session.commit()
        flash(f"Supplier '{supplier.name}' deleted.", "warning")
        return redirect(url_for("suppliers"))

    # =========================================================================
    # FR4 – Stock In  |  FR6 – Auto quantity recalculation
    # =========================================================================

    @app.route("/stock-in", methods=["GET", "POST"])
    @login_required
    def stock_in():
        form = StockInForm()
        form.product_id.choices = [(p.id, f"{p.name} (qty: {p.quantity})")
                                   for p in Product.query.order_by(Product.name).all()]
        if form.validate_on_submit():
            product = Product.query.get_or_404(form.product_id.data)
            movement = StockMovement(
                product_id    = product.id,
                movement_type = "in",
                quantity      = form.quantity.data,
                reference     = form.reference.data.strip() if form.reference.data else None,
                note          = form.note.data.strip() if form.note.data else None,
                recorded_by_id = current_user.id,
            )
            # FR6: auto-update quantity
            product.quantity += form.quantity.data
            db.session.add(movement)
            db.session.commit()
            flash(f"Stock-in recorded: +{movement.quantity} × {product.name}. "
                  f"New qty: {product.quantity}.", "success")
            return redirect(url_for("stock_in"))
        return render_template("stock_in.html", form=form)

    # =========================================================================
    # FR5 – Stock Out  |  FR6 – Auto quantity recalculation
    # =========================================================================

    @app.route("/stock-out", methods=["GET", "POST"])
    @login_required
    def stock_out():
        form = StockOutForm()
        form.product_id.choices = [(p.id, f"{p.name} (qty: {p.quantity})")
                                   for p in Product.query.order_by(Product.name).all()]
        if form.validate_on_submit():
            product = Product.query.get_or_404(form.product_id.data)
            if form.quantity.data > product.quantity:
                flash(f"Insufficient stock. Only {product.quantity} unit(s) available.", "danger")
                return render_template("stock_out.html", form=form)
            movement = StockMovement(
                product_id    = product.id,
                movement_type = "out",
                quantity      = form.quantity.data,
                reference     = form.reference.data.strip() if form.reference.data else None,
                note          = form.note.data.strip() if form.note.data else None,
                recorded_by_id = current_user.id,
            )
            # FR6: auto-update quantity
            product.quantity -= form.quantity.data
            db.session.add(movement)
            db.session.commit()
            flash(f"Stock-out recorded: −{movement.quantity} × {product.name}. "
                  f"New qty: {product.quantity}.", "success")
            return redirect(url_for("stock_out"))
        return render_template("stock_out.html", form=form)

    # =========================================================================
    # FR8 – Stock history
    # =========================================================================

    @app.route("/stock-history")
    @login_required
    def stock_history():
        product_id = request.args.get("product_id", type=int)
        page       = request.args.get("page", 1, type=int)

        query = StockMovement.query
        if product_id:
            query = query.filter_by(product_id=product_id)

        movements = (query
                     .order_by(StockMovement.created_at.desc())
                     .paginate(page=page, per_page=20, error_out=False))

        products = Product.query.order_by(Product.name).all()
        return render_template("stock_history.html",
                               movements=movements,
                               products=products,
                               selected_product_id=product_id)

    # =========================================================================
    # FR8 – Inventory report
    # =========================================================================

    @app.route("/report")
    @login_required
    def report():
        products = Product.query.order_by(Product.category, Product.name).all()

        # Summary stats
        total_items      = sum(p.quantity for p in products)
        total_value      = sum(p.quantity * p.unit_price for p in products)
        low_stock_count  = sum(1 for p in products if p.is_low_stock)
        out_of_stock     = sum(1 for p in products if p.quantity == 0)

        # Category breakdown
        categories = {}
        for p in products:
            categories.setdefault(p.category, {"count": 0, "qty": 0, "value": 0.0})
            categories[p.category]["count"] += 1
            categories[p.category]["qty"]   += p.quantity
            categories[p.category]["value"] += p.quantity * p.unit_price

        return render_template(
            "report.html",
            products=products,
            total_items=total_items,
            total_value=total_value,
            low_stock_count=low_stock_count,
            out_of_stock=out_of_stock,
            categories=categories,
        )

    # ── Error pages ───────────────────────────────────────────────────────────

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)