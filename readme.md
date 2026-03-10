Target Architecture:

Global External HTTP(S) Load Balancer (GLB): To receive incoming messages.
Cloud Run: A fully managed service to host a simple application. This application will receive HTTP POST requests from the GLB, and publish the message body (the test.json content) to a Pub/Sub topic. We use Cloud Run for its simplicity and auto-scaling capabilities for this type of workload.
Pub/Sub: A topic to receive messages from the Cloud Run service.
BigQuery Subscription: A push subscription on the Pub/Sub topic that writes messages directly to a BigQuery table using the Storage Write API.


Benchmark Setup Steps:

1. Select Region: Choose a large GCP region (e.g., europe-west1 or us-central1) for optimal default quotas.
2. Setup BigQuery:
Create a Dataset.
Create a BigQuery table. The schema should be derived from the test.json structure. Consider partitioning the table by an extracted timestamp and clustering by fields like data.app_id and data.agent_id to optimize query performance and costs.
3. Setup Pub/Sub:
Create a Pub/Sub Topic.
Create a BigQuery Subscription on the topic, configuring it to write to the BigQuery table created above. Ensure the subscription settings match the table schema (e.g., by enabling use_table_schema).
4. Deploy Cloud Run Service:
Develop a lightweight containerized application (e.g., using Python, or Go) that exposes an HTTP endpoint.
This endpoint will receive the POST request, take the request body, and publish it as a message to the Pub/Sub Topic.
Deploy to Cloud Run in the same region, with appropriate CPU/memory settings and autoscaling enabled.
5. Configure Load Balancer:
Setup a Global External HTTP(S) Load Balancer.
Create a serverless network endpoint group (NEG) for the Cloud Run service.
Configure the GLB backend service to use the serverless NEG.
6. Generate Load:
Use a distributed load testing tool (e.g., Locust, JMeter, or custom scripts running on a group of Compute Engine VMs) to send 100,000 HTTP POST requests per second to the GLBs IP address. 
Each request should contain the test.json payload.
7. Monitor:
Use Cloud Monitoring dashboards to observe:
  GLB request counts and latency.
  Cloud Run instance counts, CPU/memory usage, request latency.
  Pub/Sub publish throughput and BigQuery subscription throughput.
  BigQuery Storage Write API usage and any potential errors.
  Query BigQuery to confirm the number of rows ingested matches the expected volume.

step by step:

A. Cloud Run BQ and PubSub

1. BQ: (adjust to your own schema, this is an example)

CREATE TABLE `your-project.data_warehouse.activity_logs` (
  application_key STRING,
  trace_uuid STRING,
  occurrence_ts_str STRING,
  internal_member_id STRING,
  anonymous_device_id STRING,
  payload_attributes STRING,
  subscriber_traits STRING,
  record_loaded_at TIMESTAMP
);

2. create pubsub topic and subscrition (Ensure the subscription settings match the table schema (e.g., by enabling use_table_schema)

3. In cloud Console set up vars and build/deploy cloud run container:

# Replace with your project ID and desired service name
export PROJECT_ID="project_id"
export GOOGLE_CLOUD_PROJECT="project_id"
export SERVICE_NAME="your-ingest-service"
export REGION="europe-west1" # Or your chosen region
export PUBSUB_TOPIC_ID="topic_name"
export MAX_INSTANCES=400

gcloud builds submit --tag gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest .

export PROJECT_NUMBER=$(gcloud projects describe ${PROJECT_ID} --format="value(projectNumber)")
export RUN_SERVICE_ACCOUNT="xxxxxx-compute@developer.gserviceaccount.com"


gcloud pubsub topics add-iam-policy-binding ${PUBSUB_TOPIC_ID} \
  --member="serviceAccount:${RUN_SERVICE_ACCOUNT}" \
  --role="roles/pubsub.publisher" \
  --project=${PROJECT_ID}


gcloud run deploy ${SERVICE_NAME}  \
--image gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest  \
--platform managed   \
--region ${REGION}   \
--allow-unauthenticated  \ 
--set-env-vars PUBSUB_TOPIC_ID=${PUBSUB_TOPIC_ID}  \
--cpu=2  \
--memory=2Gi \
--cpu-boost  \
--min-instances=1  \
--max-instances=${MAX_INSTANCES} \
--concurrency=80  \
--timeout=300

test out using this sample (AI generated example, use your own payload)

json:

{
  "application_key": "enterprise-mobile-app",
  "trace_uuid": "8f3a2b11-9cde-4e71-b204-f5291a119e02",
  "occurrence_ts_str": "2026-03-10T10:15:30Z",
  "internal_member_id": "user-8842-premium",
  "anonymous_device_id": "did-660-f47ac10b-58cc",
  "payload_attributes": "{\"detection_type\": \"hooking\", \"severity\": \"high\", \"flags\": [\"frida\", \"re_tool\"]}",
  "subscriber_traits": "{\"platform\": \"insertsOS\", \"os_version\": \"14\", \"manufacturer\": \"whatev\", \"tier\": \"gold\"}",
  "record_loaded_at": "2026-03-10T10:16:00Z"
}

example: 

curl -X POST "https://INGEST-SERVICE-URL.europe-west1.run.app" \
-H "Authorization: bearer $(gcloud auth print-identity-token)" \
-H "Content-Type: application/json" \
-d '{
  "application_key": "enterprise-mobile-app",
  "trace_uuid": "8f3a2b11-9cde-4e71-b204-f5291a119e02",
  "occurrence_ts_str": "2026-03-10T10:15:30Z",
  "internal_member_id": "user-8842-premium",
  "anonymous_device_id": "did-660-f47ac10b-58cc",
  "payload_attributes": "{\"detection_type\": \"hooking\", \"severity\": \"high\", \"flags\": [\"frida\", \"re_tool\"]}",
  "subscriber_traits": "{\"platform\": \"insertsOS\", \"os_version\": \"14\", \"manufacturer\": \"whatev\", \"tier\": \"gold\"}",
  "record_loaded_at": "2026-03-10T10:16:00Z"
}'

