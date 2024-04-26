import os
import yaml

import snowflake.connector

from titan import Blueprint
from titan.blueprint import RunMode, print_plan
from titan.enums import ResourceType
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
            print(f"Reading config file: {file}")
            config = yaml.safe_load(f)
            if not config:
                print(f"Skipping empty config file: {file}")
                continue
            resources.extend(collect_resources_from_config(config))

    return resources


def str_to_bool(s: str) -> bool:
    s = s.lower()
    if s not in {"true", "false"}:
        raise ValueError(f"Invalid value for boolean: {s}")
    return s == "true"


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
        run_mode = os.environ["INPUT_RUN-MODE"]
        dry_run = str_to_bool(os.environ["INPUT_DRY-RUN"])
        resource_path = os.environ["INPUT_RESOURCE-PATH"]
        valid_resource_types = os.environ.get("INPUT_VALID-RESOURCE-TYPES", "all")
    except KeyError as e:
        raise ValueError(f"Missing environment variable: {e}") from e

    # Parse inputs
    run_mode = RunMode(run_mode)

    if valid_resource_types == "all":
        valid_resource_types = []
    else:
        valid_resource_types = [
            ResourceType(r) for r in valid_resource_types.split(",")
        ]

    # Print config
    print("Config\n------")
    print(f"\t run_mode: {run_mode}")
    print(f"\t valid_resource_types: {valid_resource_types}")
    print(f"\t dry_run: {os.environ['INPUT_DRY-RUN']} => {dry_run}")
    print(f"\t resource_path: {resource_path}")
    print(f"\t workspace: {workspace}")

    resources = collect_resources(os.path.join(workspace, resource_path))

    blueprint = Blueprint(
        name="snowflake-gitops",
        resources=resources,
        run_mode=run_mode,
        dry_run=dry_run,
        allow_role_switching=True,
        ignore_ownership=True,
        valid_resource_types=valid_resource_types,
    )
    print(resources)
    conn = snowflake.connector.connect(**connection_params)
    plan = blueprint.plan(conn)
    print_plan(plan)
    blueprint.apply(conn, plan)


if __name__ == "__main__":
    main()
