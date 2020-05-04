import os


def create_dir(path):
    """
    Create directory `path` if the path does not already exist, creating parent directories as needed
    :param path: path of directory to create
    """
    if not os.path.exists(path):
        try:
            os.mkdir(path)
        except FileNotFoundError:
            parent = os.path.split(path)[0]
            # create parent directory
            create_dir(parent)

            os.mkdir(path)
        except FileExistsError:
            return
