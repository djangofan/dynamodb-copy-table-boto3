# Make copy of DynamoDB table

### Author: Jon Austen

Copy a dynamo-local with

    python3 dynamo_copy_table.py atable copy-atable true

This is a python script to make copy of AWS Dynamodb tables using boto3 library.

 Copy a online dynamo db:

    python3 dynamo_copy_table.py atable copy-atable false



### Run your own local DynamoDB-Local:

    docker run -p 8000:8000 --name dynamodb-local --restart unless-stopped -d dwmkerr/dynamodb -sharedDb

    aws dynamodb list-tables --endpoint-url http://192.168.99.100:8000

    aws dynamodb create-table --table-name Music --attribute-definitions AttributeName=Artist,AttributeType=S AttributeName=SongTitle,AttributeType=S --key-schema AttributeName=Artist,KeyType=HASH AttributeName=SongTitle,KeyType=RANGE --provisioned-throughput ReadCapacityUnits=1,WriteCapacityUnits=1



### NOTES

https://stackoverflow.com/questions/31378347/how-to-get-the-row-count-of-a-table-instantly-in-dynamodb

