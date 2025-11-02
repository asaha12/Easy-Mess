from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from datetime import date
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secretkey'

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///mess.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


# ---------------- MODELS ----------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    username = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(256))
    role = db.Column(db.String(20))
    email = db.Column(db.String(150), unique=True)
    first_login = db.Column(db.Boolean, default=True)  # new field


class Month(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)


class Meal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)

    # Link to any user
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='meals')  # gives access: user.meals

    morning = db.Column(db.Integer, default=0)
    lunch = db.Column(db.Integer, default=0)
    dinner = db.Column(db.Integer, default=0)

    # Link to Month
    month_id = db.Column(db.Integer, db.ForeignKey('month.id'), nullable=False)
    month = db.relationship('Month', backref='meals')




class Deposit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    month_id = db.Column(db.Integer, db.ForeignKey('month.id'), nullable=False)
    
    boarder_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # FK to User
    amount = db.Column(db.Float, nullable=False)

    # ✅ Add relationship so you can access deposit.user.name
    user = db.relationship('User', backref='deposits')






class Bazar(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, default=date.today)
    month_id = db.Column(db.Integer, db.ForeignKey('month.id'))
    description = db.Column(db.String(100))
    cost = db.Column(db.Float)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ---------------- ROUTES ----------------

# List all users
@app.route('/users')
@login_required
def user_list():
    if current_user.role != 'manager':
        flash("Access denied!", "danger")
        return redirect(url_for('dashboard'))
    users = User.query.all()
    return render_template('user_list.html', users=users)


# Add new user
@app.route('/users/add', methods=['GET', 'POST'])
@login_required
def add_user():
    if current_user.role != 'manager':
        flash("Access denied!", "danger")
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        name = request.form['name']
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        role = request.form['role']
        
        if User.query.filter_by(username=username).first():
            flash("Username already exists!", "warning")
            return redirect(url_for('add_user'))
        
        new_user = User(name=name, username=username, password=password, role=role, first_login=True)
        db.session.add(new_user)
        db.session.commit()
        flash("User added successfully!", "success")
        return redirect(url_for('user_list'))

    return render_template('add_user.html')

# Edit user role
@app.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if current_user.role != 'manager':
        flash("Access denied!", "danger")
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        user.role = request.form['role']
        db.session.commit()
        flash("User role updated!", "success")
        return redirect(url_for('user_list'))
    
    return render_template('edit_user.html', user=user)

# Delete user
@app.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.role != 'manager':
        flash("Access denied!", "danger")
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash("User deleted successfully!", "success")
    return redirect(url_for('user_list'))


@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'manager':
            return redirect(url_for('manager_dashboard'))
        else:
            return redirect(url_for('boarder_dashboard'))
    return redirect(url_for('login'))




@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        new_password = request.form['new_password']
        hashed_pw = generate_password_hash(new_password, method='pbkdf2:sha256')
        current_user.password = hashed_pw
        current_user.first_login = False
        db.session.commit()
        flash("Password updated successfully!")
        return redirect(url_for('index'))

    return render_template('change_password.html')



@app.route('/manager/change_role/<int:user_id>', methods=['GET', 'POST'])
@login_required
def change_role(user_id):
    if current_user.role != 'manager':
        return redirect(url_for('index'))

    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        user.role = request.form['role']
        db.session.commit()
        flash(f"Role of {user.name} updated to {user.role}")
        return redirect(url_for('list_users'))

    return render_template('change_role.html', user=user)

@app.route('/manager/list_users')
@login_required
def list_users():
    if current_user.role != 'manager':
        return redirect(url_for('index'))

    users = User.query.all()
    return render_template('list_users.html', users=users)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            if user.first_login:
                return redirect(url_for('change_password'))
            return redirect(url_for('index'))
        else:
            flash("Invalid credentials!", "danger")
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# ---------------- MONTH MANAGEMENT ----------------

@app.route('/manager/months', methods=['GET', 'POST'])
@login_required
def manage_months():
    if current_user.role != 'manager':
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form['name']
        # disable existing active months
        Month.query.update({Month.is_active: False})
        new_month = Month(name=name, is_active=True)
        db.session.add(new_month)
        db.session.commit()
        flash(f'Month "{name}" started and set active.')
        return redirect(url_for('manage_months'))

    months = Month.query.all()
    return render_template('manage_months.html', months=months)


@app.route('/manager/disable_month/<int:id>')
@login_required
def disable_month(id):
    if current_user.role != 'manager':
        return redirect(url_for('index'))
    month = Month.query.get(id)
    if month:
        month.is_active = False
        db.session.commit()
        flash(f'Month "{month.name}" disabled.')
    return redirect(url_for('manage_months'))


