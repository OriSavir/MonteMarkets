import os
from redis import Redis
from rq import Worker, Queue
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDIS_PORT"))

redis_conn = Redis(host=REDIS_HOST, port=REDIS_PORT)

if __name__ == "__main__":
    queue = Queue(connection=redis_conn)
    worker = Worker(queues=[queue], connection=redis_conn)
    worker.work()
