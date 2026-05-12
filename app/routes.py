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
@main.route('/create-event', methods=['GET', 'POST'])
@login_required
def create_event():
    if request.method == 'POST':
        title        = request.form.get('roomName', '').strip()
        description  = request.form.get('roomDesc', '').strip()
        date_from    = request.form.get('dateFrom')
        date_to      = request.form.get('dateTo')
        time_start   = request.form.get('timeStart')
        time_end     = request.form.get('timeEnd')
        duration     = request.form.get('duration')
        deadline_str = request.form.get('deadline')
        deadline     = (datetime.strptime(deadline_str, '%Y-%m-%d').date()
                        if deadline_str else None)

        selected_dates = request.form.get('selectedDates', '')
        if not selected_dates:
            d, end_d = (datetime.strptime(date_from, '%Y-%m-%d').date(),
                        datetime.strptime(date_to,   '%Y-%m-%d').date())
            dates = []
            while d <= end_d:
                dates.append(d.strftime('%Y-%m-%d'))
                d += timedelta(days=1)
            selected_dates = ','.join(dates)

        room = Room(
            title          = title,
            description    = description,
            date_from      = datetime.strptime(date_from, '%Y-%m-%d').date(),
            date_to        = datetime.strptime(date_to,   '%Y-%m-%d').date(),
            time_start     = time_start,
            time_end       = time_end,
            duration       = duration,
            organiser_id   = current_user.id,
            selected_dates = selected_dates,
            deadline       = deadline,
        )
        db.session.add(room)
        db.session.commit()
        return redirect(url_for('main.availability', code=room.code))

    return render_template('create_event.html', user=current_user)

@main.route('/availability')
@main.route('/availability/<code>')
@login_required
def availability(code=None):
    room           = None
    time_slots     = []
    existing       = {}
    selected_dates = []

    if code:
        room = Room.query.filter_by(code=code).first_or_404()

        if room.confirmed_slot:
            return redirect(url_for('main.results', code=code))

        if room.organiser_id != current_user.id:
            existing_participant = RoomParticipant.query.filter_by(
                room_id=room.id, user_id=current_user.id
            ).first()
            if not existing_participant:
                db.session.add(RoomParticipant(
                    room_id=room.id, user_id=current_user.id, status='invited'
                ))
                if current_user.notif_room_invites:
                    db.session.add(Notification(
                        user_id=current_user.id, type='invite',
                        message=(f'You have been invited to "{room.title}"'
                                 f' by {room.organiser.display_name}.'),
                    ))
                db.session.commit()

        time_slots = generate_time_slots(room.time_start, room.time_end)

        if room.selected_dates:
            selected_dates = [
                datetime.strptime(d.strip(), '%Y-%m-%d').date()
                for d in room.selected_dates.split(',')
            ]

        existing = {
            a.time_slot: a.status
            for a in Availability.query.filter_by(
                room_id=room.id, user_id=current_user.id
            ).all()
        }

    personal_schedule = {
        f"{ps.day}|{ps.time_slot}": ps.status
        for ps in current_user.personal_schedule
    }

    return render_template('availability.html',
                           user=current_user,
                           room=room,
                           time_slots=time_slots,
                           timedelta=timedelta,
                           existing=existing,
                           selected_dates=selected_dates,
                           personal_schedule=personal_schedule)

