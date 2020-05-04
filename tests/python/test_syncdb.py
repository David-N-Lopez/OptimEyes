import os

from flask import Flask

from webserver.db import get_db


def test_syncdb(app: Flask):
    """Tests that `syncdb` cli command correctly modifies the database to reflect the contents in
    `DATA_DIR` directory."""
    runner = app.test_cli_runner()

    data_dir = app.config.get('DATA_DIR')
    # create test datasets and labels
    datasets = ['dataset0', 'dataset1', 'dataset2']
    labels = [
        ['d0-label0'],
        ['d1-label0', 'd1-label1', 'd2-label2'],
        ['d2-label0', 'd2-label1'],
    ]
    datapoints = [
        [
            ['0', '1', '2', '3'],
        ],
        [
            ['5', '9', '10', '13'],
            ['12', '90', '910', '1113'],
            [],
        ],
        [
            [],
            ['22']
        ]
    ]

    for i, dataset in enumerate(datasets):
        ds_dir = os.path.join(data_dir, dataset)
        os.mkdir(ds_dir)

        for j, label in enumerate(labels[i]):
            dl_dir = os.path.join(ds_dir, label)
            os.mkdir(dl_dir)

            for datapoint in datapoints[i][j]:
                os.mkdir(os.path.join(dl_dir, datapoint))

    result = runner.invoke(args=['syncdb'])
    assert result.exception is None

    # check database
    _check_db(app)


def test_syncdb_update(app: Flask):
    """Tests that `syncdb` cli command updates database information correctly"""

    runner = app.test_cli_runner()

    data_dir = app.config.get('DATA_DIR')
    # create test datasets and labels
    datasets = ['dataset0']
    labels = [
        ['label0', 'label1'],
    ]
    datapoints = [
        [
            ['0', '1', '2', '3'],
            ['5', '8', '22', '33'],
        ],
    ]

    for i, dataset in enumerate(datasets):
        ds_dir = os.path.join(data_dir, dataset)
        os.mkdir(ds_dir)

        for j, label in enumerate(labels[i]):
            dl_dir = os.path.join(ds_dir, label)
            os.mkdir(dl_dir)

            for datapoint in datapoints[i][j]:
                os.mkdir(os.path.join(dl_dir, datapoint))

    # add incorrect data to database
    db = get_db()
    cur = db.cursor()

    wrong_ds = 'dataset1'
    ds_path = os.path.join(data_dir, datasets[0])
    wrong_ds_path = os.path.join(data_dir, wrong_ds)

    # add wrong dataset
    cur.execute('insert into datasets (name, path) values (?, ?)', [wrong_ds, wrong_ds_path])
    cur.execute('select last_insert_rowid();')
    wrong_ds_id = cur.fetchone()[0]

    # add right dataset
    cur.execute('insert into datasets (name, path) values (?, ?)', [datasets[0], ds_path])
    cur.execute('select last_insert_rowid();')
    ds_id = cur.fetchone()[0]

    # add correct datapoints
    label = labels[0][0]
    cur.execute('insert into datapoints (path, dataset_id) values (?, ?)',
                [os.path.join(ds_path, label, datapoints[0][0][0]), ds_id])
    cur.execute('insert into datapoints (path, dataset_id) values (?, ?)',
                [os.path.join(ds_path, label, datapoints[0][0][1]), ds_id])

    # add incorrect datapoints
    label = labels[0][1]
    # wrong label
    cur.execute('insert into datapoints (path, dataset_id) values (?, ?)',
                [os.path.join(ds_path, label, datapoints[0][0][2]), ds_id])
    # wrong dataset and label
    cur.execute('insert into datapoints (path, dataset_id) values (?, ?)',
                [os.path.join(wrong_ds_path, label, datapoints[0][0][3]), wrong_ds_id])
    # wrong dataset
    cur.execute('insert into datapoints (path, dataset_id) values (?, ?)',
                [os.path.join(wrong_ds_path, label, datapoints[0][1][0]), wrong_ds_id])
    # commit
    db.commit()

    result = runner.invoke(args=['syncdb'])
    assert result.exception is None

    # check database
    _check_db(app)


def _check_db(app: Flask):
    """
    Collects all datasets and data point information from `DATA_DIR` (from app configuration) and
    checks that the information in database correctly reflects that.
    """
    # collect everything in DATA_DIR
    data_dir = app.config.get('DATA_DIR')
    it = os.scandir(data_dir)

    datasets = []
    datapoints = []
    for ds_entry in it:
        ds_path = ds_entry.path
        datasets.append(ds_path)

        it2 = os.scandir(ds_path)
        for dl_entry in it2:
            label = dl_entry.name

            it3 = os.scandir(dl_entry.path)
            for dp_entry in it3:
                dp_id = int(dp_entry.name)
                dp_path = dp_entry.path

                datapoints.append([dp_id, dp_path, ds_path])
            it3.close()
        it2.close()
    it.close()

    # collect everything in database
    db = get_db()
    cur = db.cursor()

    cur.execute('select * from datasets')
    datasets_table = cur.fetchall()
    cur.execute('select * from datapoints')
    datapoints_table = cur.fetchall()

    # check datasets are the same
    assert len(datasets_table) == len(datasets)

    ds_l = len(datasets)
    ds_dict = dict()
    for ds_row in datasets_table:
        ds_path = ds_row['path']
        ds_id = ds_row['id']
        i = 0
        while i < ds_l:
            if ds_path == datasets[i]:
                ds_dict[ds_id] = ds_path
                break
            i += 1
        assert i < ds_l and 'dataset in database not in directory'

    # check datapoints
    assert len(datapoints_table) == len(datapoints)

    for dp_row in datapoints_table:
        dp_id = dp_row['id']
        dp_path = dp_row['path']
        ds_id = dp_row['dataset_id']

        results = 0
        for dp_id_i, dp_path_i, ds_path_i in datapoints:
            if dp_id_i == dp_id:
                assert dp_path == dp_path_i and "datapoint paths are the same"
                assert ds_dict[ds_id] == ds_path_i and "datasets are the same"
                results += 1

        assert results == 1 and "no duplicate datapoints"
