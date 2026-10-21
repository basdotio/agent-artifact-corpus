SECONDS=0

gcloud run deploy agentic-portal --source . --project $PROJECT_ID --region $REGION --allow-unauthenticated \
    --set-env-vars "PROJECT_ID=$PROJECT_ID,REGION=$REGION,AUTH_API_KEY=$AUTH_API_KEY,AUTH_DOMAIN=$AUTH_DOMAIN,APIGEE_AGENT_URL=$APIGEE_AGENT_URL" \
    --service-account "agentic-portal-service@$PROJECT_ID.iam.gserviceaccount.com"

duration=$SECONDS
echo "Total deployment finished in $((duration / 60)) minutes and $((duration % 60)) seconds."
