#!/usr/bin/env bash
# Run a single Athena query against the Reown analytics warehouse and print results.
#
# Usage:
#   athena-query.sh "SELECT COUNT(*) FROM prod_warehouse.fact_relay__sessions WHERE dt = CURRENT_DATE"
#
# Env overrides (sensible defaults for the analytics account):
#   PROFILE    AWS profile (default: Administrator-898587786287 — Read-Only cannot start queries)
#   REGION     AWS region   (default: eu-central-1)
#   WORKGROUP  Athena workgroup (default: dbt_prod_workgroup — has its own S3 output location)
#
# Requires a valid SSO session. If you see "Token has expired", run (interactive, opens a browser):
#   aws sso login --sso-session rs-relay-analytics
set -euo pipefail

QUERY="${1:?usage: athena-query.sh \"<SQL>\"}"
PROFILE="${PROFILE:-Administrator-898587786287}"
REGION="${REGION:-eu-central-1}"
WORKGROUP="${WORKGROUP:-dbt_prod_workgroup}"

aws() { command aws --profile "$PROFILE" --region "$REGION" "$@"; }

QID=$(aws athena start-query-execution \
  --work-group "$WORKGROUP" \
  --query-string "$QUERY" \
  --query 'QueryExecutionId' --output text)
echo "query-execution-id: $QID" >&2

# Poll until terminal state.
while true; do
  STATE=$(aws athena get-query-execution --query-execution-id "$QID" \
            --query 'QueryExecution.Status.State' --output text)
  case "$STATE" in
    SUCCEEDED) break ;;
    FAILED|CANCELLED)
      REASON=$(aws athena get-query-execution --query-execution-id "$QID" \
                 --query 'QueryExecution.Status.StateChangeReason' --output text)
      echo "query $STATE: $REASON" >&2
      exit 1 ;;
  esac
  sleep 2
done

# Results as tab-separated rows (row 0 is the header). get-query-results pages at
# 1000 rows — for large result sets prefer an aggregate query (COUNT/SUM/COUNT(DISTINCT ...))
# over row counting. For multi-page extraction, paginate with --starting-token.
aws athena get-query-results --query-execution-id "$QID" \
  --query 'ResultSet.Rows[*].Data[*].VarCharValue' --output text