@main.route('/availability/<code>/submit', methods=['POST'])
@login_required
def submit_availability(code):
    room = Room.query.filter_by(code=code).first_or_404()

    is_organiser   = room.organiser_id == current_user.id
    is_participant = RoomParticipant.query.filter_by(
        room_id=room.id, user_id=current_user.id
    ).first() is not None

    if not is_organiser and not is_participant:
        abort(403)

    if room.confirmed_slot:
        return redirect(url_for('main.results', code=code))

    Availability.query.filter_by(room_id=room.id, user_id=current_user.id).delete()

    for key, value in request.form.items():
        if key.startswith('tile_') and value in ('free', 'maybe', 'busy'):
            parts    = key.split('_')
            date_str = parts[1]
            hour, minute, period = parts[2], parts[3], parts[4]
            slot = f"{date_str} {hour}:{minute} {period}"
            db.session.add(Availability(
                room_id=room.id, user_id=current_user.id,
                time_slot=slot, status=value,
            ))

    db.session.flush()
    tiles_saved = Availability.query.filter_by(
        room_id=room.id, user_id=current_user.id
    ).count()

    if room.organiser_id != current_user.id:
        participant = RoomParticipant.query.filter_by(
            room_id=room.id, user_id=current_user.id
        ).first()
        if participant:
            participant.status = 'awaiting' if tiles_saved > 0 else 'invited'
        elif tiles_saved > 0:
            db.session.add(RoomParticipant(
                room_id=room.id, user_id=current_user.id, status='awaiting'
            ))

    if room.organiser_id != current_user.id and tiles_saved > 0:
        organiser = User.query.get(room.organiser_id)
        if organiser.notif_availability:
            db.session.add(Notification(
                user_id=room.organiser_id, type='availability',
                message=(f'{current_user.display_name} has submitted their'
                         f' availability for "{room.title}".'),
            ))

    db.session.commit()
    return redirect(url_for('main.dashboard'))

# TODO: Replace with full dashboard route — Person 3 (feature/results)
@main.route('/dashboard')
@login_required
def dashboard():
    cleanup_expired_rooms()
    rooms_created = Room.query.filter_by(organiser_id=current_user.id).all()
    created_ids   = [r.id for r in rooms_created]
    rooms_invited = RoomParticipant.query.filter_by(
        user_id=current_user.id
    ).filter(
        RoomParticipant.room_id.notin_(created_ids)
    ).all()
    return render_template('dashboard.html',
                           user=current_user,
                           rooms_created=rooms_created,
                           rooms_invited=rooms_invited)


# ════════════════════════════════════════════════════════════════
#  Results
# ════════════════════════════════════════════════════════════════

@main.route('/results')
@main.route('/results/<code>')
@login_required
def results(code=None):
    room              = None
    heatmap           = {}
    best_slots        = []
    top_slot          = None
    participants_data = []
    is_organiser      = False
    total_users       = 0
    time_slots        = []
    selected_dates    = []

    if code:
        room = Room.query.filter_by(code=code).first_or_404()

        is_organiser   = room.organiser_id == current_user.id
        is_participant = RoomParticipant.query.filter_by(
            room_id=room.id, user_id=current_user.id
        ).first() is not None

        if not is_organiser and not is_participant:
            abort(403)

        time_slots = generate_time_slots(room.time_start, room.time_end)

        if room.selected_dates:
            selected_dates = [
                datetime.strptime(d.strip(), '%Y-%m-%d').date()
                for d in room.selected_dates.split(',')
            ]

        total_users = len(set(a.user_id for a in room.availabilities))

        for a in room.availabilities:
            heatmap.setdefault(a.time_slot, 0)
            if a.status == 'free':
                heatmap[a.time_slot] += 1
            elif a.status == 'maybe':
                heatmap[a.time_slot] += 0.5

        def _slot_sort_key(item):
            slot, score = item
            try:
                dt = datetime.strptime(slot, '%Y-%m-%d %I:%M %p')
            except ValueError:
                dt = datetime.max
            return (-score, dt)

        best_slots = sorted(heatmap.items(), key=_slot_sort_key)[:3]

        selected_param = request.args.get('selected')
        if room.confirmed_slot and room.confirmed_slot in heatmap:
            top_slot = (room.confirmed_slot, heatmap[room.confirmed_slot])
        elif room.suggested_slot and room.suggested_slot in heatmap:
            top_slot = (room.suggested_slot, heatmap[room.suggested_slot])
        elif selected_param and selected_param in heatmap:
            top_slot = (selected_param, heatmap[selected_param])
        elif best_slots:
            top_slot = best_slots[0]

        organiser       = User.query.get(room.organiser_id)
        organiser_avail = Availability.query.filter_by(
            room_id=room.id, user_id=room.organiser_id
        ).all()
        participants_data.append({
            'user':       organiser,
            'role':       'Organiser',
            'responded':  len(organiser_avail) > 0,
            'free_count': sum(1 for a in organiser_avail if a.status == 'free'),
        })
        for rp in room.participants:
            if rp.user_id == room.organiser_id:
                continue
            user_avail = Availability.query.filter_by(
                room_id=room.id, user_id=rp.user_id
            ).all()
            participants_data.append({
                'user':       rp.user,
                'role':       'Participant',
                'responded':  rp.status in ('awaiting', 'confirmed'),
                'free_count': sum(1 for a in user_avail if a.status == 'free'),
            })

    return render_template('results.html',
                           user=current_user,
                           room=room,
                           heatmap=heatmap,
                           best_slots=best_slots,
                           top_slot=top_slot,
                           participants_data=participants_data,
                           is_organiser=is_organiser,
                           total_users=total_users,
                           time_slots=time_slots,
                           selected_dates=selected_dates,
                           timedelta=timedelta)