@app.route('/manager/delete_month/<int:id>')
@login_required
def delete_month(id):
    if current_user.role != 'manager':
        return redirect(url_for('index'))
    month = Month.query.get(id)
    if month:
        db.session.delete(month)
        db.session.commit()
        flash(f'Month "{month.name}" deleted.')
    return redirect(url_for('manage_months'))


# ---------------- DASHBOARDS ----------------

@app.route('/manager/dashboard')
@login_required
def manager_dashboard():
    if current_user.role != 'manager':
        return redirect(url_for('index'))
    
    active_month = Month.query.filter_by(is_active=True).first()
    if not active_month:
        flash("No active month found.")
        return redirect(url_for('manage_months'))

    # Gather all entries for the active month
    bazars = Bazar.query.filter_by(month_id=active_month.id).all()
    deposits = Deposit.query.filter_by(month_id=active_month.id).all()
    meals = Meal.query.filter_by(month_id=active_month.id).all()

    # Total bazar cost
    total_bazar = sum(b.cost for b in bazars)

    # Total meals for all users (boarders + managers)
    total_meals = sum(m.morning + m.lunch + m.dinner for m in meals)
    
    # Meal rate
    meal_rate = round(total_bazar / total_meals, 2) if total_meals > 0 else 0

    # Include all users (boarders + managers)
    users = User.query.all()
    stats = []

    for u in users:
        u_meals = [m for m in meals if m.user_id == u.id]
        u_deposits = [d for d in deposits if d.boarder_id == u.id]

        total_meal_count = sum(m.morning + m.lunch + m.dinner for m in u_meals)
        total_deposit = sum(d.amount for d in u_deposits)
        meal_cost = round(total_meal_count * meal_rate, 2)
        balance = round(total_deposit - meal_cost, 2)

        stats.append({
            'name': u.name,
            'role': u.role,
            'total_meal': total_meal_count,
            'deposit': total_deposit,
            'meal_cost': meal_cost,
            'balance': balance
        })

    return render_template('manager_dashboard.html',
                           active_month=active_month,
                           total_bazar=total_bazar,
                           total_meals=total_meals,
                           meal_rate=meal_rate,
                           stats=stats)


@app.route('/boarder/dashboard')
@login_required
def boarder_dashboard():
    if current_user.role != 'boarder':
        return redirect(url_for('index'))

    active_month = Month.query.filter_by(is_active=True).first()
    if not active_month:
        flash("No active month found.")
        return redirect(url_for('index'))

    bazars = Bazar.query.filter_by(month_id=active_month.id).all()
    deposits = Deposit.query.filter_by(month_id=active_month.id).all()
    meals = Meal.query.filter_by(month_id=active_month.id).all()

    total_bazar = sum(b.cost for b in bazars)
    total_meals = sum(m.morning + m.lunch + m.dinner for m in meals)
    meal_rate = round(total_bazar / total_meals, 2) if total_meals > 0 else 0

    my_meals = [m for m in meals if m.boarder_id == current_user.id]
    my_deposits = [d for d in deposits if d.boarder_id == current_user.id]

    total_meal_count = sum(m.morning + m.day + m.night for m in my_meals)
    total_deposit = sum(d.amount for d in my_deposits)
    meal_cost = round(total_meal_count * meal_rate, 2)
    balance = round(total_deposit - meal_cost, 2)

    return render_template('boarder_dashboard.html',
                           active_month=active_month,
                           total_bazar=total_bazar,
                           total_meals=total_meals,
                           meal_rate=meal_rate,
                           total_meal_count=total_meal_count,
                           total_deposit=total_deposit,
                           meal_cost=meal_cost,
                           balance=balance)


# ---------------- ADD MEAL ----------------
@app.route('/add_meal/', defaults={'month_id': None}, methods=['GET','POST'])
@app.route('/add_meal/<int:month_id>', methods=['GET','POST'])
def add_meal(month_id):
    if not month_id:
        # pick the current active month
        active_month = Month.query.order_by(Month.id.desc()).first()
        month_id = active_month.id
    else:
        active_month = Month.query.get_or_404(month_id)
    users = User.query.all()  # fetch all users

    if request.method == 'POST':
        date_str = request.form.get('date')
        user_id = int(request.form.get('user_id'))
        morning = int(request.form.get('morning', 0))
        lunch = int(request.form.get('lunch', 0))
        dinner = int(request.form.get('dinner', 0))


        meal = Meal(
            date=date.fromisoformat(date_str),
            user_id=user_id,
            morning=morning,
            lunch=lunch,
            dinner=dinner,
            month_id=active_month.id
        )

        db.session.add(meal)
        db.session.commit()
        flash("Meal added successfully!", "success")
        return redirect(url_for('add_meal', month_id=month_id))

    return render_template('add_meal.html', active_month=active_month, users=users)