=================================================

B. GLB setup

export PROJECT_ID="id"
export SERVICE_NAME="your-ingest-service" # Your Cloud Run service name
export REGION="europe-west1" # Your Cloud Run region
export PUBSUB_TOPIC_ID="topic_id"
export LB_NAME="your-ingest-lb"
export NEG_NAME="your-ingest-neg"
export BACKEND_SERVICE_NAME="your-ingest-backend-service"
export URL_MAP_NAME="your-ingest-url-map"
export TARGET_PROXY_NAME="your-ingest-target-proxy"
export FORWARDING_RULE_NAME="your-ingest-fw"
export IP_NAME="your-ingest-static-ip"

gcloud compute addresses create ${IP_NAME} --global --project=${PROJECT_ID}


export LB_IP=$(gcloud compute addresses describe ${IP_NAME} --global --project=${PROJECT_ID} --format="value(address)")
echo "Load Balancer IP: ${LB_IP}"


gcloud compute network-endpoint-groups create ${NEG_NAME} \
  --region=${REGION} \
  --network-endpoint-type=serverless \
  --cloud-run-service=${SERVICE_NAME} \
  --project=${PROJECT_ID}


gcloud compute backend-services create ${BACKEND_SERVICE_NAME} \
  --global \
  --load-balancing-scheme=EXTERNAL_MANAGED \
  --protocol=HTTP \
  --project=${PROJECT_ID}


  gcloud compute backend-services add-backend ${BACKEND_SERVICE_NAME} \
  --global \
  --network-endpoint-group=${NEG_NAME} \
  --network-endpoint-group-region=${REGION} \
  --project=${PROJECT_ID}

gcloud compute url-maps create ${URL_MAP_NAME} \
  --default-service=${BACKEND_SERVICE_NAME} \
  --global \
  --project=${PROJECT_ID}


gcloud compute target-http-proxies create ${TARGET_PROXY_NAME} \
  --url-map=${URL_MAP_NAME} \
  --global \
  --project=${PROJECT_ID}

gcloud compute forwarding-rules create ${FORWARDING_RULE_NAME} \
  --global \
  --load-balancing-scheme=EXTERNAL_MANAGED \
  --address=${IP_NAME} \
  --target-http-proxy=${TARGET_PROXY_NAME} \
  --ports=80 \
  --project=${PROJECT_ID}

After a few minutes, the load balancer will be provisioned, and all traffic to http://<LB_IP> will be directed to your Cloud Run service.


C. Locust setup:

to send ~100k/sec to GLB we need 10 VM with e2-standard-16 (16 vCPUs, 64 GB Memory)

1. install locust, one node will be Master and the rest workers. We need to start the worker process for each core, 144 in total:

sudo apt update
sudo apt install -y python3-pip python3-venv
python3 -m venv env
source env/bin/activate

pip install locust
pip install google-auth google-auth-httplib2 google-auth-oauthlib

2. create locally locustfile.py and payload file test.json

3. add the firewall rule to let UI access on the outside + plus fw rule to let worker connect to master

gcloud compute firewall-rules create locust-master-worker \
  --direction=INGRESS \
  --priority=1000 \
  --network=base \
  --action=ALLOW \
  --rules=tcp:5557,tcp:5558 \
  --source-tags=locust-worker \
  --target-tags=locust-master --project=${PROJECT_ID}


4. start Master and get to UI: 
locust -f locustfile.py --master --host http://LB_IP:80

5. start workers on each thread:

vi 16.sh
chmod +x 16.sh

for i in {1..16}; do
    locust -f locustfile.py --worker --master-host=IP_internal --host http://LB_IP:80 &
done

6. start Locust with:

15k users and ramp up: 45 user. check you also have 144 workers registered. hit run:

<img width="826" height="220" alt="image" src="https://github.com/user-attachments/assets/7f3b91f3-ab2f-4c14-8316-4fed60eb683f" />

7. Monitor Clour Run instances and BQ, check graph from Locust UI: 

<img width="1547" height="938" alt="image" src="https://github.com/user-attachments/assets/be50bfc3-d2d3-43fc-8a85-116ad7ce41ca" />

<img width="1282" height="700" alt="image" src="https://github.com/user-attachments/assets/c72c6c29-65ed-4608-91a8-2916c7a73b42" />













