from flask_wtf import FlaskForm
from wtforms import (StringField, PasswordField, SelectField, IntegerField,
                     FloatField, TextAreaField, SubmitField, HiddenField)
from wtforms.validators import DataRequired, Email, Optional, NumberRange, Length


# ── Authentication ────────────────────────────────────────────────────────────

class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=2, max=80)])
    password = PasswordField("Password", validators=[DataRequired()])
    submit   = SubmitField("Log In")


# ── Product Management (FR2, FR3) ─────────────────────────────────────────────

class ProductForm(FlaskForm):
    name            = StringField("Product Name",   validators=[DataRequired(), Length(max=150)])
    category        = StringField("Category",       validators=[DataRequired(), Length(max=80)])
    quantity        = IntegerField("Initial Quantity", validators=[DataRequired(), NumberRange(min=0)])
    unit_price      = FloatField("Unit Price ($)",   validators=[DataRequired(), NumberRange(min=0)])
    min_stock_level = IntegerField("Min Stock Level", validators=[DataRequired(), NumberRange(min=0)])
    supplier_id     = SelectField("Supplier", coerce=int, validators=[Optional()])
    submit          = SubmitField("Save Product")


# ── Supplier / Vendor Management (FR7) ────────────────────────────────────────

class SupplierForm(FlaskForm):
    name         = StringField("Supplier Name",  validators=[DataRequired(), Length(max=120)])
    contact_name = StringField("Contact Person", validators=[Optional(), Length(max=120)])
    phone        = StringField("Phone",          validators=[Optional(), Length(max=30)])
    email        = StringField("Email",          validators=[Optional(), Email(), Length(max=120)])
    address      = TextAreaField("Address",      validators=[Optional()])
    submit       = SubmitField("Save Supplier")


# ── Stock-In (FR4) ────────────────────────────────────────────────────────────

class StockInForm(FlaskForm):
    product_id = SelectField("Product",   coerce=int, validators=[DataRequired()])
    quantity   = IntegerField("Quantity", validators=[DataRequired(), NumberRange(min=1)])
    reference  = StringField("Reference / PO #", validators=[Optional(), Length(max=100)])
    note       = TextAreaField("Note",           validators=[Optional()])
    submit     = SubmitField("Record Stock In")


# ── Stock-Out (FR5) ───────────────────────────────────────────────────────────

class StockOutForm(FlaskForm):
    product_id = SelectField("Product",   coerce=int, validators=[DataRequired()])
    quantity   = IntegerField("Quantity", validators=[DataRequired(), NumberRange(min=1)])
    reference  = StringField("Reference / Invoice #", validators=[Optional(), Length(max=100)])
    note       = TextAreaField("Note",                validators=[Optional()])
    submit     = SubmitField("Record Stock Out")
