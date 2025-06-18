targetScope = 'resourceGroup'

metadata description = 'Main Bicep template for PDF Parser application infrastructure'

@minLength(1)
@maxLength(64)
@description('Name of the environment which is used to generate a short unique hash for resource names')
param environmentName string

@minLength(1)
@description('Primary location for all resources')
param location string = resourceGroup().location

@description('Secret key for Flask application')
@secure()
param secretKey string = ''

// Generate a unique token for resource naming
var resourceToken = toLower(uniqueString(subscription().id, resourceGroup().id, environmentName))
var resourcePrefix = 'pdf-parser'

// Container Registry
resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: 'pdfparserreg${resourceToken}'
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: true
  }
  tags: {
    'azd-env-name': environmentName
  }
}

// Log Analytics Workspace
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${resourcePrefix}-logs-${resourceToken}'
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
  tags: {
    'azd-env-name': environmentName
  }
}

// Application Insights
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${resourcePrefix}-insights-${resourceToken}'
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
  tags: {
    'azd-env-name': environmentName
  }
}

// Key Vault
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: 'pdfkv${resourceToken}'
  location: location
  properties: {
    tenantId: subscription().tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    accessPolicies: []
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
  }
  tags: {
    'azd-env-name': environmentName
  }
}

// User Assigned Managed Identity
resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${resourcePrefix}-identity-${resourceToken}'
  location: location
  tags: {
    'azd-env-name': environmentName
  }
}

// Role assignment for Key Vault access
resource keyVaultSecretsUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: keyVault
  name: guid(keyVault.id, managedIdentity.id, '4633458b-17de-408a-b874-0445c86b69e6')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6') // Key Vault Secrets User
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// Role assignment for Container Registry pull access
resource acrPullRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: containerRegistry
  name: guid(containerRegistry.id, managedIdentity.id, '7f951dda-4ed3-4680-a7ca-43fe172d538d')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d') // AcrPull
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// Container Apps Environment
resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: '${resourcePrefix}-env-${resourceToken}'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
  tags: {
    'azd-env-name': environmentName
  }
}

// Store secrets in Key Vault
resource secretKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'SECRET-KEY'
  properties: {
    value: !empty(secretKey) ? secretKey : 'dev-secret-key-${uniqueString(resourceGroup().id)}'
  }
}

resource containerRegistryUsernameSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'CONTAINER-REGISTRY-USERNAME'
  properties: {
    value: containerRegistry.listCredentials().username
  }
}

resource containerRegistryPasswordSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'CONTAINER-REGISTRY-PASSWORD'
  properties: {
    value: containerRegistry.listCredentials().passwords[0].value
  }
}

// Container App
resource containerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: '${resourcePrefix}-app-${resourceToken}'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    configuration: {
      secrets: [
        {
          name: 'secret-key'
          keyVaultUrl: '${keyVault.properties.vaultUri}secrets/SECRET-KEY'
          identity: managedIdentity.id
        }
        {
          name: 'registry-username'
          keyVaultUrl: '${keyVault.properties.vaultUri}secrets/CONTAINER-REGISTRY-USERNAME'
          identity: managedIdentity.id
        }
        {
          name: 'registry-password'
          keyVaultUrl: '${keyVault.properties.vaultUri}secrets/CONTAINER-REGISTRY-PASSWORD'
          identity: managedIdentity.id
        }
      ]
      registries: [
        {
          server: containerRegistry.properties.loginServer
          username: containerRegistry.listCredentials().username
          passwordSecretRef: 'registry-password'
          identity: managedIdentity.id
        }
      ]
      ingress: {
        external: true
        targetPort: 5000
        corsPolicy: {
          allowedOrigins: ['*']
          allowedMethods: ['*']
          allowedHeaders: ['*']
        }
      }
    }
    template: {
      containers: [
        {
          image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
          name: 'pdf-parser'
          env: [
            {
              name: 'PORT'
              value: '5000'
            }
            {
              name: 'SECRET_KEY'
              secretRef: 'secret-key'
            }
            {
              name: 'UPLOAD_FOLDER'
              value: '/tmp/uploads'
            }
            {
              name: 'MAX_CONTENT_LENGTH'
              value: '16777216'
            }
            {
              name: 'SESSION_TYPE'
              value: 'filesystem'
            }
            {
              name: 'SESSION_FILE_DIR'
              value: '/tmp/sessions'
            }
            {
              name: 'SESSION_PERMANENT'
              value: 'false'
            }
            {
              name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
              value: appInsights.properties.ConnectionString
            }
          ]
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 10
        rules: [
          {
            name: 'http-scale'
            http: {
              metadata: {
                concurrentRequests: '50'
              }
            }
          }
        ]
      }
    }
  }
  tags: {
    'azd-env-name': environmentName
    'azd-service-name': 'pdf-parser-app'
  }
  dependsOn: [
    keyVaultSecretsUser
    acrPullRole
  ]
}

// Outputs
output RESOURCE_GROUP_ID string = resourceGroup().id
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = containerRegistry.properties.loginServer
output AZURE_CONTAINER_REGISTRY_NAME string = containerRegistry.name
output AZURE_KEY_VAULT_ENDPOINT string = keyVault.properties.vaultUri
output AZURE_KEY_VAULT_NAME string = keyVault.name
output PDF_PARSER_APP_URL string = 'https://${containerApp.properties.configuration.ingress.fqdn}'
output PDF_PARSER_APP_NAME string = containerApp.name
output APPLICATIONINSIGHTS_CONNECTION_STRING string = appInsights.properties.ConnectionString
