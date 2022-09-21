"""
We use scaleway as a AWS S3 API compatible provider of object storage.
Below is the wrapper around it for working with the objects.
"""
import boto3
import json
from django.conf import settings


def retrieve_object_storage():
    """
    Return an object storage session
    """
    session = boto3.Session(region_name=settings.OBJECT_STORAGE_REGION)
    return session.resource(
        "s3",
        endpoint_url=settings.OBJECT_STORAGE_ENDPOINT,
        aws_access_key_id=settings.OBJECT_STORAGE_ACCESS_KEY_ID,
        aws_secret_access_key=settings.OBJECT_STORAGE_SECRET_ACCESS_KEY,
    )


def retrieve_bucket(bucket_name: str):
    """
    Return a specific S3 object storage bucket
    """
    return retrieve_object_storage().Bucket(bucket_name)


# TODO: set return type
def bucket_green_domains():
    """
    Return an object storage bucket containing snapshots
    of the green domain table
    """
    return retrieve_bucket(settings.DOMAIN_SNAPSHOT_BUCKET)


# TODO: Maybe get a bucket specifically for Microsoft's dataset?
# def microsoft_network_ranges_bucket():
# def bucket_microsoft_import_data():
def bucket_file_get_json(bucket_name: str, json_data: dict, file_name: str) -> dict:
    """
    Retrieve specific file from a bucket
    """
    # s3_object = retrieve_object_storage().Object(bucket_name, file_name)
    # TODO: Implement a get functionality here
    # return s3_object.get....
    return {}


def bucket_file_put_json(bucket_name: str, json_data: dict, file_name: str):
    """
    Put/overwrite data in a specified file and bucket
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
