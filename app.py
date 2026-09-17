import os
from datetime import datetime

from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import StringField, TextAreaField, DateField, TimeField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo
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

    reviewer = db.relationship('Admin', foreign_keys=[reviewed_by])


@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))


# ---------------------------------------------------------------------------
# Forms
# ---------------------------------------------------------------------------

class EventSubmissionForm(FlaskForm):
    title = StringField('Event Title', validators=[DataRequired(), Length(max=150)])
    description = TextAreaField('Description', validators=[Length(max=2000)])
    submitter_name = StringField('Your Name', validators=[DataRequired(), Length(max=120)])
    submitter_email = StringField('Your Email', validators=[DataRequired(), Email(), Length(max=120)])
    event_date = DateField('Event Date', validators=[DataRequired()])
    event_time = TimeField('Event Time', validators=[])
    location = StringField('Location', validators=[Length(max=200)])
    submit = SubmitField('Submit Event')


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
        event = Event(
            title=form.title.data,
            description=form.description.data,
            submitter_name=form.submitter_name.data,
            submitter_email=form.submitter_email.data,
            event_date=form.event_date.data,
            event_time=form.event_time.data,
            location=form.location.data,
            status='pending',
        )
        db.session.add(event)
        db.session.commit()
        flash('Thanks! Your event was submitted and is awaiting admin approval.', 'success')
        return redirect(url_for('submit_event'))
    return render_template('submit.html', form=form)


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
