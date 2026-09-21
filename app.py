import os
import json
from datetime import datetime

from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import (
    StringField, TextAreaField, DateField, TimeField, PasswordField, SubmitField,
    SelectField, SelectMultipleField, IntegerField, HiddenField,
)
from wtforms.validators import DataRequired, Email, Length, EqualTo, NumberRange, ValidationError, Optional
from wtforms.widgets import ListWidget, CheckboxInput
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-me-in-.env')

db_user = os.environ.get('DB_USER', 'root')
db_password = os.environ.get('DB_PASSWORD', '349839Techamek')
db_host = os.environ.get('DB_HOST', 'localhost')
db_name = os.environ.get('DB_NAME', 'calendar_app')

app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"mysql+pymysql://{db_user}:{db_password}@{db_host}/{db_name}"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
csrf = CSRFProtect(app)

login_manager = LoginManager(app)
login_manager.login_view = 'admin_login'
login_manager.login_message = 'Please log in to access the admin area.'


# ---------------------------------------------------------------------------
# Pricing configuration
# Pulled from Coco Cafe "Special Events - Space Rental & Catering Options"
# (v.20260121). Keep this block in sync if the venue updates its rate sheet.
# ---------------------------------------------------------------------------

SPACE_RENTAL_PER_HOUR = 175.00
SPACE_RENTAL_INCLUDED_GUESTS = 35          # guest count included in the base hourly rate
SPACE_RENTAL_OVERAGE_PER_HOUR = 50.00      # extra $/hr once guest count exceeds the above
MENU_PRICE_PER_PERSON = 17.50
MAX_GUEST_CAPACITY = 50                    # venue maximum guest capacity
SALES_TAX_RATE = 0.0675                    # Medina County, OH combined sales tax rate (2026)
GRATUITY_RATE = 0.20                       # 20% gratuity added to the final invoice

DURATION_CHOICES = [
    ('1', '1 hour'), ('1.5', '1.5 hours'), ('2', '2 hours'), ('2.5', '2.5 hours'),
    ('3', '3 hours'), ('3.5', '3.5 hours'), ('4', '4 hours'), ('5', '5 hours'),
    ('6', '6 hours'),
]

EVENT_TYPE_CHOICES = [
    'Bridal Shower', 'Baby Shower', 'Birthday Celebration', 'Anniversary Party',
    'Business Meeting', 'Corporate Event', 'Intimate Gathering', 'Other',
]

SAVORY_OPTIONS = [
    'Chicken Salad Croissants', 'Ham & Cheese Croissants', 'Baguette Sandwiches',
    'Mini Quiches (meat and/or veggie)', 'Focaccia Sandwiches', 'Pizza Bread (meat and/or veggie)',
]

SWEET_OPTIONS = [
    'Blueberry Lemon Scones', 'Fruit & Cheese Danish', 'Cinnamon Buns',
    'Tea Biscuits', 'Assorted Muffins', 'Assorted Cookies',
]

# key -> (label, per_hour $, per_person $, flat $)
ENHANCEMENTS = {
    'crepe':      ('Crepe Menu',                    25.0, 7.0, 0.0),
    'espresso':   ('Espresso Menu',                 25.0, 5.0, 0.0),
    'decor':      ('Decor Service',                  0.0, 0.0, 325.0),
    'fruit_tray': ('Fruit Tray',                     0.0, 4.0, 0.0),
    'salad':      ('Salad with 2 Dressings',         0.0, 4.0, 0.0),
    'vegan_gf':   ('Vegan & Gluten Friendly Options', 0.0, 0.0, 0.0),
}

TABLE_TYPES = {
    'round8':   {'label': 'Round Table', 'seats': 8, 'shape': 'circle'},
    'round6':   {'label': 'Round Table', 'seats': 6, 'shape': 'circle'},
    'rect6':    {'label': 'Rectangular Table', 'seats': 6, 'shape': 'rect'},
    'hightop4': {'label': 'High-Top Table', 'seats': 4, 'shape': 'circle'},
}