# ════════════════════════════════════════════════════════════════
#  Confirm Time
# ════════════════════════════════════════════════════════════════

@main.route('/results/<code>/confirm', methods=['POST'])
@login_required
def confirm_time(code):
    room = Room.query.filter_by(code=code).first_or_404()
    if room.organiser_id != current_user.id:
        return redirect(url_for('main.results', code=code))

    room.confirmed_slot = request.form.get('confirmed_slot')

    for rp in room.participants:
        rp.status = 'confirmed'
        if rp.user.notif_best_time:
            db.session.add(Notification(
                user_id=rp.user_id, type='confirmed',
                message=(f'A meeting time has been confirmed for'
                         f' "{room.title}": {room.confirmed_slot}'),
            ))

    db.session.commit()
    return redirect(url_for('main.results', code=code))


# ════════════════════════════════════════════════════════════════
#  Notify Participants
# ════════════════════════════════════════════════════════════════

@main.route('/results/<code>/notify', methods=['POST'])
@login_required
def notify_participants(code):
    room = Room.query.filter_by(code=code).first_or_404()
    if room.organiser_id != current_user.id:
        return redirect(url_for('main.results', code=code))

    notify_slot = request.form.get('notify_slot', room.confirmed_slot or '')

    for rp in room.participants:
        if rp.user.notif_best_time:
            if room.confirmed_slot:
                msg        = f'A meeting time has been confirmed for "{room.title}": {notify_slot}'
                notif_type = 'confirmed'
            else:
                msg        = f'Best time found for "{room.title}"! Suggested time: {notify_slot}'
                notif_type = 'best_time'
            db.session.add(Notification(
                user_id=rp.user_id, type=notif_type, message=msg
            ))

    room.suggested_slot = notify_slot
    db.session.commit()
    return redirect(url_for('main.results', code=code, notified=1, selected=notify_slot))


# ════════════════════════════════════════════════════════════════
#  Remind Participant
# ════════════════════════════════════════════════════════════════

@main.route('/results/<code>/remind/<int:user_id>', methods=['POST'])
@login_required
def remind_participant(code, user_id):
    room = Room.query.filter_by(code=code).first_or_404()
    if room.organiser_id != current_user.id:
        return redirect(url_for('main.results', code=code))

    db.session.add(Notification(
        user_id=user_id, type='invite',
        message=(f'⏰ Reminder: Please submit your availability for'
                 f' "{room.title}" before it\'s too late!'),
    ))
    db.session.commit()
    return redirect(url_for('main.results', code=code, reminded=1))

