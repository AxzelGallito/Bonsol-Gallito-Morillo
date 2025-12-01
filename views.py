# Updated views.py with fixed minuscart route
from flask import Blueprint, render_template, flash, redirect, request, jsonify, url_for, current_app
from flask_login import login_required, current_user
from intasend import APIService
from datetime import datetime
from .models import Product, Cart, Order
from .models import Customer
from .extensions import db
import sqlite3
from werkzeug.utils import secure_filename
import os


views = Blueprint('views', __name__)

API_PUBLISHABLE_KEY = 'YOUR_PUBLISHABLE_KEY'
API_TOKEN = 'YOUR_API_TOKEN'


@views.app_context_processor
def inject_cart_count():
    if current_user.is_authenticated:
        cart_count = Cart.query.filter_by(customer_link=current_user.id).count()
    else:
        cart_count = 0
    return dict(cart_count=cart_count)


@views.route('/')
def home():
    category = request.args.get('category')
    items = Product.query.filter_by(category=category, flash_sale=True).all() if category \
             else Product.query.filter_by(flash_sale=True).all()

    return render_template('home.html', items=items)


@views.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        search_query = request.form.get('search')
        items = Product.query.filter(Product.product_name.ilike(f'%{search_query}%')).all()
        return render_template('search.html', items=items,
                               cart=Cart.query.filter_by(customer_link=current_user.id).all()
                               if current_user.is_authenticated else [])

    return render_template('search.html')


@views.route('/category/<string:category_name>')
def products_by_category(category_name):
    items = Product.query.filter_by(category=category_name).all()
    return render_template('category.html', items=items, category=category_name)


@views.route('/add-to-cart/<int:item_id>')
@login_required
def add_to_cart(item_id):
    item_to_add = Product.query.get(item_id)
    item_exists = Cart.query.filter_by(product_link=item_id, customer_link=current_user.id).first()

    # STOCK CHECK
    if item_exists:
        if item_exists.quantity >= item_to_add.in_stock:
            flash(f"Only {item_to_add.in_stock} item(s) in stock.")
            return redirect(request.referrer)

        item_exists.quantity += 1
        db.session.commit()
        flash(f"Updated quantity for {item_exists.product.product_name}")

    else:
        if item_to_add.in_stock < 1:
            flash("This item is out of stock.")
            return redirect(request.referrer)

        new_item = Cart(quantity=1, product_link=item_to_add.id, customer_link=current_user.id)
        db.session.add(new_item)
        db.session.commit()
        flash(f"{item_to_add.product_name} added to cart")

    return redirect(request.referrer)


@views.route('/cart')
@login_required
def show_cart():
    cart = Cart.query.filter_by(customer_link=current_user.id).all()
    amount = sum(item.product.current_price * item.quantity for item in cart)
    return render_template('cart.html', cart=cart, amount=amount, total=amount)


@views.route('/pluscart')
@login_required
def plus_cart():
    cart_item = Cart.query.get(request.args.get('cart_id'))
    product = cart_item.product

    # --- STOCK LIMIT CHECK ---
    if cart_item.quantity >= product.in_stock:
        return jsonify({
            'quantity': cart_item.quantity,
            'limited': True,              # tells JS "stop"
            'max_stock': product.in_stock
        })

    # SAFE TO INCREASE
    cart_item.quantity += 1
    db.session.commit()

    cart = Cart.query.filter_by(customer_link=current_user.id).all()
    amount = sum(item.product.current_price * item.quantity for item in cart)

    return jsonify({
        'quantity': cart_item.quantity,
        'amount': amount,
        'total': amount,
        'limited': False
    })


@views.route('/minuscart')
@login_required
def minus_cart():
    cart_item = Cart.query.get(request.args.get('cart_id'))

    if not cart_item:
        return jsonify({'error': 'Item not found'}), 404

    cart_item.quantity -= 1

    if cart_item.quantity <= 0:
        db.session.delete(cart_item)
        db.session.commit()

        cart = Cart.query.filter_by(customer_link=current_user.id).all()
        amount = sum(item.product.current_price * item.quantity for item in cart)

        return jsonify({
            'quantity': 0,
            'amount': amount,
            'total': amount,
            'removed': True
        })

    db.session.commit()

    cart = Cart.query.filter_by(customer_link=current_user.id).all()
    amount = sum(item.product.current_price * item.quantity for item in cart)

    return jsonify({
        'quantity': cart_item.quantity,
        'amount': amount,
        'total': amount,
        'removed': False
    })


