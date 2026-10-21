echo "Creating service account..."
gcloud iam service-accounts create "agentic-portal-service" --description="Service account to manage the agentic portal" \
    --display-name="Agentic Portal Service" --project $PROJECT_ID

sleep 5

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:agentic-portal-service@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/run.admin"
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:agentic-portal-service@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/eventarc.eventReceiver"
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:agentic-portal-service@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/apihub.admin"
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:agentic-portal-service@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/apigee.admin"

echo "Updating API hub style types..."
curl -X PATCH "https://apihub.googleapis.com/v1/projects/$PROJECT_ID/locations/$REGION/attributes/system-api-style?updateMask=allowedValues" \
-H "Authorization: Bearer $(gcloud auth print-access-token)" \
-H 'Content-Type: application/json; charset=utf-8' \
--data-binary @- << EOF

{
  "name": "projects/$PROJECT_ID/locations/$REGION/attributes/system-api-style",
  "displayName": "API Style",
  "description": "API style attribute",
  "definitionType": "SYSTEM_DEFINED",
  "scope": "API",
  "dataType": "ENUM",
  "allowedValues": [
    {
      "id": "rest",
      "displayName": "REST",
      "description": "REST",
      immutable: true
    },
    {
      "id": "grpc",
      "displayName": "gRPC",
      "description": "gRPC",
      immutable: true
    },
    {
      "id": "async-api",
      "displayName": "AsyncAPI",
      "description": "AsyncAPI",
      immutable: true
    },
    {
      "id": "soap",
      "displayName": "SOAP",
      "description": "SOAP",
      immutable: true
    },
    {
      "id": "graphql",
      "displayName": "GraphQL",
      "description": "GraphQL",
      immutable: true
    },
    {
      "id": "mcp-api",
      "displayName": "MCP",
      "description": "MCP",
      immutable: true
    },
    {
      "id": "a2a-api",
      "displayName": "A2A",
      "description": "A2A"
    },
    {
      "id": "json-rpc",
      "displayName": "JSON-RPC",
      "description": "JSON-RPC"
    }
  ],
  "cardinality": 1,
}
EOF
