gcloud eventarc triggers create api-create-trigger --event-filters="type=google.cloud.apihub.api.v1.created" \
    --destination-run-service="agentic-portal" --destination-run-path="/cache-refresh" --location=$REGION --project=$PROJECT_ID \
    --service-account="agentic-portal-service@$PROJECT_ID.iam.gserviceaccount.com"
gcloud eventarc triggers create api-update-trigger --event-filters="type=google.cloud.apihub.api.v1.updated" \
    --destination-run-service="agentic-portal" --destination-run-path="/cache-refresh" --location=$REGION --project=$PROJECT_ID \
    --service-account="agentic-portal-service@$PROJECT_ID.iam.gserviceaccount.com"
