"""
We use scaleway as a AWS S3 API compatible provider of object storage.
Below is the wrapper around it for working with the objects.
"""
import boto3
import json
from django.conf import settings


# TODO: how to specify this return time. The following example throws an error as
# this structure does not exist
# def retrieve_object_storage() -> boto3.resources.factory.s3.ServiceResource:
def retrieve_object_storage():
    """
    Create a resource service client by name using the default session.
    """
    # Create a session and return a resource client for the caller to use
    session = boto3.Session(region_name=settings.OBJECT_STORAGE_REGION)
    return session.resource(
        "s3",
        endpoint_url=settings.OBJECT_STORAGE_ENDPOINT,
        aws_access_key_id=settings.OBJECT_STORAGE_ACCESS_KEY_ID,
        aws_secret_access_key=settings.OBJECT_STORAGE_SECRET_ACCESS_KEY,
    )


# TODO: how to specify this return time. The following example throws an error as
# this structure does not exist
# def retrieve_bucket(bucket_name: str) -> boto3.resources.factory.s3.Bucket:
def retrieve_bucket(bucket_name: str):
    """
    Retrieve specified bucket from our object storage resource.
    """
    return retrieve_object_storage().Bucket(bucket_name)


# TODO: set return type
def bucket_green_domains():
    """
    Retrieve the green domains bucket.
    This bucket contains snapshots of green domain tables
    """
    return retrieve_bucket(settings.DOMAIN_SNAPSHOT_BUCKET)


def upload_json_file_to_bucket(bucket_name: str, json_data: dict, file_name: str):
    """
    Upload a JSON file to the object storage.
    The file will be overwritten if the file already exists
    """
    s3_object = retrieve_object_storage().Object(bucket_name, file_name)
    s3_object.put(Body=(bytes(json.dumps(json_data).encode("UTF-8"))))


def public_url(bucket: str, key: str) -> str:
    """
    Return the public url for a given key in object storage.
    Scaleway's url structure is as follows for object storage.
    # https://[bucket-name].s3.[scaleway-region].scw.cloud/[object_path]
    """
    region = settings.OBJECT_STORAGE_REGION
    return f"https://{bucket}.s3.{region}.scw.cloud/{key}"
