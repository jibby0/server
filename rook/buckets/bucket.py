import boto3
import json
import os

def connect():
    access_key = os.environ["AWS_ACCESS_KEY_ID"]
    secret_key = os.environ["AWS_SECRET_ACCESS_KEY"]

    return boto3.client('s3', 'us-east-1',
                        endpoint_url="https://s3.jibby.org",
                        aws_access_key_id = access_key,
                        aws_secret_access_key = secret_key)

def create_bucket(bucket_name):
    conn = connect()
    conn.create_bucket(Bucket=bucket_name)

def set_public_read_policy(bucket_name):
    bucket_policy = {
    "Version":"2012-10-17",
    "Statement":[
        {
        "Sid":"AddPerm",
        "Effect":"Allow",
        "Principal": "*",
        "Action":["s3:GetObject", "s3:ListBucket"],
        "Resource":[
            "arn:aws:s3:::{0}/*".format(bucket_name),
            "arn:aws:s3:::{0}".format(bucket_name),
            ]
        }
    ]
    }

    bucket_policy = json.dumps(bucket_policy)
    conn = connect()
    conn.put_bucket_policy(Bucket=bucket_name, Policy=bucket_policy)
