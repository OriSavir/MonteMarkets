import os
import signal
import sys
from redis import Redis
from rq import Worker, Queue
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDIS_PORT"))

redis_conn = Redis(host=REDIS_HOST, port=REDIS_PORT)

# Handle graceful shutdown
def handle_shutdown(signum, frame):
    print('Received shutdown signal, stopping worker...')
    worker.shutdown()
    sys.exit(0)

signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)

if __name__ == "__main__":
    queue = Queue(connection=redis_conn)
    worker = Worker(queues=[queue], connection=redis_conn)
    worker.work(with_scheduler=True)
