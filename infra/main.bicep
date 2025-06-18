targetScope = 'resourceGroup'

@description('The name of the environment for tagging resources')
param environmentName string = 'pdf-parser'

@description('Primary location for all resources')
param location string = resourceGroup().location

@description('Unique token for resource naming')
param resourceToken string = uniqueString(subscription().id, resourceGroup().id, environmentName)

@description('Secret key for the application')
@secure()
param secretKey string = newGuid()

// Tags applied to all resources
var tags = {
  'azd-env-name': environmentName
}

// Container Apps Environment
resource containerAppEnvironment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: 'caepdfparser${resourceToken}'
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalyticsWorkspace.properties.customerId
        sharedKey: logAnalyticsWorkspace.listKeys().primarySharedKey
      }
    }
  }
}

// Log Analytics Workspace
resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: 'logpdfparser${resourceToken}'
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// User Assigned Managed Identity
resource userAssignedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'mipdfparser${resourceToken}'
  location: location
  tags: tags
}

// Container Registry
resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: 'acrpdfparser${resourceToken}'
  location: location
  tags: tags
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: true
  }
}

// Role assignment for managed identity to pull from ACR
resource acrPullRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(containerRegistry.id, userAssignedIdentity.id, 'acrPull')
  scope: containerRegistry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d') // AcrPull
    principalId: userAssignedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// Container App for PDF Parser
resource pdfParserApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'capdfparser${resourceToken}'
  location: location
  tags: union(tags, {
    'azd-service-name': 'web'
  })
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${userAssignedIdentity.id}': {}
    }
  }
  properties: {
    environmentId: containerAppEnvironment.id
    configuration: {
      ingress: {
        external: true
        targetPort: 5000
        transport: 'http'
        corsPolicy: {
          allowedOrigins: ['*']
          allowedMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
          allowedHeaders: ['*']
          allowCredentials: true
        }
      }
      registries: [
        {
          server: containerRegistry.properties.loginServer
          identity: userAssignedIdentity.id
        }
      ]
      secrets: [
        {
          name: 'secret-key'
          value: secretKey
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'pdf-parser'
          image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
          env: [
            {
              name: 'SECRET_KEY'
              secretRef: 'secret-key'
            }
            {
              name: 'PORT'
              value: '5000'
            }
          ]
          resources: {
            cpu: 1
            memory: '2Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 10
        rules: [
          {
            name: 'http-rule'
            http: {
              metadata: {
                concurrentRequests: '10'
              }
            }
          }
        ]
      }
    }
  }
}

// Output the Container App URL
output AZURE_CONTAINER_APP_URL string = 'https://${pdfParserApp.properties.configuration.ingress.fqdn}'
output AZURE_CONTAINER_APP_NAME string = pdfParserApp.name
output AZURE_CONTAINER_ENVIRONMENT_NAME string = containerAppEnvironment.name
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = containerRegistry.properties.loginServer
output AZURE_CONTAINER_REGISTRY_NAME string = containerRegistry.name
output RESOURCE_GROUP_ID string = resourceGroup().id
