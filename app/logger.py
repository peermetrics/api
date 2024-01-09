import logging

log = logging.getLogger('peer_logger')

formatter = logging.Formatter('(%(levelname)s::%(asctime)s) %(message)s')

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)

log.addHandler(stream_handler)

log.setLevel(logging.INFO)