# ════════════════════════════════════════════════════════════════
#  Friends
# ════════════════════════════════════════════════════════════════

@main.route('/friends')
@login_required
def friends():
    accepted = Friendship.query.filter(
        (Friendship.user1_id == current_user.id) | (Friendship.user2_id == current_user.id),
        Friendship.status == 'accepted',
    ).all()
    pending_received = Friendship.query.filter_by(
        user2_id=current_user.id, status='pending'
    ).all()
    pending_sent = Friendship.query.filter_by(
        user1_id=current_user.id, status='pending'
    ).all()
    return render_template('friends.html',
                           user=current_user,
                           friends=accepted,
                           pending_received=pending_received,
                           pending_sent=pending_sent)


@main.route('/friends/add', methods=['POST'])
@login_required
def send_friend_request():
    username = request.form.get('username', '').strip()
    target   = User.query.filter_by(username=username).first()

    if not target:
        return redirect(url_for('main.friends', error='User not found.'))
    if target.id == current_user.id:
        return redirect(url_for('main.friends', error='You cannot add yourself.'))

    existing = Friendship.query.filter(
        ((Friendship.user1_id == current_user.id) & (Friendship.user2_id == target.id)) |
        ((Friendship.user1_id == target.id)       & (Friendship.user2_id == current_user.id))
    ).first()
    if existing:
        return redirect(url_for('main.friends', error='Friend request already exists.'))
    if not target.allow_friend_requests:
        return redirect(url_for('main.friends',
                                error=f'{target.display_name} is not accepting friend requests.'))

    db.session.add(Friendship(
        user1_id=current_user.id, user2_id=target.id, status='pending'
    ))
    if target.notif_friend_requests:
        db.session.add(Notification(
            user_id=target.id, type='friend',
            message=f'{current_user.display_name} sent you a friend request.',
        ))
    db.session.commit()
    return redirect(url_for('main.friends', success=f'Friend request sent to {target.display_name}!'))


@main.route('/friends/accept/<int:friendship_id>', methods=['POST'])
@login_required
def accept_friend(friendship_id):
    friendship = Friendship.query.get_or_404(friendship_id)
    if friendship.user2_id != current_user.id:
        return redirect(url_for('main.friends'))

    friendship.status = 'accepted'
    if friendship.sender.notif_friend_requests:
        db.session.add(Notification(
            user_id=friendship.user1_id, type='friend',
            message=f'{current_user.display_name} accepted your friend request!',
        ))
    db.session.commit()
    return redirect(url_for('main.friends'))


@main.route('/friends/decline/<int:friendship_id>', methods=['POST'])
@login_required
def decline_friend(friendship_id):
    friendship = Friendship.query.get_or_404(friendship_id)
    if friendship.user2_id != current_user.id:
        return redirect(url_for('main.friends'))
    db.session.delete(friendship)
    db.session.commit()
    return redirect(url_for('main.friends'))


@main.route('/friends/cancel/<int:friendship_id>', methods=['POST'])
@login_required
def cancel_friend_request(friendship_id):
    friendship = Friendship.query.get_or_404(friendship_id)
    if friendship.user1_id != current_user.id:
        return redirect(url_for('main.friends'))
    db.session.delete(friendship)
    db.session.commit()
    return redirect(url_for('main.friends'))


@main.route('/friends/remove/<int:friendship_id>', methods=['POST'])
@login_required
def remove_friend(friendship_id):
    friendship = Friendship.query.get_or_404(friendship_id)
    if friendship.user1_id != current_user.id and friendship.user2_id != current_user.id:
        return redirect(url_for('main.friends'))
    db.session.delete(friendship)
    db.session.commit()
    return redirect(url_for('main.friends'))


