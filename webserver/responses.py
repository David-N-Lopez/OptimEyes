import json


def error_response(status_code, description, exception=None):
    if exception:
        exception_str = str(exception)
    else:
        exception_str = ''

    body = json.dumps({
        'code': status_code,
        'description': description,
        'Exception': exception_str
    })

    return body, status_code


def success_response(description, other_data=None):
    body = {
        'code': 200,
        'description': description,
    }

    if other_data:
        for key, val in other_data:
            body[key] = val

    return json.dumps(body), 200
