import express from "express";
import cors from "cors";
import { initializeApp } from "firebase-admin/app";
import { getAuth } from "firebase-admin/auth";
import { McpUserService } from "./mcp.ts";
import {
  PortalService,
  type Error,
  type ApiHubApi,
  type ApiHubApiVersion,
  type ApiHubApiVersionSpecContents,
} from "apigee-portal-module";

const firebaseApp = initializeApp();

const app = express();
app.use(cors());
app.use(express.static("public")); // for static hosting
app.use(express.json()); // for json data

const projectId = process.env.GCLOUD_PROJECT ?? process.env.PROJECT_ID;
const region = process.env.GCLOUD_REGION ?? process.env.REGION;
console.log(`Starting with project ${projectId} and region ${region}`);

const portalService = new PortalService(projectId, region);
const mcpUserService = new McpUserService(portalService);

const getAuthToken = (req, res, next) => {
  if (
    req.headers.authorization &&
    req.headers.authorization.split(" ")[0] === "Bearer"
  ) {
    req.authToken = req.headers.authorization.split(" ")[1];
  } else {
    req.authToken = null;
  }
  next();
};

export const checkIfAuthenticated = (req, res, next) => {
  getAuthToken(req, res, async () => {
    try {
      const { authToken } = req;
      const userInfo = await getAuth().verifyIdToken(authToken);
      req.authId = userInfo.uid;
      return next();
    } catch (e) {
      return res
        .status(401)
        .send({ error: "You are not authorized to make this request" });
    }
  });
};

const cache: {
  apis: ApiHubApi[];
  versions: { [key: string]: ApiHubApiVersion };
  deployments: any;
  specs: any;
} = {
  apis: [],
  versions: {},
  deployments: {},
  specs: {},
};

let cachePromise = loadCache();

app.post("/cache-refresh", (req, res) => {
  console.log("Cache refresh call received.");
  console.log(req.body);
  cachePromise = loadCache();
});

app.get("/config", (req, res) => {
  res.json({
    serviceUrl: process.env.SERVICE_URL,
    apigeeAgentUrl: process.env.APIGEE_AGENT_URL,
    authApiKey: process.env.AUTH_API_KEY,
    authDomain: process.env.AUTH_DOMAIN,
  });
});

app.get("/apis", async (req, res) => {
  if (cachePromise) await cachePromise;
  res.send({
    apis: cache.apis,
    versions: Object.values(cache.versions),
  });
});

app.get("/api-spec", async (req, res) => {
  let result: any = {};
  let versionName = req.query.version?.toString()
    ? req.query.version.toString()
    : "";

  if (cache.versions[versionName]) {
    result.version = cache.versions[versionName];
    result.api = result.version["apiData"];
    result.deployment = result.version["deployment"];
    result.spec = result.version["spec"];
  }

  if (result.version) res.send(result);
  else res.status(404).send("Spec not found");
});

app.post("/users", async (req, res) => {
  let errorCode = 0;

  let user = req.body;
  let result = await portalService.createDeveloper(user);

  if (result.error) errorCode = result.error.code;

  if (errorCode) {
    res.status(errorCode).send("There was an error creating the user.");
  } else res.send(req.body);
});

app.get("/users/:email/apps", checkIfAuthenticated, async (req, res) => {
  let email = req.params.email;

  let apps = await portalService.getApps(email);
  if (apps.error) res.status(apps.error.code).send(apps.error.message);
  else res.status(200).send(JSON.stringify(apps.data));
});

app.post("/users/:email/apps", checkIfAuthenticated, async (req, res) => {
  let email = req.params.email;
  let appName = req.body.name;
  let products = req.body.products;

  let app = await portalService.createApp(email, appName);
  if (app.error) res.status(app.error.code).send(app.error.message);
  else res.status(200).send(JSON.stringify(app.data));
});

app.delete(
  "/users/:email/apps/:appName",
  checkIfAuthenticated,
  async (req, res) => {
    let email = req.params.email;
    let appName = req.params.appName;

    let app = await portalService.deleteApp(email, appName);
    if (app.error) res.status(app.error.code).send(app.error.message);
    else res.status(200).send(JSON.stringify(app.data));
  },
);

app.get("/products", async (req, res) => {
  let productData = await portalService.getProducts();
  if (productData.error) {
    console.error("Error getting Apigee products.");
    console.error(productData.error);
    res.status(productData.error.code).send(productData.error.message);
  } else res.status(200).send(JSON.stringify(productData.data.apiProduct));
});

app.put(
  "/users/:email/apps/:appName/keys/:keyName/products/:productName",
  checkIfAuthenticated,
  async (req, res) => {
    let email = req.params.email;
    let appName = req.params.appName;
    let keyName = req.params.keyName;
    let productName = req.params.productName;

    let apps = await portalService.addAppKeyProducts(email, appName, keyName, [
      productName,
    ]);
    if (apps.error) res.status(apps.error.code).send(apps.error.message);
    else res.status(200).send(JSON.stringify(apps.data));
  },
);

app.delete(
  "/users/:email/apps/:appName/keys/:keyName/products/:productName",
  checkIfAuthenticated,
  async (req, res) => {
    let email = req.params.email;
    let appName = req.params.appName;
    let keyName = req.params.keyName;
    let productName = req.params.productName;

    let apps = await portalService.removeAppKeyProduct(
      email,
      appName,
      keyName,
      productName,
    );
    if (apps.error) res.status(apps.error.code).send(apps.error.message);
    else res.status(200).send(JSON.stringify(apps.data));
  },
);

// MCP
app.post("/mcp", mcpUserService.mcppost);
app.get("/mcp", mcpUserService.handleSessionRequest);
app.delete("/mcp", mcpUserService.handleSessionRequest);

async function loadCache(): Promise<boolean> {
  return new Promise(async (resolve, reject) => {
    let portalService = new PortalService(projectId, region);
    let projectApis = await portalService.getApis(
      "target_user.enum_values.values.display_name:Public",
    );
    if (projectApis.data && projectApis.data.length > 0) {
      cache.apis = projectApis.data;

      for (let api of cache.apis) {
        // get versions
        let versions = await portalService.getApiVersions(api.name);
        if (versions && versions.data && versions.data.length > 0) {
          // cache.versions = cache.versions.concat(versions.data);
          for (let version of versions.data) {
            cache.versions[version.name] = version;
            version["apiData"] = api;
            if (version.deployments && version.deployments.length > 0) {
              // get deployments
              let deploymentResult = await portalService.getApiDeployment(
                version.deployments[0],
              );
              if (deploymentResult && deploymentResult.data) {
                cache.deployments[version.name] = deploymentResult.data;
                version["deployment"] = deploymentResult.data;
              }
            }

            // get specs
            let versionSpecResult: { data: any; error: Error } =
              await portalService.getApiVersionSpecs(version.name);
            if (
              versionSpecResult.data &&
              versionSpecResult.data.specs &&
              versionSpecResult.data.specs.length &&
              versionSpecResult.data.specs.length > 0
            ) {
              let specResult: {
                data: ApiHubApiVersionSpecContents;
                error: Error;
              } = await portalService.getApiVersionSpecContents(
                versionSpecResult.data.specs[0]["name"],
              );

              if (specResult.data) {
                cache.specs[version.name] = specResult.data;
                version["spec"] = specResult.data;
              }
            }
          }
        }
      }
    }

    mcpUserService.updateCache(cache);
    resolve(true);
  });
}

app.listen("8080", () => {
  console.log(`agentic-portal listening on port 8080`);
});
