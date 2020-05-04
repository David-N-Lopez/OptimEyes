import json
import base64
import binascii
import os
import functools

from flask import Blueprint, Flask, request, g, redirect, url_for, render_template, flash, current_app, session, \
    Response, abort
from werkzeug.security import check_password_hash

from .db import get_db
from .util import create_dir
from . import responses

bp = Blueprint('api', __name__, url_prefix='/api')


@bp.route('/data/<string:command>', methods=['POST'])
def modify_dataset(command):
    """
    Adds data points to datasets with data collected from the JSON body of the post request.
    The mimetype of the request must be JSON, i.e 'Content-Type' header should indicate
    that the content is JSON.

    :param command:
        Only `add` atm. Adds datapoint entry to database linked to the provided user and writes the
        base64 encoded images to disk in the directory for the dataset and label that was provided.
    :return:
        JSON response with information about success or failure.
    """

    # check if mimetype of request is json
    if not request.is_json:
        return responses.error_response(400, 'mimetype of request is not JSON')

    body = request.json

    # check credentials
    user, password = body.get('user'), body.get('password')
    db = get_db()
    user_row = db.execute('select * from users where username=(?);', [user]).fetchone()

    if user_row is None or not check_password_hash(user_row['hash_password'], password):
        return responses.error_response(401, 'User with that username and password does not exist')

    if command == 'add':
        dataset_name = body.get('dataset')
        label = body.get('label')
        images = body.get('images')

        # data validation
        dataset_row = db.execute('select * from datasets where name=(?);', [dataset_name]).fetchone()
        if dataset_row is None:
            return responses.error_response(400, 'dataset {:s} not valid'.format(dataset_name))

        # check if label is valid
        if label not in _get_labels(dataset_row['path']):
            return responses.error_response(400, 'label {:s} not valid'.format(label))

        # images must be an array
        if type(images) is not list:
            return responses.error_response(400, 'images must be an array of base64 encoded images'.format(label))
        # at least one image
        if len(images) < 1:
            return responses.error_response(400, 'images must have at least one image'.format(label))

        # convert ascii string to bytes
        for i in range(len(images)):
            str_img = images[i]
            try:
                img_bytes = base64.b64decode(str_img, validate=True)
                images[i] = img_bytes
            except binascii.Error as e:
                return responses.error_response(400, 'error decoding image {:d}'.format(i), exception=e)

        try:
            _add_datapoint(dataset_row['id'], label, images, user_row['id'])
        except Exception as e:
            return responses.error_response(500, 'error adding datapoint', exception=e)

    return responses.success_response('Successfully added datapoint')


@functools.lru_cache()
def _get_labels(dataset_path):
    dir = os.path.join(current_app.config.get('DATA_DIR'), dataset_path)
    labels = []
    with os.scandir(dir) as it:
        for entry in it:
            if entry.is_dir():
                labels.append(entry.name)
    return labels


def _add_datapoint(dataset_id, label, images, user_id):
    db = get_db()
    cur = db.cursor()
    dataset_row = cur.execute('select * from datasets where id=(?);', [dataset_id]).fetchone()

    base_dir = current_app.config.get('DATA_DIR')
    dir = os.path.join(base_dir, dataset_row['path'], label)

    cur.execute('insert into datapoints (path, user_id, dataset_id) '
                'values (?, ?, ?);',
                ['N/A', user_id, dataset_id]
                )
    cur.execute('select last_insert_rowid();')
    datapoint_id = cur.fetchone()[0]

    # create the directory which will contain the images
    dir = os.path.join(dir, str(datapoint_id))
    create_dir(dir)

    # update path in database
    cur.execute('update datapoints set path=? where id=?', [dir, datapoint_id])

    # commit to make sure key constraints aren't broken
    db.commit()

    # write to disk
    for i in range(len(images)):
        image = images[i]
        img_path = os.path.join(dir, '{:d}.png'.format(i))

        with open(img_path, 'wb') as f:
            f.write(image)


