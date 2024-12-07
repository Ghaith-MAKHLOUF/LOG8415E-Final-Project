from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pymysql
import random
import uvicorn
import json
import subprocess


app = FastAPI()


with open("instance_info_workers.json", 'r') as f:
    workers_json = json.load(f)

    master_data = workers_json[0]
    master_ip   = master_data["Private IP"]

    slave1_data = workers_json[1]
    slave1_ip   = slave1_data["Private IP"]

    slave2_data = workers_json[2]
    slave2_ip   = slave2_data["Private IP"]
 

# Database connection details
MASTER_DB = {f"host": master_ip, "user": "proxy_user", "password": "", "db": "sakila"}
SLAVE_DB = [{f"host": slave1_ip, "user": "proxy_user", "password": "", "db": "sakila"},
            {f"host": slave2_ip, "user": "proxy_user", "password": "", "db": "sakila"}]


class SQLRequest(BaseModel):
    query: str
    type_query: str
    strategy: str


def ping_host(host):
    """Ping a host and return the round-trip time (in ms)."""
    try:
        command = ["ping", "-c", "4", host]  # 4 packets for a more stable reading on Unix-like systems

        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        output = result.stdout
        if result.returncode == 0:
            # Find the line with 'avg' latency in the result.
            lines = output.splitlines()
            for line in lines:
                if "avg" in line:
                    # Extract the average round-trip time.
                    avg_time = line.split('=')[-1].split('/')[1]
                    return float(avg_time)  # Return average latency in ms.
        else:
            return None
    except Exception as e:
        print(f"Error pinging host {host}: {str(e)}")
        return None


def execute_query(db_config, sql_query):
    """Executes a SQL query on the specified database."""
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            cursor.execute(sql_query)
            if sql_query.strip().lower().startswith("select"):
                result = cursor.fetchall()
            else:
                connection.commit()
                result = {"status": "success"}
        connection.close()
        return result
    except Exception as e:
        return {"error": str(e)}


@app.post("/sql")
async def proxy_sql(data: SQLRequest):
    print("Proxy: Request received. Processing...")
    sql_query = data.query
    query_type = data.type_query
    query_strategy = data.strategy

    if query_type == "read":
        if query_strategy == "direct_hit":               # Redirect query to master node.
            
            db_config = MASTER_DB
            result = execute_query(db_config, sql_query)
            print(f"Queries forwarded to Master: {db_config['host']}")
            return result

        elif query_strategy == "random":                 # Randomly choose a slave node and forward requests to it.
            
            db_config = random.choice(SLAVE_DB)          
            print(f"Queries randomly forwarded to slave: {db_config['host']}")
            result = execute_query(db_config, sql_query)
            return result

        elif query_strategy == "customized":             # Choose the fastest instance by pinging.
            
            # Ping the master and slave instances and measure the response time.
            master_latency = ping_host(MASTER_DB["host"])
            slave_latencies = [ping_host(slave["host"]) for slave in SLAVE_DB]
            print("Master Latency: ", master_latency)
            print("Slaves Latency: ", slave_latencies)
            # Handle the case where ping might fail and return None.
            valid_latencies = [(MASTER_DB["host"], master_latency)] + [
                (slave["host"], latency) for slave, latency in zip(SLAVE_DB, slave_latencies) if latency is not None
            ]
            
            # Choose the instance with the lowest latency.
            best_instance = min(valid_latencies, key=lambda x: x[1], default=None)

            if best_instance:
                best_host, best_latency = best_instance
                print(f"Queries forwarded to {best_host} with latency {best_latency} ms")
                # Set db_config to the best host's config.
                if best_host == MASTER_DB["host"]:
                    db_config = MASTER_DB
                else:
                    db_config = next(slave for slave in SLAVE_DB if slave["host"] == best_host)
            else:
                raise HTTPException(status_code=500, detail="Unable to determine the best instance based on ping times.")
            
            result = execute_query(db_config, sql_query)
            return result
    
    elif query_type == "write":  # Always route write queries to the master first

        # Execute on master first
        db_config = MASTER_DB
        result_master = execute_query(db_config, sql_query)
        print(f"Query executed on Master {MASTER_DB['host']}. Result: {result_master}")
        # Now we replicate the write query to the slaves

        slave_results = []
        for slave in SLAVE_DB:
            slave_result = execute_query(slave, sql_query)
            slave_results.append({slave["host"]: slave_result})
            print(f"Query executed on slave {slave['host']}. Result: {slave_result}")

        # Return the result from the master and slaves
        return {"master_result": result_master, "slave_results": slave_results}
    
    else:
        raise HTTPException(status_code=400, detail="Invalid query type")
    
    return None


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=80)
