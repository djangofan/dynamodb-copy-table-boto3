import sys
import os
import boto3
import multiprocessing
import itertools
from time import sleep

localDynamoHost='http://192.168.99.100:8000'

# iam_role = boto3.session.Session(profile_name='intern')
# dynamodb = iam_role.resource('dynamodb', region_name=region)
# table = dynamodb.Table(new_table)
# print table.item_count


def scan_table(src_table, client, segment, total_segments, queue):
    item_count = 0
    paginator = client.get_paginator('scan')

    for page in paginator.paginate(
            TableName=src_table,
            Select='ALL_ATTRIBUTES',
            ReturnConsumedCapacity='NONE',
            ConsistentRead=True,
            Segment=segment,
            TotalSegments=total_segments,
            PaginationConfig={"PageSize": 500}):

        item_count += len(page['Items'])
    queue.put(item_count)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: {0} <source_table_name> <isLocal>".format(sys.argv[0]))
        sys.exit(1)

    table_1 = sys.argv[1]
    isLocal = sys.argv[2]
    # defaults to us-west-2
    region = os.getenv('AWS_DEFAULT_REGION', os.getenv('AWS_REGION', 'us-west-2'))

    if not isLocal:
        iam_role = boto3.session.Session(profile_name='default')
        db_client = iam_role.client('dynamodb')
    else:
        db_client = boto3.client('dynamodb', endpoint_url=localDynamoHost)

    queue = multiprocessing.Queue()
    results = []

    pool_size = 4
    pool = []

    #spinner = itertools.cycle(['-', '/', '|', '\\'])

    for i in range(pool_size):
        worker = multiprocessing.Process(
            target=scan_table,
            kwargs={
                'src_table': table_1,
                'client': db_client,
                'segment': i,
                'total_segments': pool_size,
                'queue': queue
            }
        )
        pool.append(worker)
        worker.start()

    for process in pool:
        while process.is_alive():
            #sys.stdout.write(spinner.next())
            sys.stdout.flush()
            sleep(0.1)
            sys.stdout.write('\b')

    for p in pool:
        count = queue.get()  # will block
        results.append(count)

    print("*** {0} items counted. Exiting...".format(sum(results)))
