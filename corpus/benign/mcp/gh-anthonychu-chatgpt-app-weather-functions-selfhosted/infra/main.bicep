targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name of the the environment which is used to generate a short unique hash used in all resources.')
param environmentName string

// AUTHENTICATION DISABLED - Uncomment the parameters below to re-enable authentication
// @description('References application or service contact information from a Service or Asset Management database')
// param serviceManagementReference string = ''
// 
// @description('Comma-separated list of client application IDs to pre-authorize for accessing the MCP API (optional)')
// param preAuthorizedClientIds string = ''
// 
// @description('OAuth2 delegated permissions for App Service Authentication login flow')
// param delegatedPermissions array = ['User.Read']
// 
// @description('Token exchange audience for sovereign cloud deployments (optional)')
// param tokenExchangeAudience string = ''

@minLength(1)
@description('Primary location for all resources & Flex Consumption Function App')
@allowed([
  'australiaeast'
  'australiasoutheast'
  'brazilsouth'
  'canadacentral'
  'centralindia'
  'centralus'
  'eastasia'
  'eastus'
  'eastus2'
  'eastus2euap'
  'francecentral'
  'germanywestcentral'
  'italynorth'
  'japaneast'
  'koreacentral'
  'northcentralus'
  'northeurope'
  'norwayeast'
  'southafricanorth'
  'southcentralus'
  'southeastasia'
  'southindia'
  'spaincentral'
  'swedencentral'
  'uaenorth'
  'uksouth'
  'ukwest'
  'westcentralus'
  'westeurope'
  'westus'
  'westus2'
  'westus3'
])
@metadata({
  azd: {
    type: 'location'
  }
})
param location string
param vnetEnabled bool = true // Enable VNet by default
param appServiceName string = ''
param apiUserAssignedIdentityName string = ''
param applicationInsightsName string = ''
param appServicePlanName string = ''
param logAnalyticsName string = ''
param resourceGroupName string = ''
param storageAccountName string = ''
param vNetName string = ''
@description('Id of the user identity to be used for testing and debugging. This is not required in production. Leave empty if not needed.')
param principalId string = ''

var abbrs = loadJsonContent('./abbreviations.json')
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))
var tags = { 'azd-env-name': environmentName }
var functionAppName = !empty(appServiceName) ? appServiceName : '${abbrs.webSitesFunctions}app-${resourceToken}'
var deploymentStorageContainerName = 'app-package-${take(functionAppName, 32)}-${take(toLower(uniqueString(functionAppName, resourceToken)), 7)}'

// AUTHENTICATION DISABLED - Uncomment the line below to re-enable authentication
// Convert comma-separated string to array for pre-authorized client IDs
// var preAuthorizedClientIdsArray = !empty(preAuthorizedClientIds) ? map(split(preAuthorizedClientIds, ','), clientId => trim(clientId)) : []

// Organize resources in a resource group
resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: !empty(resourceGroupName) ? resourceGroupName : '${abbrs.resourcesResourceGroups}${environmentName}'
  location: location
  tags: tags
}

// User assigned managed identity to be used by the function app to reach storage and other dependencies
// Assign specific roles to this identity in the RBAC module
module appUserAssignedIdentity 'br/public:avm/res/managed-identity/user-assigned-identity:0.4.1' = {
  name: 'appUserAssignedIdentity'
  scope: rg
  params: {
    location: location
    tags: tags
    name: !empty(apiUserAssignedIdentityName) ? apiUserAssignedIdentityName : '${abbrs.managedIdentityUserAssignedIdentities}app-${resourceToken}'
  }
}

// Create an App Service Plan to group applications under the same payment plan and SKU
module appServicePlan 'br/public:avm/res/web/serverfarm:0.1.1' = {
  name: 'appserviceplan'
  scope: rg
  params: {
    name: !empty(appServicePlanName) ? appServicePlanName : '${abbrs.webServerFarms}${resourceToken}'
    sku: {
      name: 'FC1'
      tier: 'FlexConsumption'
    }
    reserved: true
    location: location
    tags: tags
  }
}

