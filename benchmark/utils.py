import os

def get_path(path):
    dirname = os.path.dirname(__file__)
    return os.path.join(dirname, path)