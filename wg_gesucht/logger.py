import os
import logging


def get_logger(name, folder, level=logging.INFO):
    formatter = logging.Formatter('%(asctime)s::%(name)s::%(levelname)s::%(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    logger = logging.getLogger(name)
    logger.setLevel(level)

    info_file_handler = logging.FileHandler(os.path.join(folder, 'info.log'))
    info_file_handler.setFormatter(formatter)
    info_file_handler.setLevel(logging.INFO)

    error_file_handler = logging.FileHandler(os.path.join(folder, 'error.log'))
    error_file_handler.setFormatter(formatter)
    error_file_handler.setLevel(logging.ERROR)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.WARNING)

    logger.addHandler(info_file_handler)
    logger.addHandler(error_file_handler)
    logger.addHandler(stream_handler)

    return logger
