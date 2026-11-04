#!/usr/bin/env python3
"""Upload a private, immutable frontend release. Does not switch the live distribution."""
import argparse
import hashlib
import json
import mimetypes
from pathlib import Path
import re

import boto3
from deploy_ecs import ACCOUNT, REGION, ROOT, outputs, save

ALLOWED_EXTENSIONS = {".html", ".css", ".js", ".json", ".png", ".jpg", ".jpeg", ".webp", ".svg", ".ico", ".woff", ".woff2"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-zA-Z0-9-]{1,64}", args.release):
        parser.error("release must contain 1–64 letters, digits or hyphens")
    session = boto3.Session(region_name=REGION)
    if session.client("sts").get_caller_identity()["Account"] != ACCOUNT:
        raise RuntimeError("Unexpected AWS account")
    bucket = outputs(session.client("cloudformation"), "pataporte-dev-edge")["WebBucketName"]
    s3 = session.client("s3")
    directory = ROOT / "frontend"
    manifest = {}
    files = []
    for path in sorted(directory.rglob("*")):
        if path.is_file() and not path.is_symlink() and path.suffix.lower() in ALLOWED_EXTENSIONS and not any(p.startswith(".") for p in path.relative_to(directory).parts):
            relative = path.relative_to(directory).as_posix()
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            manifest[relative] = digest
            files.append((path, relative, digest))
    if "index.html" not in manifest:
        raise RuntimeError("Missing frontend/index.html")
    # Check the entire prefix first: a failed upload can resume, but a release ID is never reused for different bytes.
    for path, relative, digest in files:
        key = f"releases/{args.release}/{relative}"
        try:
            existing = s3.head_object(Bucket=bucket, Key=key)
        except s3.exceptions.ClientError as exc:
            if exc.response["Error"]["Code"] not in {"404", "NoSuchKey", "NotFound"}:
                raise
        else:
            if existing.get("Metadata", {}).get("sha256") != digest:
                raise RuntimeError("Release ID already exists with different content; choose a new release")
    for path, relative, digest in files:
        key = f"releases/{args.release}/{relative}"
        s3.put_object(Bucket=bucket, Key=key, Body=path.read_bytes(), ServerSideEncryption="AES256",
                      ContentType=mimetypes.guess_type(path.name)[0] or "application/octet-stream",
                      CacheControl="public, max-age=300", Metadata={"sha256": digest})
        if s3.head_object(Bucket=bucket, Key=key).get("Metadata", {}).get("sha256") != digest:
            raise RuntimeError("Upload verification failed")
    save("frontend-upload", {"release": args.release, "bucket": bucket, "files": manifest, "distribution_changed": False})
    print(json.dumps({"release": args.release, "verified_files": len(files), "distribution_changed": False}))


if __name__ == "__main__":
    main()