// AUTHENTICATION DISABLED - Uncomment the module below to re-enable Entra ID app registration
// Entra ID application registration for authentication (with predictable hostname)
// module entraApp 'app/entra.bicep' = {
//   name: 'entraApp'
//   scope: rg
//   params: {
//     appUniqueName: '${functionAppName}-app'
//     appDisplayName: 'Authorization App'
//     serviceManagementReference: serviceManagementReference
//     functionAppHostname: '${functionAppName}.azurewebsites.net'
//     preAuthorizedClientIds: preAuthorizedClientIdsArray
//     managedIdentityClientId: appUserAssignedIdentity.outputs.clientId
//     managedIdentityPrincipalId: appUserAssignedIdentity.outputs.principalId
//     tags: tags
//   }
// }

module app './app/app.bicep' = {
  name: 'app'
  scope: rg
  params: {
    name: functionAppName
    location: location
    tags: tags
    applicationInsightsName: monitoring.outputs.name
    appServicePlanId: appServicePlan.outputs.resourceId
    runtimeName: 'python'
    runtimeVersion: '3.12'
    storageAccountName: storage.outputs.name
    enableBlob: storageEndpointConfig.enableBlob
    enableQueue: storageEndpointConfig.enableQueue
    enableTable: storageEndpointConfig.enableTable
    deploymentStorageContainerName: deploymentStorageContainerName
    identityId: appUserAssignedIdentity.outputs.resourceId
    identityClientId: appUserAssignedIdentity.outputs.clientId
    // AUTHENTICATION DISABLED - Uncomment the line below to re-enable pre-authorized client IDs
    // preAuthorizedClientIds: preAuthorizedClientIdsArray
    appSettings: {
      PYTHONPATH: '/home/site/wwwroot/.python_packages/lib/site-packages'
      AzureWebJobsFeatureFlags: 'EnableMcpCustomHandlerPreview'
    }
    virtualNetworkSubnetId: vnetEnabled ? serviceVirtualNetwork!.outputs.appSubnetID : ''
    // AUTHENTICATION DISABLED - Uncomment the authorization parameters below to re-enable authentication
    // Authorization parameters
    // authClientId: entraApp.outputs.applicationId
    // authIdentifierUri: entraApp.outputs.identifierUri
    // authExposedScopes: entraApp.outputs.exposedScopes
    // authTenantId: tenant().tenantId
    // delegatedPermissions: delegatedPermissions
    // tokenExchangeAudience: tokenExchangeAudience
  }
}

// Backing storage for Azure functions backend API
module storage 'br/public:avm/res/storage/storage-account:0.8.3' = {
  name: 'storage'
  scope: rg
  params: {
    name: !empty(storageAccountName) ? storageAccountName : '${abbrs.storageStorageAccounts}${resourceToken}'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false // Disable local authentication methods as per policy
    dnsEndpointType: 'Standard'
    publicNetworkAccess: vnetEnabled ? 'Disabled' : 'Enabled'
    networkAcls: vnetEnabled ? {
      defaultAction: 'Deny'
      bypass: 'None'
    } : {
      defaultAction: 'Allow'
      bypass: 'AzureServices'
    }
    blobServices: {
      containers: [{name: deploymentStorageContainerName}]
    }
    minimumTlsVersion: 'TLS1_2'  // Enforcing TLS 1.2 for better security
    location: location
    tags: tags
  }
}

// Define the configuration object locally to pass to the modules
var storageEndpointConfig = {
  enableBlob: true  // Required for AzureWebJobsStorage, .zip deployment, Event Hubs trigger and Timer trigger checkpointing
  enableQueue: false  // Required for Durable Functions and MCP trigger
  enableTable: false  // Required for Durable Functions and OpenAI triggers and bindings
  enableFiles: false   // Not required, used in legacy scenarios
  allowUserIdentityPrincipal: true   // Allow interactive user identity to access for testing and debugging
}

