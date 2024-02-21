import os
import yaml

import snowflake.connector

from titan import Blueprint
from titan.gitops import collect_resources_from_config


def crawl(path: str):
    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith(".yaml") or file.endswith(".yml"):
                yield os.path.join(root, file)


def collect_resources(path: str):
    resources = []

    for file in crawl(path):
        with open(file, "r") as f:
            config = yaml.safe_load(f)
            resources.extend(collect_resources_from_config(config))

    return resources


def main():
    # Bootstrap environment
    try:
        connection_params = {
            "account": os.environ["SNOWFLAKE_ACCOUNT"],
            "user": os.environ["SNOWFLAKE_USERNAME"],
            "password": os.environ["SNOWFLAKE_PASSWORD"],
            "role": os.environ["SNOWFLAKE_ROLE"],
            "warehouse": os.environ["SNOWFLAKE_WAREHOUSE"],
        }
        workspace = os.environ["GITHUB_WORKSPACE"]

        # Inputs
        dry_run = bool(os.environ["INPUT_DRY-RUN"].lower().capitalize())
        resource_path = os.environ["INPUT_RESOURCE-PATH"]
        allowed_resources = os.environ.get("INPUT_ALLOWED-RESOURCES", "all")
    except KeyError as e:
        raise ValueError(f"Missing environment variable: {e}") from e

    resources = collect_resources(os.path.join(workspace, resource_path))
    blueprint = Blueprint(name="snowflake-gitops", resources=resources, dry_run=dry_run)
    conn = snowflake.connector.connect(**connection_params)
    blueprint.plan(conn)
    blueprint.apply(conn)


if __name__ == "__main__":
    main()
