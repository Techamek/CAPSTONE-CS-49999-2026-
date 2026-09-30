import os
from datetime import datetime, date, time, timedelta

from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import (
    StringField, TextAreaField, DateField, PasswordField, SubmitField,
    SelectField, RadioField, IntegerField,
)
from wtforms.validators import DataRequired, Email, Length, EqualTo, NumberRange, ValidationError
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-me-in-.env')

db_user = os.environ.get('DB_USER', 'root')
db_password = os.environ.get('DB_PASSWORD', '')
db_host = os.environ.get('DB_HOST', 'localhost')
db_name = os.environ.get('DB_NAME', 'calendar_app')

# DATABASE_URL (optional) overrides the MySQL settings above, e.g. for local testing with SQLite.
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or (
    f"mysql+pymysql://{db_user}:{db_password}@{db_host}/{db_name}"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
csrf = CSRFProtect(app)

login_manager = LoginManager(app)
login_manager.login_view = 'admin_login'
login_manager.login_message = 'Please log in to access the admin area.'


# ---------------------------------------------------------------------------
# Venue configuration
# ---------------------------------------------------------------------------

MAX_GUEST_CAPACITY = 50
SLOT_MINUTES = 30              # start times are offered every 30 minutes
BOOKING_WINDOW_DAYS = 365      # how far ahead guests can book

DURATION_CHOICES = [
    ('1', '1 hour'), ('1.5', '1.5 hours'), ('2', '2 hours'), ('2.5', '2.5 hours'),
    ('3', '3 hours'), ('3.5', '3.5 hours'), ('4', '4 hours'), ('5', '5 hours'),
    ('6', '6 hours'),
]

EVENT_TYPE_CHOICES = [
    'Bridal Shower', 'Baby Shower', 'Birthday Celebration', 'Anniversary Party',
    'Business Meeting', 'Corporate Event', 'Intimate Gathering', 'Other',
]

DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

# Table layouts (images live in static/img). Guests up to 35 choose from the
# "35" set; 36-50 guests choose from the "50" set.
LAYOUTS = {
    '35-A': {'group': '35', 'label': 'Layout A', 'seats': 36, 'image': 'img/layout35-1.png'},
    '35-B': {'group': '35', 'label': 'Layout B', 'seats': 34, 'image': 'img/layout35-2.png'},
    '35-C': {'group': '35', 'label': 'Layout C', 'seats': 34, 'image': 'img/layout35-3.png'},
    '35-D': {'group': '35', 'label': 'Layout D', 'seats': 36, 'image': 'img/layout35-4.png'},
    '50-A': {'group': '50', 'label': 'Layout A', 'seats': 50, 'image': 'img/layout50-1.png'},
    '50-B': {'group': '50', 'label': 'Layout B', 'seats': 50, 'image': 'img/layout50-2.png'},
}
LAYOUT_SMALL_GROUP_MAX = 35


def layout_group_for(guest_count):
    return '35' if guest_count <= LAYOUT_SMALL_GROUP_MAX else '50'


# ---------------------------------------------------------------------------
# Admin-side price estimate (never shown to the public submitter)
# Source: Coco Cafe "Special Events" rate sheet v.20260121. Base package only:
# space rental + per-person menu, plus tax and gratuity.
# ---------------------------------------------------------------------------

SPACE_RENTAL_PER_HOUR = 175.00
SPACE_RENTAL_INCLUDED_GUESTS = 35
SPACE_RENTAL_OVERAGE_PER_HOUR = 50.00
MENU_PRICE_PER_PERSON = 17.50
SALES_TAX_RATE = 0.0675
GRATUITY_RATE = 0.20


def calculate_price(guest_count, duration_hours):
    guest_count = max(0, int(guest_count or 0))
    duration_hours = max(0.0, float(duration_hours or 0))

    rental = SPACE_RENTAL_PER_HOUR * duration_hours
    if guest_count > SPACE_RENTAL_INCLUDED_GUESTS:
        rental += SPACE_RENTAL_OVERAGE_PER_HOUR * duration_hours
    menu_total = MENU_PRICE_PER_PERSON * guest_count
    subtotal = rental + menu_total
    tax = subtotal * SALES_TAX_RATE
    gratuity = subtotal * GRATUITY_RATE
    return {
        'space_rental_total': round(rental, 2),
        'menu_total': round(menu_total, 2),
        'subtotal': round(subtotal, 2),
        'tax_total': round(tax, 2),
        'gratuity_total': round(gratuity, 2),
        'grand_total': round(subtotal + tax + gratuity, 2),
        'deposit_amount': round(rental, 2),
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

    event_type = db.Column(db.String(50), nullable=True)
    guest_count = db.Column(db.Integer, nullable=True)
    duration_hours = db.Column(db.Float, nullable=True)
    layout_choice = db.Column(db.String(10), nullable=True)   # key into LAYOUTS, e.g. '35-B'

    # Admin-only base-package estimate
    space_rental_total = db.Column(db.Numeric(10, 2), nullable=True)
    menu_total = db.Column(db.Numeric(10, 2), nullable=True)
    subtotal = db.Column(db.Numeric(10, 2), nullable=True)
    tax_total = db.Column(db.Numeric(10, 2), nullable=True)
    gratuity_total = db.Column(db.Numeric(10, 2), nullable=True)
    grand_total = db.Column(db.Numeric(10, 2), nullable=True)
    deposit_amount = db.Column(db.Numeric(10, 2), nullable=True)

    reviewer = db.relationship('Admin', foreign_keys=[reviewed_by])

    def layout_info(self):
        return LAYOUTS.get(self.layout_choice)

    def start_end(self):
        if not self.event_time:
            return None
        start = datetime.combine(self.event_date, self.event_time)
        return start, start + timedelta(hours=self.duration_hours or 0)


class WeeklyHours(db.Model):
    """Recurring opening hours for bookings, one row per weekday (0=Monday)."""
    __tablename__ = 'weekly_hours'
    id = db.Column(db.Integer, primary_key=True)
    weekday = db.Column(db.Integer, unique=True, nullable=False)
    enabled = db.Column(db.Boolean, default=False, nullable=False)
    open_time = db.Column(db.Time, nullable=True)
    close_time = db.Column(db.Time, nullable=True)


class DateOverride(db.Model):
    """A one-off change for a specific date: closed all day, or custom hours."""
    __tablename__ = 'date_overrides'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, unique=True, nullable=False)
    is_closed = db.Column(db.Boolean, default=True, nullable=False)
    open_time = db.Column(db.Time, nullable=True)
    close_time = db.Column(db.Time, nullable=True)
    note = db.Column(db.String(200), nullable=True)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Admin, int(user_id))


