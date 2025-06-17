# Deploying PDF Parser to Azure App Service

This document provides step-by-step instructions for deploying the PDF Parser application to Azure App Service.

## Prerequisites

1. An Azure account with an active subscription
2. Azure CLI installed on your computer (or use the Azure Cloud Shell)
3. Git installed on your computer
4. VS Code with the Azure App Service extension installed

## Deployment Steps

### 1. Sign in to Azure

```bash
az login
```

### 2. Set up Variables

```bash
# Replace these values with your own
RESOURCE_GROUP="pdf-parser-rg"
LOCATION="eastus"
APP_SERVICE_PLAN="pdf-parser-plan"
WEB_APP_NAME="pdf-parser-app"  # Must be globally unique
```

### 3. Create a Resource Group

```bash
az group create --name $RESOURCE_GROUP --location $LOCATION
```

### 4. Create an App Service Plan

```bash
az appservice plan create --name $APP_SERVICE_PLAN --resource-group $RESOURCE_GROUP --sku B1 --is-linux
```

### 5. Create a Web App

```bash
az webapp create --resource-group $RESOURCE_GROUP --plan $APP_SERVICE_PLAN --name $WEB_APP_NAME --runtime "PYTHON|3.10"
```

### 6. Configure the Web App

```bash
# Set startup command
az webapp config set --resource-group $RESOURCE_GROUP --name $WEB_APP_NAME --startup-file "gunicorn --bind=0.0.0.0 --timeout 600 app:app"

# Set environment variables
az webapp config appsettings set --resource-group $RESOURCE_GROUP --name $WEB_APP_NAME --settings SECRET_KEY=$(openssl rand -hex 24)
```

### 7. Deploy Code using VS Code

#### Option A: Using VS Code Azure App Service Extension

1. Open the project in VS Code
2. Click on the Azure icon in the Activity Bar
3. Navigate to APP SERVICE under your subscription
4. Right-click on the web app you created and select "Deploy to Web App..."
5. Select the current workspace when prompted
6. Confirm the deployment

#### Option B: Using Local Git Deployment

1. Configure local git deployment:

```bash
az webapp deployment source config-local-git --name $WEB_APP_NAME --resource-group $RESOURCE_GROUP
```

2. Get the deployment URL:

```bash
DEPLOYMENT_URL=$(az webapp deployment source config-local-git --name $WEB_APP_NAME --resource-group $RESOURCE_GROUP --query url -o tsv)
echo $DEPLOYMENT_URL
```

3. Add the Azure remote and push your code:

```bash
git remote add azure $DEPLOYMENT_URL
git push azure main
```

### 8. Install System Dependencies

The PDF Parser application requires system dependencies such as Ghostscript and other libraries. You can install these by using a custom startup script or by setting up a custom Docker container.

For basic setup with startup.sh, the App Service will run your startup script which installs the necessary dependencies.

### 9. Verify Deployment

Once deployed, you can access your application at:

```
https://$WEB_APP_NAME.azurewebsites.net
```

### 10. Monitoring and Logging

To monitor your application and view logs:

```bash
# Stream logs
az webapp log tail --name $WEB_APP_NAME --resource-group $RESOURCE_GROUP

# Configure logging
az webapp log config --name $WEB_APP_NAME --resource-group $RESOURCE_GROUP --application-logging filesystem
```

## Troubleshooting

If your deployment fails or the application doesn't work as expected:

1. Check the logs using the command above
2. Make sure your requirements.txt file includes all necessary dependencies
3. Verify that your application runs successfully locally
4. Check if your web.config file is properly configured
5. Ensure that system dependencies are installed via your startup script

## Additional Resources

- [Deploy a Python web app to Azure App Service](https://docs.microsoft.com/azure/app-service/quickstart-python)
- [Configure a Linux Python app for Azure App Service](https://docs.microsoft.com/azure/app-service/configure-language-python)
- [Troubleshoot a Python app in Azure App Service](https://docs.microsoft.com/azure/app-service/troubleshoot-python)
