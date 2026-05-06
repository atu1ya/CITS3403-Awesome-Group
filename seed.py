from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    if not User.query.filter_by(username='testuser').first():
        user = User(
            username='testuser',
            email='test@smartmeet.com',
            password_hash=generate_password_hash('Test123!'),
            display_name='Test User',
        )
        db.session.add(user)
        db.session.commit()
        print('Test account created.')
    else:
        print('Test account already exists, skipping.')

# Username: testuser
# Password: Test123!