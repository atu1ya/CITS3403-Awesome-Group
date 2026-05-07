from flask import Blueprint, render_template, redirect, url_for, request, jsonify, session, abort, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from datetime import date, datetime, timedelta
from app import db
from app.models import (
    User, Room, RoomParticipant,
    Availability, Notification, Friendship, PersonalSchedule,
)
import secrets

main = Blueprint('main', __name__)


# ════════════════════════════════════════════════════════════════
#  Helpers
# ════════════════════════════════════════════════════════════════

def validate_password(password):
    """Return an error string, or None if the password is valid."""
    if len(password) < 8:
        return 'Password must be at least 8 characters.'
    if not any(c.isupper() for c in password):
        return 'Password must contain at least one uppercase letter.'
    if not any(c.isdigit() for c in password):
        return 'Password must contain at least one number.'
    if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password):
        return 'Password must contain at least one special character.'
    return None


def generate_time_slots(start, end):
    """Return a list of 30-min slot labels between start and end (e.g. '9:00 AM')."""
    def parse_hour(s):
        time_part, period = s.split(' ')
        h, m = map(int, time_part.split(':'))
        if period == 'PM' and h != 12:
            h += 12
        if period == 'AM' and h == 12:
            h = 0
        return h, m

    slots = []
    sh, sm = parse_hour(start)
    eh, em = parse_hour(end)
    cur_h, cur_m = sh, sm

    while (cur_h, cur_m) < (eh, em):
        period    = 'AM' if cur_h < 12 else 'PM'
        display_h = cur_h if cur_h <= 12 else cur_h - 12
        if display_h == 0:
            display_h = 12
        slots.append(f"{display_h}:{str(cur_m).zfill(2)} {period}")
        cur_m += 30
        if cur_m >= 60:
            cur_m  = 0
            cur_h += 1

    return slots


def cleanup_expired_rooms():
    """Delete rooms whose date_to is in the past, along with their child rows."""
    expired = Room.query.filter(Room.date_to < date.today()).all()
    for room in expired:
        Availability.query.filter_by(room_id=room.id).delete()
        RoomParticipant.query.filter_by(room_id=room.id).delete()
        db.session.delete(room)
    if expired:
        db.session.commit()


# ════════════════════════════════════════════════════════════════
#  Public pages
# ════════════════════════════════════════════════════════════════

@main.route('/')
def index():
    return render_template('index.html')


# ════════════════════════════════════════════════════════════════
#  Auth – sign-up, email verification, login, logout
# ════════════════════════════════════════════════════════════════

@main.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        display_name = request.form.get('display_name', '').strip()
        username     = request.form.get('username', '').strip()
        email        = request.form.get('email', '').strip()
        password     = request.form.get('password', '').strip()
        confirm      = request.form.get('confirm', '').strip()

        def re_render(error):
            return render_template('signup.html',
                error=error, display_name=display_name,
                username=username, email=email)

        if not all([display_name, username, email, password, confirm]):
            return re_render('Please fill in all fields.')

        pwd_error = validate_password(password)
        if pwd_error:
            return re_render(pwd_error)

        if password != confirm:
            return re_render('Passwords do not match.')

        if User.query.filter_by(username=username).first():
            return re_render('Username already taken.')

        if User.query.filter_by(email=email).first():
            return re_render('Email already registered.')

        code = str(secrets.randbelow(900000) + 100000)
        session['pending_verification'] = {
            'code':         code,
            'email':        email,
            'display_name': display_name,
            'username':     username,
            'password':     password,
            'attempts':     0,
        }
        _send_verification_email(email, display_name, code)
        return redirect(url_for('main.verify_email'))

    return render_template('signup.html')


@main.route('/verify-email', methods=['GET', 'POST'])
def verify_email():
    pending = session.get('pending_verification')
    if not pending:
        return redirect(url_for('main.signup'))

    email = pending['email']
    error = None

    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        if code == pending['code']:
            data = session.pop('pending_verification')
            new_user = User(
                username      = data['username'],
                email         = email,
                password_hash = generate_password_hash(data['password']),
                display_name  = data['display_name'],
            )
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('main.index'))
        else:
            pending['attempts'] = pending.get('attempts', 0) + 1
            session['pending_verification'] = pending
            if pending['attempts'] >= 5:
                session.pop('pending_verification')
                return redirect(url_for('main.signup'))
            remaining = 5 - pending['attempts']
            error = f'Invalid code. Please try again. ({remaining} attempt{"s" if remaining != 1 else ""} remaining)'

    return render_template('verify_email.html', email=email, error=error)