# ---------------- ADD DEPOSIT ----------------
@app.route('/manager/add_deposit', methods=['GET', 'POST'])
@login_required
def add_deposit():
    if current_user.role != 'manager':
        return redirect(url_for('index'))
    
    active_month = Month.query.filter_by(is_active=True).first()
    if not active_month:
        flash("No active month found. Start a month first.")
        return redirect(url_for('manage_months'))

    # ✅ Include all users (boarders + managers)
    users = User.query.all()  

    if request.method == 'POST':
        date_str = request.form['date']
        user_id = int(request.form['user'])
        amount = float(request.form['amount'])
        
        deposit = Deposit(
            date=date.fromisoformat(date_str),
            month_id=active_month.id,
            boarder_id=user_id,  # same column for simplicity
            amount=amount
        )
        db.session.add(deposit)
        db.session.commit()
        flash('Deposit added successfully!')
        return redirect(url_for('add_deposit'))

    return render_template('add_deposit.html', users=users, active_month=active_month)



# ---------------- ADD BAZAR ----------------
@app.route('/manager/add_bazar', methods=['GET', 'POST'])
@login_required
def add_bazar():
    if current_user.role != 'manager':
        return redirect(url_for('index'))
    active_month = Month.query.filter_by(is_active=True).first()
    if not active_month:
        flash("No active month found. Start a month first.")
        return redirect(url_for('manage_months'))

    if request.method == 'POST':
        date_str = request.form['date']
        description = request.form['description']
        cost = float(request.form['cost'])
        bazar = Bazar(date=date.fromisoformat(date_str), month_id=active_month.id,
                      description=description, cost=cost)
        db.session.add(bazar)
        db.session.commit()
        flash('Bazar entry added successfully!')
        return redirect(url_for('add_bazar'))

    return render_template('add_bazar.html', active_month=active_month)

@app.route('/manager/view_meals')
@login_required
def view_meals():
    if current_user.role != 'manager':
        return redirect(url_for('index'))
    active_month = Month.query.filter_by(is_active=True).first()
    if not active_month:
        flash("No active month found.")
        return redirect(url_for('manage_months'))
    meals = Meal.query.filter_by(month_id=active_month.id).all()
    return render_template('view_meals.html', meals=meals, active_month=active_month)

@app.route('/manager/delete_meal/<int:id>')
@login_required
def delete_meal(id):
    if current_user.role != 'manager':
        return redirect(url_for('index'))
    meal = Meal.query.get(id)
    if meal:
        db.session.delete(meal)
        db.session.commit()
        flash('Meal deleted successfully!')
    return redirect(url_for('view_meals'))

@app.route('/manager/view_deposits')
@login_required
def view_deposits():
    if current_user.role != 'manager':
        return redirect(url_for('index'))
    active_month = Month.query.filter_by(is_active=True).first()
    if not active_month:
        flash("No active month found.")
        return redirect(url_for('manage_months'))
    deposits = Deposit.query.filter_by(month_id=active_month.id).all()
    return render_template('view_deposits.html', deposits=deposits, active_month=active_month)

@app.route('/manager/delete_deposit/<int:id>')
@login_required
def delete_deposit(id):
    if current_user.role != 'manager':
        return redirect(url_for('index'))
    deposit = Deposit.query.get(id)
    if deposit:
        db.session.delete(deposit)
        db.session.commit()
        flash('Deposit deleted successfully!')
    return redirect(url_for('view_deposits'))

@app.route('/manager/view_bazar')
@login_required
def view_bazar():
    if current_user.role != 'manager':
        return redirect(url_for('index'))
    active_month = Month.query.filter_by(is_active=True).first()
    if not active_month:
        flash("No active month found.")
        return redirect(url_for('manage_months'))
    bazars = Bazar.query.filter_by(month_id=active_month.id).all()
    return render_template('view_bazar.html', bazars=bazars, active_month=active_month)

@app.route('/manager/delete_bazar/<int:id>')
@login_required
def delete_bazar(id):
    if current_user.role != 'manager':
        return redirect(url_for('index'))
    bazar = Bazar.query.get(id)
    if bazar:
        db.session.delete(bazar)
        db.session.commit()
        flash('Bazar entry deleted successfully!')
    return redirect(url_for('view_bazar'))



with app.app_context():
    db.create_all()  # ✅ Create tables automatically on every startup

if __name__ == '__main__':
    app.run(debug=True)