// Consolidated Role Assignments
module rbac 'app/rbac.bicep' = {
  name: 'rbacAssignments'
  scope: rg
  params: {
    storageAccountName: storage.outputs.name
    appInsightsName: monitoring.outputs.name
    managedIdentityPrincipalId: appUserAssignedIdentity.outputs.principalId
    userIdentityPrincipalId: principalId
    enableBlob: storageEndpointConfig.enableBlob
    enableQueue: storageEndpointConfig.enableQueue
    enableTable: storageEndpointConfig.enableTable
    allowUserIdentityPrincipal: storageEndpointConfig.allowUserIdentityPrincipal
  }
}

// Virtual Network & private endpoint to blob storage
module serviceVirtualNetwork 'app/vnet.bicep' =  if (vnetEnabled) {
  name: 'serviceVirtualNetwork'
  scope: rg
  params: {
    location: location
    tags: tags
    vNetName: !empty(vNetName) ? vNetName : '${abbrs.networkVirtualNetworks}${resourceToken}'
  }
}

module storagePrivateEndpoint 'app/storage-PrivateEndpoint.bicep' = if (vnetEnabled) {
  name: 'servicePrivateEndpoint'
  scope: rg
  params: {
    location: location
    tags: tags
    virtualNetworkName: !empty(vNetName) ? vNetName : '${abbrs.networkVirtualNetworks}${resourceToken}'
    subnetName: vnetEnabled ? serviceVirtualNetwork!.outputs.peSubnetName : '' // Keep conditional check for safety, though module won't run if !vnetEnabled
    resourceName: storage.outputs.name
    enableBlob: storageEndpointConfig.enableBlob
    enableQueue: storageEndpointConfig.enableQueue
    enableTable: storageEndpointConfig.enableTable
  }
}

// Monitor application with Azure Monitor - Log Analytics and Application Insights
module logAnalytics 'br/public:avm/res/operational-insights/workspace:0.7.0' = {
  name: '${uniqueString(deployment().name, location)}-loganalytics'
  scope: rg
  params: {
    name: !empty(logAnalyticsName) ? logAnalyticsName : '${abbrs.operationalInsightsWorkspaces}${resourceToken}'
    location: location
    tags: tags
    dataRetention: 30
  }
}
 
module monitoring 'br/public:avm/res/insights/component:0.4.1' = {
  name: '${uniqueString(deployment().name, location)}-appinsights'
  scope: rg
  params: {
    name: !empty(applicationInsightsName) ? applicationInsightsName : '${abbrs.insightsComponents}${resourceToken}'
    location: location
    tags: tags
    workspaceResourceId: logAnalytics.outputs.resourceId
    disableLocalAuth: true
  }
}

// App outputs
output APPLICATIONINSIGHTS_CONNECTION_STRING string = monitoring.outputs.connectionString
output AZURE_LOCATION string = location
output AZURE_TENANT_ID string = tenant().tenantId
output SERVICE_APP_NAME string = app.outputs.SERVICE_APP_NAME
output SERVICE_APP_DEFAULT_HOSTNAME string = app.outputs.SERVICE_APP_DEFAULT_HOSTNAME
output AZURE_FUNCTION_NAME string = app.outputs.SERVICE_APP_NAME

// AUTHENTICATION DISABLED - Uncomment the outputs below to re-enable authentication outputs
// Entra App outputs (using the initial app for core properties)
// output ENTRA_APPLICATION_ID string = entraApp.outputs.applicationId
// output ENTRA_APPLICATION_OBJECT_ID string = entraApp.outputs.applicationObjectId
// output ENTRA_SERVICE_PRINCIPAL_ID string = entraApp.outputs.servicePrincipalId
// output ENTRA_IDENTIFIER_URI string = entraApp.outputs.identifierUri
// 
// // Authorization outputs
// output AUTH_ENABLED bool = mcp.outputs.AUTH_ENABLED
// output CONFIGURED_SCOPES string = mcp.outputs.CONFIGURED_SCOPES
// 
// // Pre-authorized applications
// output PRE_AUTHORIZED_CLIENT_IDS string = preAuthorizedClientIds
// 
// // Entra App redirect URI outputs (using predictable hostname)
// output CONFIGURED_REDIRECT_URIS array = entraApp.outputs.configuredRedirectUris
// output AUTH_REDIRECT_URI string = entraApp.outputs.authRedirectUri
