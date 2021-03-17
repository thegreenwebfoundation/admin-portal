import os

from dramatiq.brokers.rabbitmq import RabbitmqBroker
from dramatiq.brokers.stub import StubBroker


if os.getenv("UNIT_TESTS") == "1":
    broker = StubBroker()
    broker.emit_after("process_boot")
else:
    broker = RabbitmqBroker()
