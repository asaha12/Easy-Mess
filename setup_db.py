from app import db, User
from werkzeug.security import generate_password_hash
from app import app

with app.app_context():
    db.create_all()  # ensure tables exist

    # Add default manager
    manager_pw = generate_password_hash("manager123")  # no 'method' needed
    manager = User(name="Main Manager", username="manager1", password=manager_pw, role="manager", first_login=True)
    
    # Add sample boarders
    boarder1_pw = generate_password_hash("boarder123")
    boarder2_pw = generate_password_hash("boarder123")
    boarder1 = User(name="Boarder One", username="boarder1", password=boarder1_pw, role="boarder", first_login=True)
    boarder2 = User(name="Boarder Two", username="boarder2", password=boarder2_pw, role="boarder", first_login=True)

    # Add all users to DB
    db.session.add(manager)
    db.session.add(boarder1)
    db.session.add(boarder2)
    db.session.commit()

    print("Default manager and sample boarders added successfully!")
    print("Login credentials:")
    print("Manager -> username: manager1 | password: manager123")
    print("Boarder1 -> username: boarder1 | password: boarder123")
    print("Boarder2 -> username: boarder2 | password: boarder123")
