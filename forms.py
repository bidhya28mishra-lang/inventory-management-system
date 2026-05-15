from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, FloatField, SelectField, PasswordField, TextAreaField
from wtforms.validators import DataRequired, NumberRange, Length

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])

class ProductForm(FlaskForm):
    name = StringField('Product Name', validators=[DataRequired()])
    category = StringField('Category')
    unit_price = FloatField('Unit Price', validators=[NumberRange(min=0)])
    low_stock_threshold = IntegerField('Low Stock Threshold', validators=[NumberRange(min=0)])
    supplier_id = SelectField('Supplier', coerce=int, validators=[DataRequired()])

class SupplierForm(FlaskForm):
    name = StringField('Supplier Name', validators=[DataRequired()])
    contact_person = StringField('Contact Person')
    phone = StringField('Phone')
    email = StringField('Email')

class StockForm(FlaskForm):
    product_id = SelectField('Product', coerce=int, validators=[DataRequired()])
    quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=1)])
    notes = TextAreaField('Notes')