def calculate_price(guest_count, duration_hours, enhancement_keys):
    """Returns a full price breakdown dict given the raw inputs.

    Mirrors the terms on the Coco Cafe Special Events rate sheet:
    - space rental is quoted per hour for up to 35 guests, with a per-hour
      overage fee above that
    - menu is priced per person
    - enhancements are a la carte, some per-hour + per-person, some flat
    - the deposit equals the space rental fee
    - Medina County sales tax and a 20% gratuity are added to the final total
    """
    guest_count = max(0, int(guest_count or 0))
    duration_hours = max(0.0, float(duration_hours or 0))
    enhancement_keys = enhancement_keys or []

    overage_guests = guest_count > SPACE_RENTAL_INCLUDED_GUESTS
    space_rental = SPACE_RENTAL_PER_HOUR * duration_hours
    space_rental_overage = (SPACE_RENTAL_OVERAGE_PER_HOUR * duration_hours) if overage_guests else 0.0
    space_rental_total = space_rental + space_rental_overage

    menu_total = MENU_PRICE_PER_PERSON * guest_count

    enhancement_lines = []
    enhancements_total = 0.0
    for key in enhancement_keys:
        if key not in ENHANCEMENTS:
            continue
        label, per_hour, per_person, flat = ENHANCEMENTS[key]
        cost = (per_hour * duration_hours) + (per_person * guest_count) + flat
        enhancement_lines.append({'key': key, 'label': label, 'cost': round(cost, 2)})
        enhancements_total += cost

    subtotal = space_rental_total + menu_total + enhancements_total
    tax_total = subtotal * SALES_TAX_RATE
    gratuity_total = subtotal * GRATUITY_RATE
    grand_total = subtotal + tax_total + gratuity_total
    deposit_amount = space_rental_total  # "deposit amount is equal to the space rental fee"

    return {
        'guest_count': guest_count,
        'duration_hours': duration_hours,
        'overage_guests': overage_guests,
        'space_rental_total': round(space_rental_total, 2),
        'menu_total': round(menu_total, 2),
        'enhancement_lines': enhancement_lines,
        'enhancements_total': round(enhancements_total, 2),
        'subtotal': round(subtotal, 2),
        'tax_rate': SALES_TAX_RATE,
        'tax_total': round(tax_total, 2),
        'gratuity_rate': GRATUITY_RATE,
        'gratuity_total': round(gratuity_total, 2),
        'grand_total': round(grand_total, 2),
        'deposit_amount': round(deposit_amount, 2),
    }


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Admin(db.Model, UserMixin):
    __tablename__ = 'admins'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Event(db.Model):
    __tablename__ = 'events'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    submitter_name = db.Column(db.String(120), nullable=False)
    submitter_email = db.Column(db.String(120), nullable=False)
    event_date = db.Column(db.Date, nullable=False)
    event_time = db.Column(db.Time, nullable=True)
    location = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, approved, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)

    # --- event planning details (new) ---
    event_type = db.Column(db.String(50), nullable=True)
    guest_count = db.Column(db.Integer, nullable=True)
    duration_hours = db.Column(db.Float, nullable=True)
    savory_selections = db.Column(db.String(400), nullable=True)   # comma-separated
    sweet_selections = db.Column(db.String(400), nullable=True)    # comma-separated
    enhancements = db.Column(db.String(400), nullable=True)        # comma-separated keys
    table_layout = db.Column(db.Text, nullable=True)               # JSON string of table placements

    # --- price tracking (new) ---
    space_rental_total = db.Column(db.Numeric(10, 2), nullable=True)
    menu_total = db.Column(db.Numeric(10, 2), nullable=True)
    enhancements_total = db.Column(db.Numeric(10, 2), nullable=True)
    subtotal = db.Column(db.Numeric(10, 2), nullable=True)
    tax_total = db.Column(db.Numeric(10, 2), nullable=True)
    gratuity_total = db.Column(db.Numeric(10, 2), nullable=True)
    grand_total = db.Column(db.Numeric(10, 2), nullable=True)
    deposit_amount = db.Column(db.Numeric(10, 2), nullable=True)

    reviewer = db.relationship('Admin', foreign_keys=[reviewed_by])

    def savory_list(self):
        return [s for s in (self.savory_selections or '').split(',') if s]

    def sweet_list(self):
        return [s for s in (self.sweet_selections or '').split(',') if s]

    def enhancement_labels(self):
        keys = [k for k in (self.enhancements or '').split(',') if k]
        return [ENHANCEMENTS[k][0] for k in keys if k in ENHANCEMENTS]

    def table_layout_list(self):
        try:
            return json.loads(self.table_layout) if self.table_layout else []
        except (TypeError, ValueError):
            return []

    def total_seats_placed(self):
        return sum(t.get('seats', 0) for t in self.table_layout_list())


@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))


# ---------------------------------------------------------------------------
# Forms
# ---------------------------------------------------------------------------

class MultiCheckboxField(SelectMultipleField):
    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()


