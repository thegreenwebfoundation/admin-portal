"""
We use scaleway as a AWS S3 API compatible provider of object storage.
Below is the wrapper around it for working with the objects.
"""
import boto3
from django.conf import settings
from botocore.exceptions import ClientError
import logging
import typing


def object_storage_bucket(bucket_name: str):
    """
    Return the bucket identified by `bucket_name` for uploading
    and downloading files.
    """
    session = boto3.Session(region_name=settings.OBJECT_STORAGE_REGION)
    object_storage = session.resource(
        "s3",
        endpoint_url=settings.OBJECT_STORAGE_ENDPOINT,
        aws_access_key_id=settings.OBJECT_STORAGE_ACCESS_KEY_ID,
        aws_secret_access_key=settings.OBJECT_STORAGE_SECRET_ACCESS_KEY,
    )
    return object_storage.Bucket(bucket_name)


def object_storage_client():
    session = boto3.Session(region_name=settings.OBJECT_STORAGE_REGION)
    object_storage = session.resource(
        "s3",
        endpoint_url=settings.OBJECT_STORAGE_ENDPOINT,
        aws_access_key_id=settings.OBJECT_STORAGE_ACCESS_KEY_ID,
        aws_secret_access_key=settings.OBJECT_STORAGE_SECRET_ACCESS_KEY,
    )
    return object_storage.meta.client


def green_domains_bucket():
    """
    Return an object storage bucket containing snapshots
    of the green domain table
    """
    return object_storage_bucket(settings.DOMAIN_SNAPSHOT_BUCKET)


def public_url(bucket: str, key: str) -> str:
    """
    Return the public url for a given key in object storage.
    Scaleway's url structure is as follows for object storage.
    # https://[bucket-name].s3.[scaleway-region].scw.cloud/[object_path]
    """
    region = settings.OBJECT_STORAGE_REGION
    return f"https://{bucket}.s3.{region}.scw.cloud/{key}"


def create_presigned_url(
    bucket_name: str, object_name: str, expiration=60 * 60
) -> typing.Union[str, None]:
    """
    Generate a presigned URL to share an S3 object

    :param bucket_name: name of the bucket
    :param object_name: the name of the object key in the bucket
    :param expiration: Time in seconds for the presigned URL to remain valid
    :return: Presigned URL as string. If error, returns None.

    https://boto3.amazonaws.com/v1/documentation/api/latest/guide/clients.html
    """

    # Generate a presigned URL for the S3 object
    s3_client = object_storage_client()

    try:
        response = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": object_name},
            ExpiresIn=expiration,
        )
    except ClientError as e:
        logging.error(e)
        return None

    # The response contains the presigned URL
    return response
