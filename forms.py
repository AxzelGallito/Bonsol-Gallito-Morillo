from flask_wtf import FlaskForm
from wtforms import (
    StringField, IntegerField, FloatField, PasswordField,
    EmailField, BooleanField, SubmitField, SelectField
)
from wtforms.validators import DataRequired, Length, NumberRange
from flask_wtf.file import FileField
from wtforms import SubmitField

# -------------------- AUTH FORMS --------------------

class SignUpForm(FlaskForm):
    email = EmailField('Email', validators=[DataRequired()])
    username = StringField('Username', validators=[DataRequired(), Length(min=2)])
    address = StringField('Address', validators=[DataRequired(), Length(min=4)])
    password1 = PasswordField('Enter Your Password', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Confirm Your Password', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Sign Up')


class LoginForm(FlaskForm):
    email = EmailField('Email', validators=[DataRequired()])
    password = PasswordField('Enter Your Password', validators=[DataRequired()])
    submit = SubmitField('Log in')


class PasswordChangeForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired(), Length(min=6)])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    confirm_new_password = PasswordField('Confirm New Password', validators=[DataRequired(), Length(min=6)])
    change_password = SubmitField('Change Password')


# -------------------- MERGED SHOP ITEMS FORM --------------------

class ShopItemsForm(FlaskForm):
    product_name = StringField('Product Name', validators=[DataRequired()])
    current_price = FloatField('Current Price', validators=[DataRequired()])
    previous_price = FloatField('Previous Price', validators=[DataRequired()])

    # Your first code used StringField, second used IntegerField → unified as IntegerField
    in_stock = IntegerField('Stock Quantity', validators=[DataRequired(), NumberRange(min=0)])

    product_picture = FileField('Product Picture', validators=[DataRequired()])
    flash_sale = BooleanField('Flash Sale')

    # Category field from second code block
    category = SelectField(
        'Category',
        choices=[
            ('Phone', 'Phone'),
            ('Accessories', 'Accessories'),
            ('Watch', 'Watch'),
            ('Laptop', 'Laptop'),
            ('Gaming', 'Gaming'),
            ('Television', 'Television'),
        ],
        validators=[DataRequired()]
    )

    # Keeping all submit buttons
    add_product = SubmitField('Add Product')
    update_product = SubmitField('Update Product')


# -------------------- ORDER FORM --------------------

class OrderForm(FlaskForm):
    order_status = SelectField(
        'Order Status',
        choices=[
            ('Pending', 'Pending'),
            ('Accepted', 'Accepted'),
            ('Out for delivery', 'Out for delivery'),
            ('Delivered', 'Delivered'),
            ('Canceled', 'Canceled')
        ]
    )
    update = SubmitField('Update Status')