class EventSubmissionForm(FlaskForm):
    title = StringField('Event Title', validators=[DataRequired(), Length(max=150)])
    event_type = SelectField(
        'Type of Event',
        choices=[(t, t) for t in EVENT_TYPE_CHOICES],
        validators=[DataRequired()],
    )
    description = TextAreaField('Description', validators=[Length(max=2000)])

    guest_count = IntegerField(
        'Number of Guests',
        validators=[DataRequired(), NumberRange(min=1, max=MAX_GUEST_CAPACITY,
                                                 message=f'Guest count must be between 1 and {MAX_GUEST_CAPACITY} (venue max capacity).')],
    )

    event_date = DateField('Event Date', validators=[DataRequired()])
    event_time = TimeField('Start Time', validators=[DataRequired()])
    duration_hours = SelectField(
        'Duration', choices=DURATION_CHOICES, validators=[DataRequired()],
    )
    location = StringField('Location / Room', validators=[Length(max=200)])

    savory_selections = MultiCheckboxField(
        'Savory Menu (choose 2)', choices=[(s, s) for s in SAVORY_OPTIONS],
    )
    sweet_selections = MultiCheckboxField(
        'Sweet Menu (choose 2)', choices=[(s, s) for s in SWEET_OPTIONS],
    )
    enhancements = MultiCheckboxField(
        'Enhancements & Add-Ons (optional)',
        choices=[(k, v[0]) for k, v in ENHANCEMENTS.items()],
        validators=[Optional()],
    )

    table_layout = HiddenField('Table Layout', default='[]')

    submitter_name = StringField('Your Name', validators=[DataRequired(), Length(max=120)])
    submitter_email = StringField('Your Email', validators=[DataRequired(), Email(), Length(max=120)])
    submit = SubmitField('Submit Event')

    def validate_savory_selections(self, field):
        if len(field.data) != 2:
            raise ValidationError('Please choose exactly 2 savory options.')

    def validate_sweet_selections(self, field):
        if len(field.data) != 2:
            raise ValidationError('Please choose exactly 2 sweet options.')

    def validate_table_layout(self, field):
        try:
            data = json.loads(field.data) if field.data else []
            if not isinstance(data, list):
                raise ValueError
        except (TypeError, ValueError):
            raise ValidationError('Table layout could not be read. Please rebuild your table arrangement.')


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Log In')


class AddAdminForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(max=80)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Create Admin')


# ---------------------------------------------------------------------------
# Public routes
# ---------------------------------------------------------------------------

@app.route('/', methods=['GET', 'POST'])
def submit_event():
    form = EventSubmissionForm()
    if form.validate_on_submit():
        enhancement_keys = form.enhancements.data
        price = calculate_price(form.guest_count.data, float(form.duration_hours.data), enhancement_keys)

        event = Event(
            title=form.title.data,
            event_type=form.event_type.data,
            description=form.description.data,
            submitter_name=form.submitter_name.data,
            submitter_email=form.submitter_email.data,
            event_date=form.event_date.data,
            event_time=form.event_time.data,
            duration_hours=float(form.duration_hours.data),
            guest_count=form.guest_count.data,
            location=form.location.data,
            status='pending',
            savory_selections=','.join(form.savory_selections.data),
            sweet_selections=','.join(form.sweet_selections.data),
            enhancements=','.join(enhancement_keys),
            table_layout=form.table_layout.data or '[]',
            space_rental_total=price['space_rental_total'],
            menu_total=price['menu_total'],
            enhancements_total=price['enhancements_total'],
            subtotal=price['subtotal'],
            tax_total=price['tax_total'],
            gratuity_total=price['gratuity_total'],
            grand_total=price['grand_total'],
            deposit_amount=price['deposit_amount'],
        )
        db.session.add(event)
        db.session.commit()
        flash(
            f'Thanks! Your event was submitted and is awaiting admin approval. '
            f'Estimated total: ${price["grand_total"]:.2f} (deposit due: ${price["deposit_amount"]:.2f}).',
            'success',
        )
        return redirect(url_for('submit_event'))
    return render_template(
        'submit.html', form=form,
        table_types=TABLE_TYPES, max_capacity=MAX_GUEST_CAPACITY,
    )


