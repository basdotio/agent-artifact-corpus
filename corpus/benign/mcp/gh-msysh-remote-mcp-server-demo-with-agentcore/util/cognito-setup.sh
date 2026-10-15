#!/bin/bash

REGION=us-east-1
POOL_NAME='MyUserPool'
CLIENT_NAME='MyClient'
USER_NAME='testuser'
TEMPORARY_PASSWORD='Temp123!'
PASSWORD='MyPassword123!'

# Create User Pool and capture Pool ID directly
export POOL_ID=$(aws cognito-idp create-user-pool \
  --pool-name ${POOL_NAME} \
  --policies '{"PasswordPolicy":{"MinimumLength":8}}' \
  --region ${REGION} | jq -r '.UserPool.Id')

# Create App Client and capture Client ID directly
export CLIENT_ID=$(aws cognito-idp create-user-pool-client \
  --user-pool-id ${POOL_ID} \
  --client-name ${CLIENT_NAME} \
  --no-generate-secret \
  --explicit-auth-flows "ALLOW_USER_PASSWORD_AUTH" "ALLOW_REFRESH_TOKEN_AUTH" \
  --region ${REGION} | jq -r '.UserPoolClient.ClientId')

# Create User
aws cognito-idp admin-create-user \
  --user-pool-id ${POOL_ID} \
  --username ${USER_NAME} \
  --temporary-password "${TEMPORARY_PASSWORD}" \
  --region ${REGION} \
  --message-action SUPPRESS > /dev/null

# Set Permanent Password
aws cognito-idp admin-set-user-password \
  --user-pool-id ${POOL_ID} \
  --username ${USER_NAME} \
  --password "${PASSWORD}" \
  --region ${REGION} \
  --permanent > /dev/null

# Authenticate User and capture Access Token
export BEARER_TOKEN=$(aws cognito-idp initiate-auth \
  --client-id "${CLIENT_ID}" \
  --auth-flow USER_PASSWORD_AUTH \
  --auth-parameters USERNAME="${USER_NAME}",PASSWORD="${PASSWORD}" \
  --region ${REGION} | jq -r '.AuthenticationResult.AccessToken')

# Output the required values
echo "Pool id: ${POOL_ID}"
echo "Discovery URL: https://cognito-idp.${REGION}.amazonaws.com/${POOL_ID}/.well-known/openid-configuration"
echo "Client ID: ${CLIENT_ID}"
echo "Bearer Token: ${BEARER_TOKEN}"