# ---------------------------------------------------------------------------
# Availability engine
# ---------------------------------------------------------------------------

def ensure_default_weekly_hours():
    """Seed Mon-Fri 9-5 (Sat/Sun closed) if the admin hasn't configured anything yet."""
    if WeeklyHours.query.count() > 0:
        return
    for wd in range(7):
        db.session.add(WeeklyHours(
            weekday=wd, enabled=wd < 5, open_time=time(9, 0), close_time=time(17, 0),
        ))
    db.session.commit()


def parse_hhmm(value):
    try:
        return datetime.strptime((value or '').strip(), '%H:%M').time()
    except ValueError:
        return None


def fmt_time(t):
    return t.strftime('%I:%M %p').lstrip('0')


class Availability:
    """Loads hours, overrides and approved bookings once, then answers queries."""

    def __init__(self):
        today = date.today()
        self.weekly = {w.weekday: w for w in WeeklyHours.query.all()}
        self.overrides = {o.date: o for o in DateOverride.query.filter(DateOverride.date >= today).all()}
        self.busy = {}
        approved = Event.query.filter(Event.status == 'approved', Event.event_date >= today).all()
        for e in approved:
            span = e.start_end()
            if span:
                self.busy.setdefault(e.event_date, []).append(span)

    def window(self, d):
        ov = self.overrides.get(d)
        if ov:
            if ov.is_closed or not (ov.open_time and ov.close_time):
                return None
            return ov.open_time, ov.close_time
        rule = self.weekly.get(d.weekday())
        if rule and rule.enabled and rule.open_time and rule.close_time:
            return rule.open_time, rule.close_time
        return None

    def slots(self, d, duration_hours):
        if d < date.today():
            return []
        win = self.window(d)
        if not win:
            return []
        day_close = datetime.combine(d, win[1])
        length = timedelta(hours=duration_hours)
        now = datetime.now()
        busy = self.busy.get(d, [])
        out = []
        t = datetime.combine(d, win[0])
        while t + length <= day_close:
            end = t + length
            if t > now and not any(t < b_end and end > b_start for b_start, b_end in busy):
                out.append(t.time())
            t += timedelta(minutes=SLOT_MINUTES)
        return out

    def available_dates(self, duration_hours):
        today = date.today()
        return [
            (today + timedelta(days=i)).isoformat()
            for i in range(BOOKING_WINDOW_DAYS + 1)
            if self.slots(today + timedelta(days=i), duration_hours)
        ]


