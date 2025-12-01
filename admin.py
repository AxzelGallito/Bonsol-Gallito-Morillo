from flask import Blueprint, current_app, request, render_template, flash, send_from_directory, redirect, url_for
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from .forms import ShopItemsForm, OrderForm
from .models import Product, Order, Customer, Cart     # <-- IMPORTANT: Added Cart
from .extensions import db
import os
import re

admin = Blueprint('admin', __name__)

# ---------------- Helper Functions ---------------- #

def sanitize_filename(filename: str) -> str:
    if not filename:
        return ''
    filename = secure_filename(filename)
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    return filename.strip().rstrip('.')

def save_file(file) -> str:
    upload_folder = os.path.join(current_app.root_path, 'media')
    os.makedirs(upload_folder, exist_ok=True)

    filename = sanitize_filename(file.filename)
    file_path = os.path.join(upload_folder, filename)
    file.save(file_path)

    return f'/media/{filename}'

def admin_required():
    """Return 404 unless the user is admin (id=1)."""
    if not current_user.is_authenticated or current_user.id != 1:
        return render_template('404.html')
    return None

# ---------------- Media Files ---------------- #

@admin.route('/media/<path:filename>')
def media(filename):
    media_folder = os.path.join(current_app.root_path, 'media')
    file_path = os.path.join(media_folder, filename)

    if os.path.exists(file_path):
        return send_from_directory(media_folder, filename)

    sanitized = sanitize_filename(filename)
    sanitized_path = os.path.join(media_folder, sanitized)

    if os.path.exists(sanitized_path):
        return send_from_directory(media_folder, sanitized)

    for f in os.listdir(media_folder):
        if f.lower() == filename.lower():
            return send_from_directory(media_folder, f)

    return "Image not found", 404

# ---------------- Product Routes ---------------- #

@admin.route('/add-shop-items', methods=['GET', 'POST'])
@login_required
def add_shop_items():
    if admin_required():
        return admin_required()

    form = ShopItemsForm()

    if form.validate_on_submit():
        file = form.product_picture.data
        if not file or not file.filename:
            flash("Please upload a product image.")
            return render_template('add_shop_items.html', form=form)

        picture_url = save_file(file)

        new_item = Product(
            product_name=form.product_name.data,
            current_price=form.current_price.data,
            previous_price=form.previous_price.data,
            in_stock=form.in_stock.data,
            flash_sale=form.flash_sale.data,
            category=form.category.data,
            product_picture=picture_url
        )

        try:
            db.session.add(new_item)
            db.session.commit()
            flash(f"{new_item.product_name} added successfully")
            return redirect(url_for('admin.shop_items'))
        except Exception as e:
            db.session.rollback()
            flash("Product not added due to an error.")
            print("Error adding product:", e)

    return render_template('add_shop_items.html', form=form)

@admin.route('/shop-items')
@login_required
def shop_items():
    if admin_required():
        return admin_required()

    search = request.args.get('search', '').strip()

    if search:
        # Search by product name OR category (case-insensitive)
        items = Product.query.filter(
            (Product.product_name.ilike(f"%{search}%")) |
            (Product.category.ilike(f"%{search}%"))
        ).order_by(Product.date_added).all()
    else:
        items = Product.query.order_by(Product.date_added).all()

    return render_template('shop_items.html', items=items, search=search)

