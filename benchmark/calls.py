import asyncio
import aiohttp
import json
import time
from utils import *
import random


with open(get_path("../deploy/configs/instance_info_gatekeeper.json"), 'r') as f:
    gatekeeper_data_json = json.load(f)
    gatekeeper_data = gatekeeper_data_json[0]
    gatekeeper_address = gatekeeper_data["DNS"]


async def call_endpoint_sql(session, request_num, sql_query, query_type, query_strategy):
   
    url = f"http://{gatekeeper_address}/query_gk"  # gatekeeper endpoint for SQL
    headers = {'content-type': 'application/json'}
    payload = {
        "query": sql_query,
        "type_query": query_type,
        "strategy": query_strategy 
    }

    try:
        async with session.post(url, json=payload, headers=headers) as response:
            status_code = response.status
            response_json = await response.json()
            print(f"Request {request_num}: Status Code: {status_code}")
            print(f"Response: {json.dumps(response_json, indent=2)}")  # Print the error details
            return status_code, response_json
    except Exception as e:
        print(f"Request {request_num}: Failed - {str(e)}")
        return None, str(e)

async def launch_requests(query_type):
    """
    Launches SQL read/write requests to the gatekeeper.

    Args:
        query_type: 'read' or 'write'.
    """
    num_requests = 1000                       
    start_time = time.time()

    if query_type == "read":
        sql_query = "SELECT COUNT(*) FROM film;"    # Example read query
        query_strategy = "direct_hit"               # direct_hit / random / customized
    elif query_type == "write":
        random_nbr = random.randint(1,1000)
        sql_query = f"INSERT INTO actor (first_name, last_name) VALUES ('Test_{random_nbr}', 'User_{random_nbr}');"  # Example write query
        query_strategy = "direct_hit"           # According to how the requests are structured a strategy needs to be set even for writing requests. It should be "direct_hit" 

    async with aiohttp.ClientSession() as session:
        tasks = [call_endpoint_sql(session, i, sql_query, query_type, query_strategy) for i in range(num_requests)]
        await asyncio.gather(*tasks)

    end_time = time.time()
    print(f"\nTotal time taken: {end_time - start_time:.2f} seconds")
    print(f"Average time per request: {(end_time - start_time) / num_requests:.4f} seconds")

