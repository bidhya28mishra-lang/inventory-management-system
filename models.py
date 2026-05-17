from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """Authorized users who can log into the system (FR1)."""
    __tablename__ = "users"

    id       = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email    = db.Column(db.String(120), unique=True, nullable=False)
    role     = db.Column(db.String(20), nullable=False, default="staff")  # admin | staff | manager
    password_hash = db.Column(db.String(256), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == "admin"

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


class Supplier(db.Model):
    """Supplier/vendor records managed by admin (FR7)."""
    __tablename__ = "suppliers"

    id           = db.Column(db.Integer, primary_key=True)
    name         = db.Column(db.String(120), nullable=False)
    contact_name = db.Column(db.String(120))
    phone        = db.Column(db.String(30))
    email        = db.Column(db.String(120))
    address      = db.Column(db.Text)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    products = db.relationship("Product", back_populates="supplier", lazy="dynamic")

    def __repr__(self):
        return f"<Supplier {self.name}>"


class Product(db.Model):
    """
    Product catalogue (FR2, FR3).
    Stores: name, category, quantity, unit_price, supplier, min_stock_level.
    """
    __tablename__ = "products"

    id              = db.Column(db.Integer, primary_key=True)
    name            = db.Column(db.String(150), nullable=False)
    category        = db.Column(db.String(80), nullable=False)
    quantity        = db.Column(db.Integer, nullable=False, default=0)
    unit_price      = db.Column(db.Float, nullable=False, default=0.0)
    min_stock_level = db.Column(db.Integer, nullable=False, default=5)
    supplier_id     = db.Column(db.Integer, db.ForeignKey("suppliers.id"), nullable=True)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at      = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    supplier = db.relationship("Supplier", back_populates="products")
    stock_movements = db.relationship("StockMovement", back_populates="product", lazy="dynamic",
                                      cascade="all, delete-orphan")

    @property
    def is_low_stock(self):
        return self.quantity <= self.min_stock_level

    def __repr__(self):
        return f"<Product {self.name} qty={self.quantity}>"


class StockMovement(db.Model):
    """
    Records every stock-in and stock-out transaction (FR4, FR5, FR6).
    The quantity on Product is updated atomically with each movement.
    """
    __tablename__ = "stock_movements"

    id              = db.Column(db.Integer, primary_key=True)
    product_id      = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    movement_type   = db.Column(db.String(10), nullable=False)   # "in" | "out"
    quantity        = db.Column(db.Integer, nullable=False)
    reference       = db.Column(db.String(100))                  # PO number, invoice, etc.
    note            = db.Column(db.Text)
    recorded_by_id  = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    product     = db.relationship("Product", back_populates="stock_movements")
    recorded_by = db.relationship("User")

    def __repr__(self):
        return f"<StockMovement {self.movement_type} {self.quantity} of product {self.product_id}>"
