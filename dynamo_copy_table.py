import sys
import os
from time import sleep
import boto3
import multiprocessing
import itertools

spinner = itertools.cycle(['-', '/', '|', '\\'])

localDynamoHost='http://192.168.99.100:8000'

def copy_items(src_table, dst_table, client, segment, total_segments):
    # copy over item
    item_count = 0
    paginator = client.get_paginator('scan')

    for page in paginator.paginate(
            TableName=src_table,
            Select='ALL_ATTRIBUTES',
            ReturnConsumedCapacity='NONE',
            ConsistentRead=True,
            Segment=segment,
            TotalSegments=total_segments,
            PaginationConfig={"PageSize": 25}):

        batch = []
        for item in page['Items']:
            item_count += 1
            batch.append({
                'PutRequest': {
                    'Item': item
                }
            })

        print("Process {0} put {1} items".format(segment, item_count))
        client.batch_write_item(
            RequestItems={
               dst_table: batch
            }
        )


def create_table(src_table, dst_table, client):
    # get source table and its schema
    print("Describe table '" + src_table + "'")
    try:
        table_schema = client.describe_table(TableName=src_table)["Table"]
    except client.exceptions.ResourceNotFoundException:
        print("!!! Table {0} does not exist. Exiting...".format(src_table))
        sys.exit(1)
    except:
        print("!!! Error reading table {0} . Exiting...".format(src_table))
        sys.exit(1)

    print("*** Reading key schema from {0} table".format(src_table))

    # create keyword args for copy table
    keyword_args = {"TableName": dst_table}

    keyword_args['KeySchema'] = table_schema['KeySchema']
    keyword_args['AttributeDefinitions'] = table_schema['AttributeDefinitions']

    global_secondary_indexes = []
    local_secondary_indexes = []

    if table_schema.get("GlobalSecondaryIndexes"):
        for item in table_schema["GlobalSecondaryIndexes"]:
            index = {}
            for k, v in item.items():
                if k in ["IndexName", "KeySchema", "Projection", "ProvisionedThroughput"]:
                    if k == "ProvisionedThroughput":
                        # uncomment below to have same read/write capacity as original table
                        # for key in v.keys():
                        #     if key not in ["ReadCapacityUnits", "WriteCapacityUnits"]:
                        #         del v[key]

                        # comment below to have same read/write capacity as original table
                        index[k] = {"ReadCapacityUnits": 3, "WriteCapacityUnits": 1200}
                        continue
                    index[k] = v
            global_secondary_indexes.append(index)

    if table_schema.get("LocalSecondaryIndexes"):
        for item in table_schema["LocalSecondaryIndexes"]:
            index = {}
            for k, v in item.iteritems():
                if k in ["IndexName", "KeySchema", "Projection"]:
                    index[k] = v
            local_secondary_indexes.append(index)

    if global_secondary_indexes:
        keyword_args["GlobalSecondaryIndexes"] = global_secondary_indexes
    if local_secondary_indexes:
        keyword_args["LocalSecondaryIndexes"] = local_secondary_indexes

    # uncomment below to have same read/write capacity as original table
    # provisionedThroughput = table_schema['ProvisionedThroughput']
    # for key in provisionedThroughput.keys():
    #     if key not in ["ReadCapacityUnits", "WriteCapacityUnits"]:
    #         del provisionedThroughput[key]

    # keyword_args["ProvisionedThroughput"] = provisionedThroughput

    # comment below to have same read/write capacity as original table
    keyword_args["ProvisionedThroughput"] = {"ReadCapacityUnits": 3, "WriteCapacityUnits": 1200}

    if table_schema.get('StreamSpecification'):
        keyword_args['StreamSpecification'] = table_schema['StreamSpecification']

    # create copy table
    try:
        client.describe_table(TableName=dst_table)
        print("!!! Table {0} already exists. Exiting...".format(dst_table))
        sys.exit(0)
    except client.exceptions.ResourceNotFoundException:
        client.create_table(**keyword_args)

        print("*** Waiting for the new table {0} to become active".format(dst_table))
        sleep(5)

        while client.describe_table(TableName=dst_table)['Table']['TableStatus'] != 'ACTIVE':
            sys.stdout.write(spinner.next())
            sys.stdout.flush()
            sleep(0.1)
            sys.stdout.write('\b')
        print("*** New table {0} to is now active!".format(dst_table))


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: {0} <source_table_name> <destination_table_name> <isLocal>".format(sys.argv[0]))
        sys.exit(1)

    table_1 = sys.argv[1]
    table_2 = sys.argv[2]
    isLocal = sys.argv[3]
    # defaults to us-west-2
    region = os.getenv('AWS_DEFAULT_REGION', os.getenv('AWS_REGION', 'us-west-2'))

    if not isLocal:
        iam_role = boto3.session.Session(profile_name='default')
        db_client = iam_role.client('dynamodb')
    else:
        db_client = boto3.client('dynamodb', endpoint_url=localDynamoHost)


    create_table(table_1, table_2, db_client)

    pool_size = 4  # tested with 4, took 5 minutes to copy 150,000+ items
    pool = []

    for i in range(pool_size):
        worker = multiprocessing.Process(
            target=copy_items,
            kwargs={
                'src_table': table_1,
                'dst_table': table_2,
                'client': db_client,
                'segment': i,
                'total_segments': pool_size
            }
        )
        pool.append(worker)
        worker.start()

    for process in pool:
        process.join()

    print("*** All Jobs Done. Exiting... ***")