@app.route('/api/price-estimate', methods=['POST'])
def api_price_estimate():
    """Live price estimate consumed by the submission form's JS."""
    data = request.get_json(silent=True) or {}
    try:
        guest_count = int(data.get('guest_count') or 0)
    except (TypeError, ValueError):
        guest_count = 0
    try:
        duration_hours = float(data.get('duration_hours') or 0)
    except (TypeError, ValueError):
        duration_hours = 0.0
    enhancement_keys = data.get('enhancements') or []
    if not isinstance(enhancement_keys, list):
        enhancement_keys = []
    price = calculate_price(guest_count, duration_hours, enhancement_keys)
    return jsonify(price)


# ---------------------------------------------------------------------------
# Admin auth
# ---------------------------------------------------------------------------

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        admin = Admin.query.filter_by(username=form.username.data).first()
        if admin and admin.check_password(form.password.data):
            login_user(admin)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('admin_dashboard'))
        flash('Invalid username or password.', 'error')
    return render_template('login.html', form=form)


@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('admin_login'))


# ---------------------------------------------------------------------------
# Admin views (all require login)
# ---------------------------------------------------------------------------

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    return render_template('dashboard.html')


@app.route('/admin/api/events')
@login_required
def api_events():
    """JSON feed consumed by FullCalendar. Only approved events are shown."""
    events = Event.query.filter_by(status='approved').all()
    output = []
    for e in events:
        start = e.event_date.isoformat()
        if e.event_time:
            start += f"T{e.event_time.isoformat()}"
        output.append({
            'id': e.id,
            'title': e.title,
            'start': start,
            'extendedProps': {
                'description': e.description or '',
                'location': e.location or '',
                'submitter_name': e.submitter_name,
                'submitter_email': e.submitter_email,
                'event_type': e.event_type or '',
                'guest_count': e.guest_count or 0,
                'duration_hours': e.duration_hours or 0,
                'savory': e.savory_list(),
                'sweet': e.sweet_list(),
                'enhancements': e.enhancement_labels(),
                'table_layout': e.table_layout_list(),
                'grand_total': float(e.grand_total) if e.grand_total is not None else None,
                'deposit_amount': float(e.deposit_amount) if e.deposit_amount is not None else None,
            },
        })
    return jsonify(output)


@app.route('/admin/pending')
@login_required
def admin_pending():
    pending_events = Event.query.filter_by(status='pending').order_by(Event.created_at.desc()).all()
    return render_template('pending.html', events=pending_events)


@app.route('/admin/events/<int:event_id>/approve', methods=['POST'])
@login_required
def approve_event(event_id):
    event = Event.query.get_or_404(event_id)
    event.status = 'approved'
    event.reviewed_by = current_user.id
    event.reviewed_at = datetime.utcnow()
    db.session.commit()
    flash(f'Approved "{event.title}".', 'success')
    return redirect(url_for('admin_pending'))


@app.route('/admin/events/<int:event_id>/reject', methods=['POST'])
@login_required
def reject_event(event_id):
    event = Event.query.get_or_404(event_id)
    event.status = 'rejected'
    event.reviewed_by = current_user.id
    event.reviewed_at = datetime.utcnow()
    db.session.commit()
    flash(f'Rejected "{event.title}".', 'success')
    return redirect(url_for('admin_pending'))


@app.route('/admin/manage', methods=['GET', 'POST'])
@login_required
def manage_admins():
    form = AddAdminForm()
    if form.validate_on_submit():
        if Admin.query.filter_by(username=form.username.data).first():
            flash('That username is already taken.', 'error')
        elif Admin.query.filter_by(email=form.email.data).first():
            flash('That email is already registered.', 'error')
        else:
            new_admin = Admin(username=form.username.data, email=form.email.data)
            new_admin.set_password(form.password.data)
            db.session.add(new_admin)
            db.session.commit()
            flash(f'Admin "{new_admin.username}" created.', 'success')
            return redirect(url_for('manage_admins'))
    admins = Admin.query.order_by(Admin.created_at.asc()).all()
    return render_template('manage_admins.html', form=form, admins=admins)


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------

@app.cli.command('init-db')
def init_db_cli():
    """Create all database tables. Run: flask init-db"""
    db.create_all()
    print('Database tables created.')


@app.cli.command('create-admin')
def create_admin_cli():
    """Create the first admin account from the command line. Run: flask create-admin"""
    import getpass
    username = input('Username: ').strip()
    email = input('Email: ').strip()
    password = getpass.getpass('Password: ')
    if Admin.query.filter_by(username=username).first():
        print('That username already exists.')
        return
    admin = Admin(username=username, email=email)
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    print(f'Admin "{username}" created.')


if __name__ == '__main__':
    app.run(debug=True)