def event_conflicts(event):
    """Other approved events overlapping this one."""
    span = event.start_end()
    if not span:
        return []
    others = Event.query.filter(
        Event.status == 'approved', Event.event_date == event.event_date, Event.id != event.id
    ).all()
    return [
        o for o in others
        if o.start_end() and span[0] < o.start_end()[1] and span[1] > o.start_end()[0]
    ]


# ---------------------------------------------------------------------------
# Forms
# ---------------------------------------------------------------------------

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
        validators=[DataRequired(), NumberRange(
            min=1, max=MAX_GUEST_CAPACITY,
            message=f'Guest count must be between 1 and {MAX_GUEST_CAPACITY} (venue max capacity).')],
    )

    duration_hours = SelectField('Duration', choices=DURATION_CHOICES, validators=[DataRequired()])
    event_date = DateField('Event Date', validators=[DataRequired(message='Please choose an available date.')])
    # Options are filled in by the browser from /api/availability/slots; validated server-side below.
    event_time = SelectField('Start Time', choices=[], validate_choice=False,
                             validators=[DataRequired(message='Please choose a start time.')])
    location = StringField('Location / Room', validators=[Length(max=200)])

    layout_choice = RadioField('Table Layout', choices=[(k, k) for k in LAYOUTS], validate_choice=False)

    submitter_name = StringField('Your Name', validators=[DataRequired(), Length(max=120)])
    submitter_email = StringField('Your Email', validators=[DataRequired(), Email(), Length(max=120)])
    submit = SubmitField('Submit Event')

    def validate_event_date(self, field):
        if field.data and field.data < date.today():
            raise ValidationError('Please choose a date in the future.')

    def validate_event_time(self, field):
        start = parse_hhmm(field.data)
        if not start:
            raise ValidationError('Please choose a start time.')
        if not self.event_date.data:
            return
        try:
            duration = float(self.duration_hours.data)
        except (TypeError, ValueError):
            return
        if start not in Availability().slots(self.event_date.data, duration):
            raise ValidationError(
                'That date and time is not available for the selected duration. Please pick another.')

    def validate_layout_choice(self, field):
        key = field.data
        if key not in LAYOUTS:
            raise ValidationError('Please choose a table layout.')
        guests = self.guest_count.data
        if guests and LAYOUTS[key]['group'] != layout_group_for(guests):
            raise ValidationError('That layout is not available for your guest count. Please choose another.')


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
        duration = float(form.duration_hours.data)
        price = calculate_price(form.guest_count.data, duration)
        event = Event(
            title=form.title.data,
            event_type=form.event_type.data,
            description=form.description.data,
            submitter_name=form.submitter_name.data,
            submitter_email=form.submitter_email.data,
            event_date=form.event_date.data,
            event_time=parse_hhmm(form.event_time.data),
            duration_hours=duration,
            guest_count=form.guest_count.data,
            location=form.location.data,
            layout_choice=form.layout_choice.data,
            status='pending',
            **price,
        )
        db.session.add(event)
        db.session.commit()
        flash('Thanks! Your event was submitted and is awaiting admin approval.', 'success')
        return redirect(url_for('submit_event'))

    layouts_by_group = {'35': [], '50': []}
    for key, info in LAYOUTS.items():
        layouts_by_group[info['group']].append((key, info))
    return render_template(
        'submit.html', form=form, max_capacity=MAX_GUEST_CAPACITY,
        layouts_by_group=layouts_by_group, small_group_max=LAYOUT_SMALL_GROUP_MAX,
    )


def _duration_arg():
    try:
        d = float(request.args.get('duration') or 1)
    except ValueError:
        d = 1.0
    return d if 0 < d <= 24 else 1.0


@app.route('/api/availability/dates')
def api_available_dates():
    """Bookable dates for a given duration. Read-only; exposes no event details."""
    return jsonify(Availability().available_dates(_duration_arg()))


