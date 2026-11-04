#!/usr/bin/env bash
# Usage: infra/deploy-stack.sh <stack-name> <template-file> [Key=Value ...]
# Creates or updates a stack with the project tags (propagated to every taggable resource).
# Needs ENVIRONMENT; IAC_VERSION defaults to "dev" (the pipeline passes the git sha).
set -euo pipefail

stack=$1 template=$2
shift 2

args=(
  --stack-name "$stack"
  --template-file "$template"
  --no-fail-on-empty-changeset
  --tags owner:team=pataporte "owner:environment=${ENVIRONMENT:?}" iac:repo-name=pataporte-aws "iac:version=${IAC_VERSION:-dev}"
)
if [ $# -gt 0 ]; then
  args+=(--parameter-overrides "$@")
fi

aws cloudformation deploy "${args[@]}"
