from flask import Blueprint, render_template, flash, redirect, request, url_for
from flask_login import login_user, login_required, logout_user, current_user
from .forms import LoginForm, SignUpForm, PasswordChangeForm
from .models import Customer
from .extensions import db
from datetime import datetime
from werkzeug.security import generate_password_hash

auth = Blueprint('auth', __name__)

@auth.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    form = SignUpForm()

    if form.validate_on_submit():
        email = form.email.data
        username = form.username.data
        address = form.address.data
        password1 = form.password1.data
        password2 = form.password2.data

        if password1 != password2:
            flash('Passwords do not match!')
            return render_template('signup.html', form=form)

        # Create new customer
        new_customer = Customer(
            email=email,
            username=username,
            address=address
        )
        new_customer.set_password(password2)  # securely hash the password

        try:
            db.session.add(new_customer)
            db.session.commit()
            flash('Account Created Successfully, You can now Login')
            return redirect('/login')
        except Exception:
            flash('Account Not Created! Email already exists')

        # Clear form
        form.email.data = ''
        form.username.data = ''
        form.address.data = ''
        form.password1.data = ''
        form.password2.data = ''

    return render_template('signup.html', form=form)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        customer = Customer.query.filter_by(email=email).first()

        if customer and customer.verify_password(password):
            login_user(customer)
            return redirect('/')
        flash('Incorrect Email or Password' if customer else 'Account does not exist.')

    return render_template('login.html', form=form)


@auth.route('/logout')
@login_required
def log_out():
    logout_user()
    return redirect('/')


@auth.route('/profile/<int:customer_id>')
@login_required
def profile(customer_id):
    customer = Customer.query.get_or_404(customer_id)

    # Prevent viewing someone else’s profile
    if customer.id != current_user.id:
        flash("You cannot view another user's profile.", "error")
        return redirect(url_for('views.home'))

    return render_template('profile.html', customer=customer)


@auth.route('/change-password/<int:customer_id>', methods=['GET', 'POST'])
@login_required
def change_password(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    form = PasswordChangeForm()

    if form.validate_on_submit():
        if customer.verify_password(form.current_password.data):
            if form.new_password.data == form.confirm_new_password.data:
                customer.set_password(form.new_password.data)  # securely hash the new password
                db.session.commit()
                flash('Password Updated Successfully')
                return redirect(url_for('auth.profile', customer_id=customer.id))
            else:
                flash('New passwords do not match!')
        else:
            flash('Current Password is Incorrect')

    return render_template('change_password.html', form=form)

@auth.route('/update-profile/<int:customer_id>', methods=['GET', 'POST'])
@login_required
def update_profile(customer_id):
    customer = Customer.query.get_or_404(customer_id)

    if customer.id != current_user.id:
        flash("You are not allowed to edit another user's profile.", "error")
        return redirect(url_for('views.home'))

    if request.method == 'POST':
        customer.username = request.form['username']
        customer.email = request.form['email']
        customer.address = request.form['address']
        customer.sex = request.form.get('sex')
        customer.pnumber = request.form.get('pnumber')

        dob_str = request.form.get('date_of_birth')
        customer.date_of_birth = datetime.strptime(dob_str, "%Y-%m-%d").date() if dob_str else None
        
        db.session.commit()
        flash("Profile updated successfully!", "success")

        return redirect(url_for('auth.profile', customer_id=customer.id))

    return render_template("update_profile.html", customer=customer)

