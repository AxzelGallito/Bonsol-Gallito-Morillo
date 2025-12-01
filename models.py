from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from .extensions import db   # <-- using your first version import


# ============================
#        CUSTOMER MODEL
# ============================
class Customer(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    username = db.Column(db.String(100))
    address = db.Column(db.String(200))
    pnumber = db.Column(db.String(20))
    sex = db.Column(db.String(10))
    date_of_birth = db.Column(db.Date)

    profile_picture = db.Column(db.String(255), nullable=True)

    password_hash = db.Column(db.String(150))
    date_joined = db.Column(db.DateTime(), default=datetime.utcnow)

    cart_items = db.relationship('Cart', backref=db.backref('customer', lazy=True))
    orders = db.relationship('Order', backref=db.backref('customer', lazy=True))

    # ------------------------ Password Helpers ------------------------ #

    def set_password(self, password):
        """Hashes and sets the user's password."""
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        """Verifies a password. Returns False if no password is set."""
        if not self.password_hash:
            return False  # Prevent NoneType error
        return check_password_hash(self.password_hash, password)
    
# ============================
#         PRODUCT MODEL
# ============================
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(100), nullable=False)
    current_price = db.Column(db.Float, nullable=False)
    previous_price = db.Column(db.Float)  # merged: second version forced nullable=False, first allowed None
    in_stock = db.Column(db.Integer, default=0, nullable=False)  # best option: Integer + default
    flash_sale = db.Column(db.Boolean, default=False)
    category = db.Column(db.String(50))  # from first version
    product_picture = db.Column(db.String(1000))  # merged: 100 → 1000 (safer for long filenames)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)

    carts = db.relationship('Cart', backref=db.backref('product', lazy=True))
    orders = db.relationship('Order', backref=db.backref('product', lazy=True))

    def __str__(self):
        return f'<Product {self.product_name}>'


# ============================
#          CART MODEL
# ============================
class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quantity = db.Column(db.Integer, nullable=False)

    customer_link = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    product_link = db.Column(
        db.Integer, 
        db.ForeignKey('product.id', ondelete='SET NULL'), 
        nullable=True
    )

    def __str__(self):
        return f'<Cart {self.id}>'


# ============================
#          ORDER MODEL
# ============================
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(100), nullable=False)
    payment_id = db.Column(db.String(1000), nullable=False)

    customer_link = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    product_link = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)

    def __str__(self):
        return f'<Order {self.id}>'
