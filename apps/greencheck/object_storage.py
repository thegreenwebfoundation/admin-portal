"""
We use scaleway as a AWS S3 API compatible provider of object storage.
Below is the wrapper around it for working with the objects.
"""
import boto3
from django.conf import settings


def green_domains_bucket():
    """
    Return an object storage bucket containing snapshots
    of the green domain table
    """
    session = boto3.Session(region_name=settings.OBJECT_STORAGE_REGION)
    object_storage = session.resource(
        "s3",
        endpoint_url=settings.OBJECT_STORAGE_ENDPOINT,
        aws_access_key_id=settings.OBJECT_STORAGE_ACCESS_KEY_ID,
        aws_secret_access_key=settings.OBJECT_STORAGE_SECRET_ACCESS_KEY,
    )
    return object_storage.Bucket(settings.DOMAIN_SNAPSHOT_BUCKET)


def make_object_public(obj):
    """
    Apply the permissive `public-read` ACL to the object,
    in case it isn't already visible.
    """
    acl = obj.Acl()
    acl.put(ACL="public-read")
    return obj


def public_url(obj):
    """
    Return the public url for a given key in object storage.
    Scaleway's url structure is as follows for object storage.
    # https://[bucket-name].s3.[scaleway-region].scw.cloud/[object_path]
    """
    region = settings.OBJECT_STORAGE_REGION
    bucket = obj.bucket_name
    key = obj.key
    return f"https://{bucket}.s3.{region}.scw.cloud/{key}"

