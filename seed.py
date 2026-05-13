from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash

app = create_app()

accounts = [
    {
        'username': 'testuser1',
        'email': 'test1@smartmeet.com',
        'password': 'Test123!',
        'display_name': 'Alice',
    },
    {
        'username': 'testuser2',
        'email': 'test2@smartmeet.com',
        'password': 'Test123!',
        'display_name': 'Bob',
    },
    {
        'username': 'testuser3',
        'email': 'test3@smartmeet.com',
        'password': 'Test123!',
        'display_name': 'Charlie',
    },
    {
        'username': 'testuser4',
        'email': 'test4@smartmeet.com',
        'password': 'Test123!',
        'display_name': 'Diana',
    },
]

with app.app_context():
    for account in accounts:
        if not User.query.filter_by(username=account['username']).first():
            user = User(
                username=account['username'],
                email=account['email'],
                password_hash=generate_password_hash(account['password']),
                display_name=account['display_name'],
            )
            db.session.add(user)
            print(f"Created account: {account['username']}")
        else:
            print(f"Account already exists, skipping: {account['username']}")
    db.session.commit()

# Test accounts (all use password: Test123!)
# testuser1 — display name: Alice
# testuser2 — display name: Bob
# testuser3 — display name: Charlie
# testuser4 — display name: Diana