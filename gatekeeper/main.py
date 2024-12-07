from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import aiohttp
import json
import uvicorn

app = FastAPI()


with open("instance_info_trustedhost.json", 'r') as f:

    trustedhost_json = json.load(f)
    trustedhost_data = trustedhost_json[0]
    trustedhost_address   = trustedhost_data["Private IP"]
 
class SQLRequest(BaseModel):
    query: str
    type_query: str
    strategy: str

@app.post("/query_gk")
async def forward_queries(sql_request: SQLRequest):
    # Perform the test on the query
    strategy = sql_request.strategy
    print(f"Gatekeeper: Query received. Strategy: {strategy}. Testing the Query...")
    if strategy not in ['direct_hit', 'random', 'customized']:          # Test: Only forward the request if its strategy is one of the three that we work with.
        raise HTTPException(status_code=400, detail=f"Malitious query detected: Unknown strategy {strategy}")
    
    # Forward query to Trusted Host
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"http://{trustedhost_address}/query_th",
                json=sql_request.dict()
            ) as response:
                # Check for errors in the response
                if response.status != 200:
                    error_message = await response.text()
                    raise HTTPException(status_code=response.status, detail=f"Trusted Host error: {error_message}")
                print("Gatekeeper: Successfully forwarded the requests to the Trusted Host.")
                return await response.json()         # Parse the JSON response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to communicate with Trusted Host: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=80)