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

# A stack whose first create failed stays in ROLLBACK_COMPLETE and can only be deleted.
status=$(aws cloudformation describe-stacks --stack-name "$stack" --query 'Stacks[0].StackStatus' --output text 2>/dev/null || true)
if [ "$status" = "ROLLBACK_COMPLETE" ]; then
  echo "$stack is in ROLLBACK_COMPLETE, deleting it first"
  aws cloudformation delete-stack --stack-name "$stack"
  aws cloudformation wait stack-delete-complete --stack-name "$stack"
fi

if ! aws cloudformation deploy "${args[@]}"; then
  echo "::group::Failed events for $stack"
  aws cloudformation describe-stack-events --stack-name "$stack" \
    --query 'StackEvents[?contains(ResourceStatus, `FAILED`)].[LogicalResourceId,ResourceStatusReason]' --output text | head -20
  echo "::endgroup::"
  exit 1
fi
