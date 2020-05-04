import os
from flask import Flask

DATABASE_FILE = 'opteyes.db'


# application factory
def create_app(test_config=None):
    # create our little application :)
    app = Flask(__name__)

    # Load default config and override config from an environment variable
    app.config.from_mapping(
        DATABASE=os.path.join(app.root_path, DATABASE_FILE),
        DEBUG=False,
        SECRET_KEY='development key',
        DATA_DIR=os.path.join(app.root_path, 'data'),
    )
    app.config.from_envvar('FLASKR_SETTINGS', silent=True)
    if test_config:
        app.config.from_mapping(test_config)

    from . import db
    db.init_app(app)

    from . import api
    app.register_blueprint(api.bp)

    return app
