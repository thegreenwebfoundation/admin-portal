"""
We use scaleway as a AWS S3 API compatible provider of object storage.
Below is the wrapper around it for working with the objects.
"""
import boto3
import logging
from botocore.exceptions import ClientError
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
# def retrieve_specific_bucket(bucket_name: str) -> boto3.resources.factory.s3.Bucket:
def retrieve_specific_bucket(bucket_name: str):
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
    return retrieve_specific_bucket(settings.DOMAIN_SNAPSHOT_BUCKET)

# TODO: ask what Chris thinks of this new format used by Boto3 for docstrings:


def upload_file_to_bucket(object_data, object_name, bucket):
    """Upload a file to an S3 bucket

    :param object_data: S3 object data
    :param object_name: S3 object name
    :param bucket: Bucket to upload to
    :return: True if file was uploaded, else False
    """
    s3_client = boto3.client('s3')
    try:
        s3_client.upload_fileobj(object_data, bucket, object_name)
    except ClientError as e:
        logging.error(e)
        return False
    return True


def public_url(bucket: str, key: str) -> str:
    """
    Return the public url for a given key in object storage.
    Scaleway's url structure is as follows for object storage.
    # https://[bucket-name].s3.[scaleway-region].scw.cloud/[object_path]
    """
    region = settings.OBJECT_STORAGE_REGION
    return f"https://{bucket}.s3.{region}.scw.cloud/{key}"
