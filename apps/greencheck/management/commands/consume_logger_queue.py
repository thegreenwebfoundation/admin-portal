from django.core.management.base import BaseCommand
from django.db import connection
from apps.greencheck.legacy_workers import LegacySiteCheckLogger
import pika
import logging
from django.conf import settings

logger = logging.getLogger(__name__)
# console = logging.StreamHandler()
# logger.addHandler(console)
# logger.setLevel(logging.DEBUG)

class Command(BaseCommand):
    help = "Start a worker consuming from legacy app queue"

    def handle(self, *args, **options):

        sitecheck_logger = LegacySiteCheckLogger()

        def on_message(channel, method_frame, header_frame, body):
            logger.debug(f"message received for {channel}")
            logger.debug(f"method_frame: {method_frame}")
            logger.debug(f"header_frame: {header_frame}")
            # logger.debug(body)
            logger.debug(f"delivery_tag: {method_frame.delivery_tag}")

            sitecheck_logger.parse_and_log_to_database(body)


        parameters = pika.URLParameters(settings.RABBITMQ_URL)
        mq_connection = pika.BlockingConnection(parameters)
        channel = mq_connection.channel()

        queue_args = {'x-max-priority': 4}
        channel.queue_declare('enqueue.app.default', durable=True, arguments=queue_args)
        channel.basic_consume('enqueue.app.default', on_message, auto_ack=True)

        try:
            channel.start_consuming()
        except KeyboardInterrupt:
            channel.stop_consuming()
        except Exception as err:
            logger.exception(err)
            channel.stop_consuming()

        mq_connection.close()