@admin.route('/update-item/<int:item_id>', methods=['GET', 'POST'])
@login_required
def update_item(item_id):
    # Check if current user is admin
    admin_check = admin_required()
    if admin_check:
        return admin_check  # redirect or response if not admin

    # Fetch the item or return 404
    item = Product.query.get_or_404(item_id)
    form = ShopItemsForm(obj=item)  # pre-fill form with existing data

    if form.validate_on_submit():
        # Update all fields directly
        item.product_name = form.product_name.data
        item.previous_price = form.previous_price.data
        item.current_price = form.current_price.data
        item.in_stock = form.in_stock.data
        item.flash_sale = form.flash_sale.data  # checkbox handled correctly
        item.category = form.category.data

        # Handle file upload
        if form.product_picture.data and form.product_picture.data.filename:
            item.product_picture = save_file(form.product_picture.data)

        try:
            db.session.commit()
            flash(f"{item.product_name} updated successfully", "success")
            return redirect(url_for('admin.shop_items'))
        except Exception as e:
            db.session.rollback()
            flash("Item not updated due to an error.", "danger")
            print("Error updating product:", e)
    else:
        # Debug: print form validation errors
        if request.method == "POST":
            print("Form errors:", form.errors)

    return render_template('update_item.html', form=form, item=item)

@admin.route('/delete-product/<int:product_id>')
@login_required
def delete_product(product_id):
    try:
        product = Product.query.get_or_404(product_id)

        # Delete all cart entries referencing this product
        Cart.query.filter_by(product_link=product.id).delete(synchronize_session=False)

        # Delete the product
        db.session.delete(product)
        db.session.commit()

        flash("Product deleted successfully. Related cart items removed.", "success")

    except Exception as e:
        db.session.rollback()
        print("DELETE ERROR:", e)
        flash("An error occurred while deleting the product.", "error")

    return redirect(url_for('admin.admin_page'))


@admin.route('/delete-item/<int:cart_id>')
@login_required
def delete_item(cart_id):
    try:
        cart_item = Cart.query.get_or_404(cart_id)

        # Ensure user owns the item
        if cart_item.customer_link != current_user.id:
            flash("You cannot delete another user's cart item.", "error")
            return redirect(url_for('views.shop_items'))

        db.session.delete(cart_item)
        db.session.commit()
        flash('Item removed from cart.', 'success')

    except Exception as e:
        db.session.rollback()
        print("DELETE ERROR:", e)
        flash('An error occurred while deleting item.', 'error')

    return redirect(url_for('views.shop_items'))

# ---------------- Order Management ---------------- #

@admin.route('/view-orders')
@login_required
def order_view():
    if admin_required():
        return admin_required()

    orders = Order.query.all()
    return render_template('view_orders.html', orders=orders)

@admin.route('/update-order/<int:order_id>', methods=['GET', 'POST'])
@login_required
def update_order(order_id):
    if admin_required():
        return admin_required()

    order = Order.query.get_or_404(order_id)
    form = OrderForm(obj=order)

    if form.validate_on_submit():
        order.status = form.order_status.data
        try:
            db.session.commit()
            flash(f"Order {order_id} updated successfully")
            return redirect(url_for('admin.order_view'))
        except Exception as e:
            db.session.rollback()
            flash("Order not updated.")
            print("Error:", e)

    return render_template('order_update.html', form=form, order=order)

# ---------------- Customers ---------------- #

@admin.route('/customers')
@login_required
def display_customers():
    check = admin_required()
    if check:
        return check

    customers = Customer.query.all()
    return render_template('customers.html', customers=customers)

@admin.route('/delete_customer/<int:id>', methods=['POST'])
@login_required
def delete_customer(id):
    if admin_required():
        return admin_required()

    customer = Customer.query.get_or_404(id)

    # Prevent deleting self
    if customer.id == current_user.id:
        flash("You cannot delete your own account.", "danger")
        return redirect(url_for('admin.display_customers'))

    try:
        # DELETE CART ITEMS
        Cart.query.filter_by(customer_link=id).delete()

        # DELETE ORDERS
        Order.query.filter_by(customer_link=id).delete()

        # DELETE CUSTOMER
        db.session.delete(customer)

        db.session.commit()
        flash("Customer deleted successfully!", "success")

    except Exception as e:
        db.session.rollback()
        flash("Failed to delete customer.", "danger")
        print("Error:", e)

    return redirect(url_for('admin.display_customers'))

# ---------------- Admin Home ---------------- #

@admin.route('/admin-page')
@login_required
def admin_page():
    if admin_required():
        return admin_required()
    return render_template('admin.html')