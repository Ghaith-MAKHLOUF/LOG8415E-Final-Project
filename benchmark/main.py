import calls
from datetime import datetime, timedelta
import asyncio
from utils import *


if __name__ == "__main__":

    # start_time = datetime.utcnow() - timedelta(minutes=20)

    print("Launching requests to the Gatekeeper...")
    asyncio.run(calls.launch_requests(query_type='read'))