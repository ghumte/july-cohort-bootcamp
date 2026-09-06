#!/usr/bin/env bash
# Deploy CloudFormation stack: ECR, ECS cluster, Redis, ALB, IAM, logs.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

: "${AWS_REGION:?Set AWS_REGION}"

STACK_NAME="${STACK_NAME:-aws-agent-deployment-demo}"
PROJECT_NAME="${PROJECT_NAME:-aws-agent-deployment-demo}"

if [[ -z "${VPC_ID:-}" ]]; then
  VPC_ID="$(aws ec2 describe-vpcs --region "${AWS_REGION}" \
    --filters Name=isDefault,Values=true \
    --query 'Vpcs[0].VpcId' --output text)"
fi

if [[ -z "${SUBNET_IDS:-}" ]]; then
  SUBNET_IDS="$(aws ec2 describe-subnets --region "${AWS_REGION}" \
    --filters Name=vpc-id,Values="${VPC_ID}" \
    --query 'Subnets[0:2].SubnetId' --output text | tr '\t' ',')"
fi

echo "Deploying stack: ${STACK_NAME}"
echo "  Region:  ${AWS_REGION}"
echo "  VPC:     ${VPC_ID}"
echo "  Subnets: ${SUBNET_IDS}"
echo "ElastiCache usually takes 5–10 minutes."

aws cloudformation deploy \
  --region "${AWS_REGION}" \
  --stack-name "${STACK_NAME}" \
  --template-file "${PROJECT_ROOT}/aws/cloudformation/stack.yaml" \
  --parameter-overrides \
    ProjectName="${PROJECT_NAME}" \
    VpcId="${VPC_ID}" \
    SubnetIds="${SUBNET_IDS}" \
  --capabilities CAPABILITY_NAMED_IAM \
  --no-fail-on-empty-changeset

echo "Syncing Redis URL into Secrets Manager..."
"${SCRIPT_DIR}/set_redis_secret.sh"

echo "Stack deployed. Next: source ./scripts/load_stack_outputs.sh"
