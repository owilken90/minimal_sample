import datetime
import json
import os
from datetime import datetime, timedelta
import re
import difflib
import warnings

import boto3
from boto3.dynamodb import conditions
from boto3.dynamodb.conditions import Attr

import base64

from . import config_backend
from .utils import json_utils
from .utils import escape

MODE = os.getenv("MODE")
SUBDOMAIN = os.getenv("SUBDOMAIN",'')
LOCK_TABLE_NAME = "LOCK"


def acquire_lock(
    resource_name: str, transaction_id: str, timeout_in_seconds: int = 40
) -> bool:
    if MODE != "PROD":
        return True

    dynamodb = boto3.resource("dynamodb")
    ex = dynamodb.meta.client.exceptions
    table = dynamodb.Table(LOCK_TABLE_NAME)

    now = datetime.now().isoformat(timespec="seconds")
    new_timeout = (datetime.now() + timedelta(seconds=timeout_in_seconds)).isoformat(
        timespec="seconds"
    )

    try:
        table.update_item(
            Key={"PK": "LOCK", "SK": f"RES#{resource_name}"},
            UpdateExpression="SET #tx_id = :tx_id, #timeout = :timeout",
            ExpressionAttributeNames={
                "#tx_id": "transaction_id",
                "#timeout": "timeout",
            },
            ExpressionAttributeValues={
                ":tx_id": transaction_id,
                ":timeout": new_timeout,
            },
            ConditionExpression=conditions.Or(
                conditions.Attr("SK").not_exists(),  # New Item, i.e. no lock
                conditions.Attr("timeout").lt(now),  # Old lock is timed out
            ),
        )

        return True

    except ex.ConditionalCheckFailedException:
        # It's already locked
        return False


def release_lock(resource_name: str, transaction_id: str) -> bool:
    if MODE != "PROD":
        return True

    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(LOCK_TABLE_NAME)

    ex = dynamodb.meta.client.exceptions

    try:
        table.delete_item(
            Key={"PK": "LOCK", "SK": f"RES#{resource_name}"},
            ConditionExpression=conditions.Attr("transaction_id").eq(transaction_id),
        )
        return True

    except (ex.ConditionalCheckFailedException, ex.ResourceNotFoundException):
        return False


def decode_jwt_payload(jwt_token):
    payload = jwt_token.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    return base64.urlsafe_b64decode(payload).decode("utf-8")

def do_read_task_json(file_path):
    if MODE == "DEV_FILE":
        with open(file_path, "r") as file:
            task_json = json.load(file)
    else:
        dbclient = boto3.client("dynamodb")
        task_json = dbclient.get_item(
            TableName=config_backend.DB_TABLE[MODE],
            Key={"part": {"S": " "}, "filepath": {"S": file_path}},
        )["Item"]["task_json"]["S"]
        task_json = json.loads(task_json)
    return task_json

def do_save_task_json(file_path, json_obj):
    if MODE == "DEV_FILE":
        with open(file_path, "w") as file:
            json.dump(json_obj, file)
    else:
        dbclient = boto3.client("dynamodb")
        dbclient.put_item(
            TableName=config_backend.DB_TABLE[MODE],
            Item={
                "part": {"S": " "},
                "filepath": {"S": file_path},
                "task_json": {"S": json.dumps(json_obj)},
                "last_updated": {"S": datetime.now().isoformat(timespec="seconds")},
            },
        )


def list_tasks_of_user(path):
    table = boto3.resource("dynamodb").Table(config_backend.DB_TABLE[MODE])
    base_path = path
    task_names = [
        res["filepath"][len(base_path) + 1 :]
        for res in table.scan(
            Select="ALL_ATTRIBUTES",
            FilterExpression=Attr("filepath").begins_with(base_path),
        )["Items"]
    ]
    return task_names
