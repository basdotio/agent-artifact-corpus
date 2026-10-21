# Apigee Agentic Portal Quickstart

---

This tutorial helps you deploy a quickstart agentic portal web app using Google Cloud Run, Apigee API hub, & Identity Platform.

Let's get started!

---

## Prerequisites

As a prerequisite you need a Google Cloud project with Apigee API hub already provisioned. You can find more info on getting started with API hub [here](https://docs.cloud.google.com/apigee/docs/apihub/getting-started-apihub).

You will also need Google Cloud Identity Platform to be set up to allow users to sign-in with their Google accounts to the portal. Follow the instructions [here](https://docs.cloud.google.com/identity-platform/docs/web/google) on setting it up.

You will need the **Application setup details** information later when deploying the service.

---

## Setup environment

To begin we need to set our environment variables.

First copy the example `1.env.sh` file and set your own values.

```sh
cp 1.env.sh .env
```

Click <walkthrough-editor-open-file filePath=".env">here</walkthrough-editor-open-file> to open the file in the editor.

Set your Google Cloud Project Id, region, and the **Application setup details** API key and Auth Domain from your Identity Platform setup.

Then, source the `.env` file in the shell.

```sh
source .env
```

---

## Create resources

Next we are going to create a service account **agentic-portal-service** to run our portal with, and grant access to Apigee, API hub and Eventarc to get data updates.

Click <walkthrough-editor-open-file filePath="2.pre-create.sh">here</walkthrough-editor-open-file> to open the file in the editor, and see the commands that will be run.

Now let's run the script:

```sh
./2.pre-create.sh
```

<walkthrough-footnote>You should see a lot of update information, but no errors. If you see an error, check your project permissions if you are allowed to create a service account or assign permissions.</walkthrough-footnote>

---

## Deploy service

Now we are going to deploy the agentic portal service to Cloud Run. Run the command below, and you should get a new URL returned where your portal is reachable.

```sh
./3.deploy-service.sh
```

<walkthrough-footnote>In case you get an error, check if you have the rights to deploy a Cloud Run service in your project.</walkthrough-footnote>

---

## Configure Eventarc

Eventarc will be used to get notified of any data changes in API hub, and make sure that our portal has the updated data in its cache. Run the following command to configure the Eventarc events.

```sh
./4.post-create.sh
```

---

## Conclusion
<walkthrough-conclusion-trophy></walkthrough-conclusion-trophy>

Congratulations! You've successfully deployed the agentic portal service.
<walkthrough-inline-feedback></walkthrough-inline-feedback>
