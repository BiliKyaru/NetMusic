# run.py
from dotenv import load_dotenv
load_dotenv()

from webapp import create_app
from webapp.extensions import db, socketio

app = create_app()

def init_db():
    with app.app_context():
        db.create_all()

init_db()

if __name__ == '__main__':
    socketio.run(app,
                 host='0.0.0.0',
                 port=3355,
                 debug=True,
                 allow_unsafe_werkzeug=True)