@main.route('/users/search')
@login_required
def search_users():
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify({'users': []})
    users = User.query.filter(
        (User.username.ilike(f'%{query}%')) | (User.display_name.ilike(f'%{query}%'))
    ).filter(User.id != current_user.id).limit(8).all()
    return jsonify({'users': [
        {'username': u.username, 'display_name': u.display_name,
         'avatar': u.avatar, 'public_profile': u.public_profile}
        for u in users
    ]})

# ════════════════════════════════════════════════════════════════
#  Notifications
# ════════════════════════════════════════════════════════════════

@main.route('/notifications')
@login_required
def notifications():
    return render_template('notifications.html', user=current_user)


@main.route('/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_read():
    for notif in current_user.notifications:
        notif.is_read = True
    db.session.commit()
    return redirect(url_for('main.notifications'))


@main.route('/notifications/<int:notif_id>/read', methods=['POST'])
@login_required
def mark_read(notif_id):
    notif = Notification.query.get_or_404(notif_id)
    if notif.user_id == current_user.id:
        notif.is_read = True
        db.session.commit()
    return redirect(url_for('main.notifications'))

# ════════════════════════════════════════════════════════════════
#  Schedule
# ════════════════════════════════════════════════════════════════

@main.route('/schedule')
@main.route('/schedule/<username>')
@login_required
def schedule(username=None):
    viewed_user = None
    target_user = current_user

    if username:
        viewed_user = User.query.filter_by(username=username).first_or_404()
        target_user = viewed_user

    existing = {
        f"{e.day}|{e.time_slot}": e.status
        for e in PersonalSchedule.query.filter_by(user_id=target_user.id).all()
    }

    return render_template('schedule.html',
                           user=current_user,
                           viewed_user=viewed_user,
                           existing=existing)


@main.route('/schedule/save', methods=['POST'])
@login_required
def save_schedule():
    import json
    entries = json.loads(request.form.get('schedule_data', '[]'))

    PersonalSchedule.query.filter_by(user_id=current_user.id).delete()
    for entry in entries:
        db.session.add(PersonalSchedule(
            user_id=current_user.id,
            day=entry['day'],
            time_slot=entry['slot'],
            status=entry['status'],
        ))

    db.session.commit()
    return redirect(url_for('main.schedule', saved=1))

# ════════════════════════════════════════════════════════════════
#  Settings
# ════════════════════════════════════════════════════════════════

@main.route('/settings')
@login_required
def settings():
    return render_template('settings.html', user=current_user)


@main.route('/settings/save', methods=['POST'])
@login_required
def save_profile():
    current_user.display_name = request.form.get('display_name', '').strip()
    current_user.bio          = request.form.get('bio', '').strip()
    current_user.avatar       = request.form.get('avatar', '').strip()

    new_username = request.form.get('username', '').strip()
    if new_username != current_user.username:
        if User.query.filter_by(username=new_username).first():
            return redirect(url_for('main.settings', error='Username already taken'))
        current_user.username = new_username

    db.session.commit()
    return redirect(url_for('main.settings', saved=1))


@main.route('/settings/notifications', methods=['POST'])
@login_required
def save_notification_preferences():
    current_user.notif_availability    = 'notif_availability'    in request.form
    current_user.notif_best_time       = 'notif_best_time'       in request.form
    current_user.notif_room_invites    = 'notif_room_invites'    in request.form
    current_user.notif_friend_requests = 'notif_friend_requests' in request.form
    current_user.notif_deadlines       = 'notif_deadlines'       in request.form
    db.session.commit()
    return redirect(url_for('main.settings', saved=1))


@main.route('/settings/privacy', methods=['POST'])
@login_required
def save_privacy_preferences():
    current_user.allow_friend_requests = 'allow_friend_requests' in request.form
    current_user.public_profile        = 'public_profile'        in request.form
    db.session.commit()
    return redirect(url_for('main.settings', saved=1))


@main.route('/settings/delete', methods=['POST'])
@login_required
def delete_account():
    user = current_user._get_current_object()
    logout_user()
    db.session.delete(user)
    db.session.commit()
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