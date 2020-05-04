import click
import os

from sqlite3 import dbapi2 as sqlite3
from flask import current_app, g
from flask.cli import with_appcontext


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(initdb_command)
    app.cli.add_command(_sync_database_command)


@click.command('syncdb')
@with_appcontext
def _sync_database_command():
    data_dir = current_app.config.get('DATA_DIR')

    db = get_db()
    cur = db.cursor()

    print('syncing database...')
    # keep track of datasets and datapoints in file system so extra ones in db can be removed
    datasets = []
    datapoints = []

    it = os.scandir(data_dir)
    for dataset_dir in it:
        if not dataset_dir.is_dir():
            continue

        cur.execute('select * from datasets where path=(?)', [dataset_dir.path])
        ds_row = cur.fetchone()

        # make sure entry for dataset exists in dataset
        if ds_row is None:
            cur.execute('insert into datasets (name, path) values (?,?)',
                        [dataset_dir.name, dataset_dir.path])
            cur.execute('select last_insert_rowid();')
            dataset_id = cur.fetchone()[0]
            print('added dataset "{:s}", id={:d}'.format(dataset_dir.name, dataset_id))
        else:
            dataset_id = ds_row['id']
        # keep note of dataset_id
        datasets.append(dataset_id)

        # sync labels
        it2 = os.scandir(dataset_dir.path)
        labels = [label_dir for label_dir in it2]
        for label_dir in labels:
            it3 = os.scandir(label_dir.path)

            for datapoint_file in it3:
                # assuming datapoint directory name is <datapoint-id>
                id_str = datapoint_file.name
                if not str.isnumeric(id_str):
                    print('ignoring "{:s}", not a valid datapoint-id...'.format(id_str))
                    continue
                datapoint_id = int(id_str)

                cur.execute('select * from datapoints where id=(?)', [datapoint_id])
                dp_row = cur.fetchone()

                if dp_row is None:
                    # datapoint doesn't exist, add one
                    cur.execute('insert into datapoints (id, path, dataset_id) '
                                'values (?, ?, ?)', [datapoint_id, datapoint_file.path, dataset_id])
                    print('adding datapoint id={:d} with label="{:s}"'.format(datapoint_id, label_dir.name))
                else:
                    # update datapoint information to make sure everything checks out
                    sql_query = 'update datapoints set {:s} where id=?'
                    changes, values = [], []
                    log = ''
                    # check dataset
                    if dataset_id != dp_row['dataset_id']:
                        changes.append('dataset_id=?')
                        values.append(dataset_id)
                        log += 'dataset_id=' + str(dataset_id)
                    # check path
                    if datapoint_file.path != dp_row['path']:
                        changes.append('path=?')
                        values.append(datapoint_file.path)
                        log += ' path="' + datapoint_file.path + '"'
                    # add id
                    values.append(datapoint_id)

                    # only run if something needed to be changed
                    if len(changes) > 0:
                        cur.execute(sql_query.format(', '.join(changes)), values)
                        print('updated datapoint id={:d} {:s}'.format(datapoint_id, log))
                # keep note of datapoint id
                datapoints.append(datapoint_id)
            it3.close()
        it2.close()
    it.close()

    # remove datapoints in database
    cur.execute('select * from datapoints')
    db_datapoints = cur.fetchall()

    for dp_row in db_datapoints:
        dp_id = dp_row['id']
        if dp_id not in datapoints:
            cur.execute('delete from datapoints where id=?', [dp_id])

    # remove datasets in database
    cur.execute('select * from datasets')
    db_datasets = cur.fetchall()

    for ds_row in db_datasets:
        ds_id = ds_row['id']
        if ds_id not in datasets:
            cur.execute('delete from datasets where id=?', [ds_id])

    db.commit()


def init_db(exclude=[]):
    """Initializes the database."""
    db = get_db()
    dir = os.path.join(current_app.root_path, 'schemas')
    test_dir = os.path.join(current_app.root_path, '../tests/schemas')

    # TODO: Move drop table commands to separate file that runs before all other schemas
    def run_schemas(_dir):
        # sort in case some need to run before others
        files = sorted(list(
            filter(
                lambda p: p.endswith('.sql') and os.path.isfile(os.path.join(_dir, p)),
                os.listdir(_dir)
            )
        ))

        print('Reading schemas from {} ...'.format(_dir))
        for file in files:
            if file in exclude:
                continue

            print('    reading {}'.format(file))
            with open(os.path.join(_dir, file), mode='r') as f:
                db.cursor().executescript(f.read())

    run_schemas(dir)
    if current_app.config.get('TESTING', False) and os.path.exists(test_dir):
        run_schemas(test_dir)


@click.command('initdb')
@with_appcontext
def initdb_command():
    """Creates the database tables."""
    init_db()
    print('Initialized the database.')


def connect_db():
    """Connects to the specific database."""
    rv = sqlite3.connect(current_app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    # enable foreign key support
    rv.execute('PRAGMA foreign_keys = ON;')
    rv.commit()

    return rv


def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db


def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()
        # del g['sqlite_db']
