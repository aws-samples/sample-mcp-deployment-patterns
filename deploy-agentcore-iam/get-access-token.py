#!/usr/bin/env python3
"""Authenticate with Cognito and store an AgentCore access token securely."""

import argparse
import base64
import getpass
import hashlib
import hmac
import json
import os
import sys
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv


def get_secret_hash(username: str, client_id: str, client_secret: str) -> str:
    """Calculate the Cognito SECRET_HASH value."""
    message = (username + client_id).encode("utf-8")
    digest = hmac.new(
        client_secret.encode("utf-8"),
        msg=message,
        digestmod=hashlib.sha256,
    ).digest()
    return base64.b64encode(digest).decode("ascii")


def inspect_access_token(token: str) -> dict[str, bool]:
    """Read only non-identifying claim presence from an unverified JWT payload."""
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload).decode("utf-8"))
    except (IndexError, ValueError, json.JSONDecodeError):
        return {"client_id": False, "aud": False, "exp": False}

    return {
        "client_id": "client_id" in claims,
        "aud": "aud" in claims,
        "exp": "exp" in claims,
    }


def write_token(path: Path, token: str) -> Path:
    """Write a token to an owner-only file without following symlinks."""
    output_path = path.expanduser().absolute()
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(output_path, flags, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as token_file:
        token_file.write(token)
        token_file.write("\n")
    os.chmod(output_path, 0o600)
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Authenticate with Cognito without printing tokens or claims."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent / ".agentcore-access-token",
        help="Owner-only file that will receive the access token.",
    )
    args = parser.parse_args()

    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    config = {
        "COGNITO_USER_POOL_ID": os.getenv("COGNITO_USER_POOL_ID"),
        "COGNITO_CLIENT_ID": os.getenv("COGNITO_CLIENT_ID"),
        "COGNITO_CLIENT_SECRET": os.getenv("COGNITO_CLIENT_SECRET"),
        "COGNITO_REGION": os.getenv("COGNITO_REGION"),
        "COGNITO_USERNAME": os.getenv("COGNITO_USERNAME"),
    }
    missing = [name for name, value in config.items() if not value]
    if missing:
        print(
            f"Missing required environment variables: {', '.join(missing)}",
            file=sys.stderr,
        )
        return 1

    password = os.getenv("COGNITO_PASSWORD") or getpass.getpass("Cognito password: ")
    client = boto3.client("cognito-idp", region_name=config["COGNITO_REGION"])

    try:
        response = client.initiate_auth(
            ClientId=config["COGNITO_CLIENT_ID"],
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": config["COGNITO_USERNAME"],
                "PASSWORD": password,
                "SECRET_HASH": get_secret_hash(
                    config["COGNITO_USERNAME"],
                    config["COGNITO_CLIENT_ID"],
                    config["COGNITO_CLIENT_SECRET"],
                ),
            },
        )
    except (
        client.exceptions.NotAuthorizedException,
        client.exceptions.UserNotFoundException,
    ):
        print("Authentication failed.", file=sys.stderr)
        return 1
    except ClientError as error:
        error_code = error.response.get("Error", {}).get("Code", "Unknown")
        print(f"Cognito request failed ({error_code}).", file=sys.stderr)
        return 1

    access_token = response["AuthenticationResult"]["AccessToken"]
    token_metadata = inspect_access_token(access_token)
    output_path = write_token(args.output, access_token)

    print("Authentication succeeded.")
    print(f"client_id claim present: {token_metadata['client_id']}")
    print(f"aud claim present: {token_metadata['aud']}")
    print(f"expiration claim present: {token_metadata['exp']}")
    print(f"Access token written to owner-only file: {output_path}")
    print("Delete the token file when testing is complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
