from flask import Flask, jsonify
from datetime import datetime, timedelta
from urllib.parse import quote
import boto3
from botocore.client import Config
import requests
import os

app = Flask(__name__)

# Configure S3 client (MinIO)
s3 = boto3.client(
    's3',
    endpoint_url='http://minio:9000',
    aws_access_key_id='local',
    aws_secret_access_key='local1234',
    config=Config(signature_version='s3v4'),
    region_name='us-east-1'
)

# S3 bucket name
bucket_name = 'onsale-flyers'

@app.route('/flyers', methods=['GET'])
def get_flyers():
    starting_id = 79968
    starting_start_date = datetime.strptime("2025-05-15", "%Y-%m-%d")
    flyer_count = 10

    base_url = "https://metrocommonapi.blob.core.windows.net/{id}/pdfs/{filename}"
    uploaded_flyers = []

    for i in range(flyer_count):
        flyer_id = starting_id - i
        start_date = starting_start_date - timedelta(days=7 * i)
        end_date = start_date + timedelta(days=6)

        start_str = start_date.strftime("%d-%m-%y")
        end_str = end_date.strftime("%d-%m-%y")

        filename = f"FoodBasics Weekly Flyer 0 Valid {start_str} - {end_str}.pdf"
        encoded_name = quote(filename)
        source_url = base_url.format(id=flyer_id, filename=encoded_name)

        local_file = f"/tmp/flyer-{flyer_id}.pdf"
        s3_key = f"{start_date.strftime('%Y-%m-%d')}/{filename}"

        try:
            # Download flyer from source
            response = requests.get(source_url)
            response.raise_for_status()
            with open(local_file, "wb") as f:
                f.write(response.content)

            # Upload to MinIO
            s3.upload_file(local_file, bucket_name, s3_key)

            # Construct S3 URL (public if MinIO bucket is open)
            s3_url = f"http://localhost:9000/{bucket_name}/{quote(s3_key)}"

            uploaded_flyers.append({
                "flyer_id": flyer_id,
                "start_date": start_str,
                "end_date": end_str,
                "original_url": source_url,
                "s3_url": s3_url
            })

            # Cleanup temp file
            os.remove(local_file)

        except Exception as e:
            uploaded_flyers.append({
                "flyer_id": flyer_id,
                "error": str(e)
            })

    return jsonify(uploaded_flyers)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)