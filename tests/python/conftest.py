import os
import shutil
import tempfile
import pytest

from webserver import create_app
from webserver.db import init_db, get_db


@pytest.fixture
def app():
    db_file, db_path = tempfile.mkstemp()
    data_dir = tempfile.mkdtemp()

    app = create_app({
        'TESTING': True,
        'DATABASE': db_path,
        'DATA_DIR': data_dir,
    })

    with app.app_context():
        init_db()
        yield app

    os.close(db_file)
    os.unlink(db_path)
    shutil.rmtree(data_dir)


@pytest.fixture
def client(app):
    return app.test_client()
