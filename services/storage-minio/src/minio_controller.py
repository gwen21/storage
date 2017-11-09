# -*- coding: utf-8 -*-
import asyncio
from os import environ, SEEK_END
from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner
from aiohttp import web

from minio import Minio
from minio.error import ResponseError

def config_minio():
    # initialize minio sdk
    access_key = environ.get("MINIO_ACCESS_KEY", "zephir")
    secret_key = environ.get("MINIO_SECRET_KEY", "zephir123")
    minio_url = environ.get("MINIO_URL", "localhost:9000")
    minio_client = Minio(minio_url, access_key=access_key, secret_key=secret_key, secure=False)

    return minio_client

MCLIENT = config_minio()
# configure default region for minio actions
# TODO : define a default region, or send region with each API call ?
mregion = environ.get("MINIO_REGION", "eu-west-1")

def ensure_bucket(bucket):
    # check if bucket exists
    if not MCLIENT.bucket_exists(bucket):
        try:
            MCLIENT.make_bucket(bucket, mregion)
            # remove existing notifications on "zephir" bucket
            MCLIENT.remove_all_bucket_notification(bucket)
            # add events on creation, removal and update of objects
            event_config = {'QueueConfigurations':[{'Arn':'arn:minio:sqs:{}:1:webhook'.format(mregion),
            'Events': ['s3:ObjectCreated:*','s3:ObjectRemoved:*']
            }]}
            MCLIENT.set_bucket_notification(bucket, event_config)
        except Exception as err:
            # FIXME : gestion des erreurs ?
            print(err)
            raise(err)


loop = asyncio.get_event_loop()

# intialize WAMP session
runner = ApplicationRunner(
    environ.get("AUTOBAHN_ROUTER", u"ws://crossbar:8080/ws"),
    u"realm1"
)
wamp_coro = runner.run(ApplicationSession, start_loop=False)
# add application to asyncio loop
(transport, wamp_proto) = loop.run_until_complete(wamp_coro)

# initialize event receiver (POST requests with aiohttp)
async def process_event_async(request):
    """Receives an event from minio and send a message to Crossbar

    Can be used to check service availability (POST request without data)
    """
    try:
        # TODO : check if json data exists (None on minio initialization)
        json_data = await request.json()
    except Exception as err:
        return web.Response(body=b"No event details")
    # convert to WAMP message
    try:
        wamp_proto._session.publish('v1.storage.event', key=json_data['Key'], event_type=json_data['EventType'])
    except Exception as err:
        # FIXME : gestion des erreurs ?
        print(err)
        raise(err)
    return web.Response(body=b"Event received")

def file_add(bucket, filename, content, content_type):
    #"json = {"files": {"filename": "toto.txt", "file": <CONTENT>}, "bucket": "zephir"}"
    ensure_bucket(bucket)

    # go to end of buffer to calculate size
    content_len = content.seek(0, SEEK_END)
    content.seek(0)
    #put_object(bucket_name, object_name, data, length, content_type)
    if MCLIENT.bucket_exists(bucket):
        #MCLIENT.put_object("toto", "test.txt", content, content_len, content_type)
        MCLIENT.put_object(bucket, filename, content, content_len, content_type)

async def file_add_async(request):
    #"json = {"files": {"filename": "toto.txt", "file": <CONTENT>}, "bucket": "zephir"}"
    data = await request.post()
    bucket = request.match_info.get("bucket", None)
    # TODO : check authorizations to write this file into the bucket
    filename = data["files"].filename
    content = data["files"].file
    content_type = data["files"].content_type
    try:
        file_add(bucket, filename, content, content_type)
    except Exception as err:
        print(err)
        raise(err)
    return web.json_response({"bucket": bucket, "filename": filename})

def file_delete(bucket, filename):
    # "json = {"filename": "toto.txt", "bucket": "zephir"}"
    MCLIENT.remove_object(bucket, filename)

async def file_delete_async(request):
    # "json = {"filename": "toto.txt", "bucket": "zephir"}"
    bucket = request.match_info.get("bucket", None)
    filename = request.match_info.get("filename", None)
    try:
        # TODO : return error if not MCLIENT.bucket_exists(bucket):
        file_delete(bucket, filename)
    except Exception as err:
        print(err)
        raise(err)
    return web.json_response({"bucket": bucket, "filename": filename})

def file_list(bucket):
    obj_list = MCLIENT.list_objects(bucket)
    return [{"name":obj.object_name, "size":obj.size} for obj in obj_list]

async def file_list_async(request):
    bucket = request.match_info.get("bucket", None)
    try:
        return_data = file_list(bucket)
    except Exception as err:
        print(err)
        raise(err)
    return web.json_response(return_data)

def bucket_list():
        bucket_list = MCLIENT.list_buckets()
        return [{"name":obj.name} for obj in bucket_list]

async def bucket_list_async(request):
    try:
        return_data = bucket_list()
    except Exception as err:
        print(err)
        raise(err)
    return web.json_response(return_data)

async def file_content_async(request):
    bucket = request.match_info.get("bucket", None)
    filename = request.match_info.get("filename", None)
    try:
        # TODO : return error if not MCLIENT.bucket_exists(bucket):
        # get_object(bucket_name, object_name)
        data = MCLIENT.get_object(bucket, filename)
        status_code = 200
        content_type = "application/octet-stream"
        # create stream response to send file content
        resp = web.StreamResponse(status=status_code, headers={"Content-Type": content_type})
        resp.enable_chunked_encoding()
        resp.enable_compression()
        # send response headers
        await resp.prepare(request)
        while True:
            stream = data.read(8192)
            if not stream:
                # flush buffer
                await resp.drain()
                break
            # send data
            resp.write(stream)
        return resp
    except Exception as err:
        print(err)
        raise(err)


if __name__ == "__main__":
    try:
        app = web.Application()
        # list existing buckets
        app.router.add_route('GET', '/files/', bucket_list_async)
        # list files from specified bucket
        app.router.add_route('GET', '/files/{bucket}', file_list_async)
        # read file content
        app.router.add_route('GET', '/files/{bucket}/{filename}', file_content_async)
        # remove file from a bucket
        app.router.add_route('DELETE', '/files/{bucket}/{filename}', file_delete_async)
        # add file in a bucket
        app.router.add_route('POST', '/files/{bucket}', file_add_async)
        # listener on port 3000 to catch minio events (webhook)
        app.router.add_route('POST', '/event', process_event_async)
        web_coro = loop.create_server(app.make_handler(), '0.0.0.0', 3000)

        srv = loop.run_until_complete(web_coro)
        print('serving on', srv.sockets[0].getsockname())
        loop.run_forever()
    except KeyboardInterrupt:
        pass