@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password   = request.form.get('password', '').strip()

        user = (User.query.filter_by(username=identifier).first()
                or User.query.filter_by(email=identifier).first())

        if not user or not check_password_hash(user.password_hash, password):
            return render_template('login.html', error='Invalid username or password.')

        login_user(user, remember=request.form.get('remember') == 'on')
        return redirect(url_for('main.index'))

    return render_template('login.html')


@main.route('/logout')
@login_required
def logout():
    logout_user()
    response = make_response(redirect(url_for('main.index')))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


# ════════════════════════════════════════════════════════════════
#  Auth – password reset
# ════════════════════════════════════════════════════════════════

@main.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    error = None
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        user  = User.query.filter_by(email=email).first()
        if not user:
            error = 'No account found with that email.'
        else:
            code = str(secrets.randbelow(900000) + 100000)
            session['pending_reset'] = {
                'code':     code,
                'email':    email,
                'attempts': 0,
            }
            _send_password_reset_email(email, user.display_name, code)
            return redirect(url_for('main.reset_password'))

    return render_template('forgot_password.html', error=error)


@main.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    pending = session.get('pending_reset')
    if not pending:
        return redirect(url_for('main.forgot_password'))

    email = pending['email']
    error = None
    code  = None

    if request.method == 'POST':
        code     = request.form.get('code', '').strip()
        password = request.form.get('password', '').strip()
        confirm  = request.form.get('confirm', '').strip()

        if code != pending['code']:
            pending['attempts'] = pending.get('attempts', 0) + 1
            session['pending_reset'] = pending
            if pending['attempts'] >= 5:
                session.pop('pending_reset')
                return redirect(url_for('main.forgot_password'))
            remaining = 5 - pending['attempts']
            error = f'Invalid code. Please try again. ({remaining} attempt{"s" if remaining != 1 else ""} remaining)'
            code  = None
        elif validate_password(password):
            error = validate_password(password)
        elif password != confirm:
            error = 'Passwords do not match.'
        else:
            user = User.query.filter_by(email=email).first()
            user.password_hash = generate_password_hash(password)
            session.pop('pending_reset')
            db.session.commit()
            return redirect(url_for('main.login'))

    return render_template('reset_password.html', email=email, error=error, code=code)


# ════════════════════════════════════════════════════════════════
#  Stub routes — to be replaced by other team members
# ════════════════════════════════════════════════════════════════

# TODO: Replace with full create event + availability routes — Person 2 (feature/rooms)
@main.route('/create-event')
@login_required
def create_event():
    return render_template('create_event.html')

# TODO: Replace with full dashboard route — Person 3 (feature/results)
@main.route('/dashboard')
@login_required
def dashboard():
    return redirect(url_for('main.index'))

# TODO: Replace with full results routes — Person 3 (feature/results)
@main.route('/results')
@login_required
def results():
    return redirect(url_for('main.index'))

# TODO: Replace with full friends routes — Person 4 (feature/social)
@main.route('/friends')
@login_required
def friends():
    return redirect(url_for('main.index'))

# TODO: Replace with full notifications routes — Person 4 (feature/social)
@main.route('/notifications')
@login_required
def notifications():
    return redirect(url_for('main.index'))

# TODO: Replace with full schedule routes — Person 4 (feature/social)
@main.route('/schedule')
@login_required
def schedule():
    return redirect(url_for('main.index'))

# TODO: Replace with full settings routes — Person 4 (feature/social)
@main.route('/settings')
@login_required
def settings():
    return redirect(url_for('main.index'))


# ════════════════════════════════════════════════════════════════
#  Private helpers (email sending)
# ════════════════════════════════════════════════════════════════

def _send_verification_email(email, display_name, code):
    from flask_mail import Message
    from app import mail
    msg = Message(
        subject    = 'SmartMeet – Verify your email',
        recipients = [email],
    )
    msg.body = (
        f'Hi {display_name},\n\n'
        f'Your SmartMeet verification code is: {code}\n\n'
        f'Enter this code to complete your sign up.\n\n'
        f'The SmartMeet Team'
    )
    mail.send(msg)


def _send_password_reset_email(email, display_name, code):
    from flask_mail import Message
    from app import mail
    msg = Message(
        subject    = 'SmartMeet – Password Reset Code',
        recipients = [email],
    )
    msg.body = (
        f'Hi {display_name},\n\n'
        f'Your SmartMeet password reset code is: {code}\n\n'
        f'If you did not request this, ignore this email.\n\n'
        f'The SmartMeet Team'
    )
    mail.send(msg)