@app.route('/api/availability/slots')
def api_available_slots():
    """Bookable start times on one date for a given duration."""
    try:
        d = datetime.strptime(request.args.get('date', ''), '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'slots': []})
    slots = Availability().slots(d, _duration_arg())
    return jsonify({'slots': [{'value': t.strftime('%H:%M'), 'label': fmt_time(t)} for t in slots]})


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
        layout = e.layout_info()
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
                'layout_label': f"{layout['label']} ({layout['seats']} seats)" if layout else '',
                'layout_image': url_for('static', filename=layout['image']) if layout else '',
                'grand_total': float(e.grand_total) if e.grand_total is not None else None,
                'deposit_amount': float(e.deposit_amount) if e.deposit_amount is not None else None,
            },
        })
    return jsonify(output)


@app.route('/admin/pending')
@login_required
def admin_pending():
    pending_events = Event.query.filter_by(status='pending').order_by(Event.created_at.desc()).all()
    conflicts = {e.id: event_conflicts(e) for e in pending_events}
    return render_template('pending.html', events=pending_events, conflicts=conflicts)


@app.route('/admin/events/<int:event_id>/approve', methods=['POST'])
@login_required
def approve_event(event_id):
    event = Event.query.get_or_404(event_id)
    clash = event_conflicts(event)
    if clash:
        flash(f'Cannot approve "{event.title}": it overlaps the approved event "{clash[0].title}".', 'error')
        return redirect(url_for('admin_pending'))
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


# --- Availability management ------------------------------------------------

@app.route('/admin/availability')
@login_required
def admin_availability():
    ensure_default_weekly_hours()
    weekly = WeeklyHours.query.order_by(WeeklyHours.weekday).all()
    overrides = DateOverride.query.filter(DateOverride.date >= date.today()).order_by(DateOverride.date).all()
    return render_template(
        'availability.html', weekly=weekly, overrides=overrides,
        day_names=DAY_NAMES, today=date.today().isoformat(),
    )


@app.route('/admin/availability/weekly', methods=['POST'])
@login_required
def save_weekly_hours():
    ensure_default_weekly_hours()
    rows = WeeklyHours.query.order_by(WeeklyHours.weekday).all()
    updates = []
    for w in rows:
        enabled = request.form.get(f'enabled_{w.weekday}') == 'on'
        o = parse_hhmm(request.form.get(f'open_{w.weekday}'))
        c = parse_hhmm(request.form.get(f'close_{w.weekday}'))
        if enabled and (not o or not c or c <= o):
            flash(f'{DAY_NAMES[w.weekday]}: closing time must be after opening time.', 'error')
            return redirect(url_for('admin_availability'))
        updates.append((w, enabled, o, c))
    for w, enabled, o, c in updates:
        w.enabled, w.open_time, w.close_time = enabled, o or w.open_time, c or w.close_time
    db.session.commit()
    flash('Weekly hours saved.', 'success')
    return redirect(url_for('admin_availability'))


@app.route('/admin/availability/override', methods=['POST'])
@login_required
def add_date_override():
    try:
        d = datetime.strptime(request.form.get('date', ''), '%Y-%m-%d').date()
    except ValueError:
        flash('Please choose a valid date.', 'error')
        return redirect(url_for('admin_availability'))
    closed = request.form.get('mode', 'closed') == 'closed'
    o = parse_hhmm(request.form.get('open_time'))
    c = parse_hhmm(request.form.get('close_time'))
    if not closed and (not o or not c or c <= o):
        flash('For custom hours, closing time must be after opening time.', 'error')
        return redirect(url_for('admin_availability'))

    ov = DateOverride.query.filter_by(date=d).first() or DateOverride(date=d)
    ov.is_closed = closed
    ov.open_time, ov.close_time = (None, None) if closed else (o, c)
    ov.note = (request.form.get('note') or '').strip()[:200] or None
    db.session.add(ov)
    db.session.commit()
    flash(f'Saved {"closure" if closed else "custom hours"} for {d.isoformat()}.', 'success')
    return redirect(url_for('admin_availability'))


@app.route('/admin/availability/override/<int:override_id>/delete', methods=['POST'])
@login_required
def delete_date_override(override_id):
    ov = DateOverride.query.get_or_404(override_id)
    db.session.delete(ov)
    db.session.commit()
    flash('Date override removed; that day follows the weekly hours again.', 'success')
    return redirect(url_for('admin_availability'))


# --- Admin accounts -----------------------------------------------------------

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
    """Create all database tables and seed default hours. Run: flask init-db"""
    db.create_all()
    ensure_default_weekly_hours()
    print('Database tables created (and default weekly hours seeded if none existed).')


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
