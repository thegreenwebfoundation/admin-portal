import logging
import os
import beeline


def post_worker_init(worker):
    logging.info(f"beeline initialization in process pid {os.getpid()}")
    beeline.init(
        writekey=os.getenv("HONEYCOMBIO_WRITE_KEY"),
        dataset=os.getenv("HONEYCOMBIO_DATASET"),
        debug=True,
    )