@views.route('/removecart')
@login_required
def remove_cart():
    cart_id = request.args.get('cart_id')
    cart_item = Cart.query.get(cart_id)

    db.session.delete(cart_item)
    db.session.commit()

    cart = Cart.query.filter_by(customer_link=current_user.id).all()
    amount = sum(item.product.current_price * item.quantity for item in cart)

    return jsonify({
        'amount': amount,
        'total': amount,
        'cart_count': len(cart)
    })


@views.route('/direct-order/<int:product_id>')
@login_required
def direct_order(product_id):

    product = Product.query.get_or_404(product_id)

    review_items = [{
        'cart_id': None,
        'product_id':product.id,
        'name': product.product_name,
        'price': product.current_price,
        'quantity': 1,
        'subtotal': product.current_price,
        'picture': product.product_picture
    }]

    total = product.current_price
    shipping = 0

    return render_template(
        'order_review.html',
        items=review_items,
        amount=total,
        total_with_shipping=total + shipping,
        shipping=shipping,
        customer_address=current_user.address,
        payment_mode="Cash on Delivery",
        direct_item_id=product.id
    )


@views.route('/place-order', methods=['POST'])
@login_required
def place_order():

    # FIXED REDIRECT HERE!!!
    if not current_user.sex or not current_user.date_of_birth or not current_user.pnumber:
        flash("Please complete your profile before placing an order.", "warning")
        return redirect(url_for('auth.update_profile', customer_id=current_user.id))

    selected_ids = request.form.getlist("selected_items[]")

    if not selected_ids:
        flash("No items selected!", "warning")
        return redirect(url_for('views.show_cart'))

    selected_cart_items = Cart.query.filter(
        Cart.id.in_(selected_ids),
        Cart.customer_link == current_user.id
    ).all()

    if not selected_cart_items:
        flash("No valid cart items selected.", "warning")
        return redirect(url_for('views.cart'))

    review_items = []
    total = 0
    shipping = 0

    for c in selected_cart_items:
        product = c.product
        subtotal = product.current_price * c.quantity

        review_items.append({
            'cart_id': c.id,
            'product_id': product.id,
            'name': product.product_name,
            'price': product.current_price,
            'quantity': c.quantity,
            'subtotal': subtotal,
            'picture': product.product_picture
        })

        total += subtotal

    return render_template(
        'order_review.html',
        items=review_items,
        amount=total,
        total_with_shipping=total + shipping,
        shipping=shipping,
        customer_address=current_user.address,
        payment_mode="Cash on Delivery"
    )


@views.route('/confirm-order', methods=['POST'])
@login_required
def confirm_order():

    if not current_user.sex or not current_user.date_of_birth or not current_user.pnumber:
        flash("Please complete your profile before placing an order.", "warning")
        return redirect(url_for('auth.update_profile', customer_id=current_user.id))

    direct_id = request.form.get("direct_item_id")

    if direct_id:
        product = Product.query.get_or_404(direct_id)

        order = Order(
            quantity=1,
            price=product.current_price,
            status="Pending",
            payment_id="DIRECT_ORDER",
            product_link=product.id,
            customer_link=current_user.id
        )

        db.session.add(order)
        product.in_stock = max(0, product.in_stock - 1)
        db.session.commit()

        flash("Order placed successfully!", "success")
        return redirect("/orders")

    selected_ids = request.form.getlist("selected_items[]")

    if not selected_ids:
        flash("No items selected to confirm.", "warning")
        return redirect("/cart")

    selected_cart_items = Cart.query.filter(
        Cart.id.in_(selected_ids),
        Cart.customer_link == current_user.id
    ).all()

    if not selected_cart_items:
        flash("Selected items invalid or no longer available.", "danger")
        return redirect("/cart")

    try:
        for item in selected_cart_items:
            order = Order(
                quantity=item.quantity,
                price=item.product.current_price,
                status="Pending",
                payment_id="CART_ORDER",
                product_link=item.product_link,
                customer_link=item.customer_link
            )
            db.session.add(order)

            prod = Product.query.get(item.product_link)
            if prod:
                prod.in_stock = max(0, prod.in_stock - item.quantity)

            db.session.delete(item)

        db.session.commit()
        flash("Order placed successfully!", "success")
        return redirect("/orders")

    except Exception:
        db.session.rollback()
        flash("Order failed.", "danger")
        return redirect("/cart")


