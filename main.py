import os
from flask import Flask, request, Response
from google.cloud import pubsub_v1

app = Flask(__name__)

# --- Configuration ---

PROJECT_ID = ""
TOPIC_ID = ""

if not PROJECT_ID:
    raise EnvironmentError("GOOGLE_CLOUD_PROJECT environment variable not set.")
if not TOPIC_ID:
    raise EnvironmentError("PUBSUB_TOPIC_ID environment variable not set.")

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)
# --- End Configuration ---

@app.route('/', methods=['POST'])
def index():
    if not request.is_json and request.content_type != 'application/json':
         # Try to get data as bytes if not JSON
        message_data = request.get_data()
        if not message_data:
            return Response("Error: Request body is empty or not in the expected format.", status=400, mimetype='text/plain')
    else:
        # If it's JSON, get the raw bytes
        message_data = request.get_data()

    try:
        # Publish the raw message data (bytes) to the Pub/Sub topic
        future = publisher.publish(topic_path, message_data)
        message_id = future.result()
        # print(f"Published message ID: {message_id}") # Optional: Logging for confirmation
        return Response(f"Message published: {message_id}", status=200, mimetype='text/plain')
    except Exception as e:
        print(f"Error publishing to Pub/Sub: {e}")
        return Response(f"Error publishing to Pub/Sub: {e}", status=500, mimetype='text/plain')

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
