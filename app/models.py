from app import db
from flask_login import UserMixin
from datetime import datetime
import secrets


class User(UserMixin, db.Model):
    __tablename__ = 'user'

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80), unique=True, nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    display_name  = db.Column(db.String(100), nullable=False)
    avatar        = db.Column(db.String(10), default='🐱')
    bio           = db.Column(db.String(200), default='')

    # Notification preferences
    notif_availability    = db.Column(db.Boolean, default=True)
    notif_best_time       = db.Column(db.Boolean, default=True)
    notif_room_invites    = db.Column(db.Boolean, default=True)
    notif_friend_requests = db.Column(db.Boolean, default=True)
    notif_deadlines       = db.Column(db.Boolean, default=False)

    # Privacy settings
    allow_friend_requests = db.Column(db.Boolean, default=True)
    public_profile        = db.Column(db.Boolean, default=False)

    # Relationships
    rooms_created     = db.relationship('Room', backref='organiser', lazy=True)
    participations    = db.relationship('RoomParticipant', backref='user', lazy=True, cascade='all, delete-orphan')
    availabilities    = db.relationship('Availability', backref='user', lazy=True, cascade='all, delete-orphan')
    notifications     = db.relationship('Notification', backref='user', lazy=True, cascade='all, delete-orphan')
    personal_schedule = db.relationship('PersonalSchedule', backref='user', lazy=True, cascade='all, delete-orphan')
    friendships_sent  = db.relationship('Friendship', foreign_keys='Friendship.user1_id', backref='sender', lazy=True, cascade='all, delete-orphan')
    friendships_recv  = db.relationship('Friendship', foreign_keys='Friendship.user2_id', backref='receiver', lazy=True, cascade='all, delete-orphan')

    @property
    def xp(self):
        rooms_created  = len(self.rooms_created) * 50
        availabilities = len(self.availabilities) * 20
        friendships    = len([f for f in self.friendships_sent if f.status == 'accepted']) * 10
        return rooms_created + availabilities + friendships

    @property
    def level(self):
        if self.xp < 100:    return 1
        elif self.xp < 250:  return 2
        elif self.xp < 500:  return 3
        elif self.xp < 800:  return 4
        elif self.xp < 1200: return 5
        elif self.xp < 1700: return 6
        elif self.xp < 2300: return 7
        elif self.xp < 3000: return 8
        elif self.xp < 4000: return 9
        else:                return 10

    @property
    def xp_max(self):
        thresholds = [100, 250, 500, 800, 1200, 1700, 2300, 3000, 4000, 5000]
        return thresholds[self.level - 1]

    @property
    def level_title(self):
        titles = ['Newcomer', 'Scheduler', 'Organiser', 'Planner', 'Coordinator',
                  'Strategist', 'Pro Planner', 'Director', 'Mastermind', 'Legend']
        return titles[self.level - 1]

    @property
    def meets_count(self):
        # Count distinct confirmed rooms this user submitted availability for
        confirmed_room_ids = {
            a.room_id for a in self.availabilities
            if a.room and a.room.confirmed_slot is not None
        }
        return len(confirmed_room_ids)

    @property
    def total_rooms(self):
        invited_count = RoomParticipant.query.filter_by(
            user_id=self.id
        ).filter(
            RoomParticipant.room_id.notin_([r.id for r in self.rooms_created])
        ).count()
        return len(self.rooms_created) + invited_count


class Room(db.Model):
    __tablename__ = 'room'

    id             = db.Column(db.Integer, primary_key=True)
    code           = db.Column(db.String(10), unique=True, nullable=False, default=lambda: secrets.token_urlsafe(6))
    title          = db.Column(db.String(100), nullable=False)
    description    = db.Column(db.String(500), default='')
    date_from      = db.Column(db.Date, nullable=False)
    date_to        = db.Column(db.Date, nullable=False)
    selected_dates = db.Column(db.String(500), nullable=True)
    time_start     = db.Column(db.String(20), nullable=False)
    time_end       = db.Column(db.String(20), nullable=False)
    duration       = db.Column(db.String(20), nullable=False)
    deadline       = db.Column(db.Date, nullable=True)
    confirmed_slot = db.Column(db.String(50), nullable=True)
    suggested_slot = db.Column(db.String(50), nullable=True)
    organiser_id   = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Relationships
    participants   = db.relationship('RoomParticipant', backref='room', lazy=True)
    availabilities = db.relationship('Availability', backref='room', lazy=True)


class RoomParticipant(db.Model):
    __tablename__ = 'room_participant'

    id      = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # invited  = just added to room
    # awaiting = has submitted availability
    # confirmed = organiser has confirmed a time slot
    status  = db.Column(db.String(20), default='invited')


class Availability(db.Model):
    __tablename__ = 'availability'

    id        = db.Column(db.Integer, primary_key=True)
    room_id   = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    user_id   = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    time_slot = db.Column(db.String(20), nullable=False)
    status    = db.Column(db.String(10), nullable=False)  # free, maybe, busy


class PersonalSchedule(db.Model):
    __tablename__ = 'personal_schedule'

    id        = db.Column(db.Integer, primary_key=True)
    user_id   = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    day       = db.Column(db.String(10), nullable=False)   # Mon, Tue, Wed etc.
    time_slot = db.Column(db.String(20), nullable=False)   # e.g. 9:00 AM
    status    = db.Column(db.String(10), nullable=False)   # free, maybe, busy


class Friendship(db.Model):
    __tablename__ = 'friendship'

    id       = db.Column(db.Integer, primary_key=True)
    user1_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user2_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # pending  = request sent, not yet accepted
    # accepted = both users are friends
    status   = db.Column(db.String(20), default='pending')


class Notification(db.Model):
    __tablename__ = 'notification'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # availability   = someone submitted availability to your room
    # invite         = you've been invited to a room
    # friend_request = someone sent you a friend request
    # best_time      = organiser confirmed a time slot
    # deadline       = room deadline reminder
    type       = db.Column(db.String(30), nullable=False)
    message    = db.Column(db.String(300), nullable=False)
    is_read    = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)