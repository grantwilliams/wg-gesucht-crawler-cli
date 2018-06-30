import os
import logging

formatter = logging.Formatter(
    '%(asctime)s::%(name)s::%(levelname)s::%(message)s')


class InfoFilter(logging.Filter):
    def filter(self, record):
        return record.levelno in [20, 30]


def get_logger(name, folder, level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(level)

    info_file_handler = logging.FileHandler(os.path.join(folder, 'info.log'))
    info_file_handler.setFormatter(formatter)
    info_file_handler.addFilter(InfoFilter())
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


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