@views.route('/cancel-order/<int:order_id>', methods=['POST'])
@login_required
def cancel_order(order_id):
    order = Order.query.get_or_404(order_id)

    if order.customer_link != current_user.id:
        flash("Unauthorized action!", "danger")
        return redirect(url_for('views.order'))

    if order.status == "Canceled":
        flash("Order is already canceled.", "info")
        return redirect(url_for('views.order'))

    product = Product.query.get(order.product_link)
    if product:
        product.in_stock += order.quantity

    order.status = "Canceled"

    db.session.commit()

    flash("Order canceled successfully! Stock restored.", "success")
    return redirect(url_for('views.order'))

@views.route("/upload-profile-picture/<int:id>", methods=["POST"])
@login_required
def upload_profile_picture(id):
    file = request.files.get("profile_picture")

    if not file or file.filename == "":
        flash("Invalid file", "error")
        return redirect(url_for("auth.profile", customer_id=id))

    filename = secure_filename(file.filename)

    upload_dir = os.path.join(current_app.config["MEDIA_FOLDER"], "profile_pictures")
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, filename)
    file.save(file_path)

    user = Customer.query.get(id)
    user.profile_picture = f"/media/profile_pictures/{filename}"  # <-- FIXED
    db.session.commit()

    flash("Profile picture updated successfully!", "success")
    return redirect(url_for("auth.profile", customer_id=id))

@views.route('/orders')
@login_required
def order():
    orders = Order.query.filter_by(customer_link=current_user.id).all()
    return render_template('orders.html', orders=orders)


@views.route('/order/received/<int:order_id>', methods=['POST'])
@login_required
def mark_order_received(order_id):
    order = Order.query.filter_by(id=order_id, customer_link=current_user.id).first()

    if not order:
        flash("Order not found.", "danger")
        return redirect("/orders")

    if order.status != "Delivered":
        flash("You can only confirm delivered orders.", "warning")
        return redirect("/orders")

    order.status = "Received"
    db.session.commit()

    flash("Thank you for confirming! Enjoy your product.", "success")
    return redirect("/orders")


@views.route('/order/not-received/<int:order_id>', methods=['POST'])
@login_required
def mark_order_not_received(order_id):
    order = Order.query.filter_by(id)


@views.route('/about-us')
def about_us():
    return render_template('about_us.html')


@views.route('/phones')
def phones():
    items = Product.query.filter_by(category="Phone").all()
    return render_template("phones.html", items=items, active_category='phones')


@views.route('/laptop')
def laptop():
    items = Product.query.filter_by(category="Laptop").all()
    return render_template("laptop.html", items=items, active_category='laptop')


@views.route('/smart-watch')
def smart_watch():
    items = Product.query.filter_by(category="Watch").all()
    return render_template("smart_watch.html", items=items, active_category='smart-watch')

@views.route('/gaming')
def gaming():
    items = Product.query.filter_by(category="Gaming").all()
    return render_template("gaming.html", items=items, active_category='gaming')

@views.route('/tv')
def tv():
    items = Product.query.filter_by(category="Television").all()
    return render_template("tv.html", items=items, active_category='tv')

@views.route('/accessories')
def accessories():
    items = Product.query.filter_by(category="Accessories").all()
    return render_template("accessories.html", items=items, active_category='accessories')