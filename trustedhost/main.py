from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import aiohttp
import json
import uvicorn

app = FastAPI()


with open("instance_info_proxy.json", 'r') as f:

    proxy_json = json.load(f)
    proxy_data = proxy_json[0]
    proxy_address   = proxy_data["Private IP"]
 
class SQLRequest(BaseModel):
    query: str
    type_query: str
    strategy: str

@app.post("/query_th")
async def forward_queries(sql_request: SQLRequest):
    print("Trusted Host: Requests received.")
    # Forward query to Proxy
    try:
        print("Trusted Host: forwarding requests to Proxy...")
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"http://{proxy_address}/sql",
                json=sql_request.dict()
            ) as response:
                # Check for errors in the response
                if response.status != 200:
                    error_message = await response.text()
                    raise HTTPException(status_code=response.status, detail=f"Proxy error: {error_message}")
                print("Successfully forwarded the requests to the Proxy.")
                return await response.json()         # Parse the JSON response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to communicate with Proxy: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=80)