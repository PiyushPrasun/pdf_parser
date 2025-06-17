#!/bin/bash

echo "========================================================="
echo "Preparing to deploy PDF Parser to Azure App Service"
echo "========================================================="

# Log in to Azure (you'll be prompted for credentials)
echo "Please log in to your Azure account:"
az login

# List available subscriptions
echo "Available Azure subscriptions:"
az account list --output table

# Prompt to select a subscription
echo "Enter the subscription ID you want to use (or press Enter to use the default):"
read SUBSCRIPTION_ID

if [ ! -z "$SUBSCRIPTION_ID" ]; then
    az account set --subscription $SUBSCRIPTION_ID
    echo "Using subscription: $SUBSCRIPTION_ID"
else
    echo "Using default subscription"
fi

# Create a resource group if it doesn't exist
echo "Enter a name for your resource group (e.g., pdf-parser-rg):"
read RESOURCE_GROUP

echo "Enter the Azure region to deploy to (e.g., westus2, eastus):"
read LOCATION

az group create --name $RESOURCE_GROUP --location $LOCATION

# Create an App Service Plan
echo "Enter a name for your App Service Plan (e.g., pdf-parser-plan):"
read APP_SERVICE_PLAN

az appservice plan create --name $APP_SERVICE_PLAN --resource-group $RESOURCE_GROUP --sku B1 --is-linux

# Create a Web App
echo "Enter a globally unique name for your Web App (e.g., pdf-parser-app-uniquename):"
read WEB_APP_NAME

az webapp create --resource-group $RESOURCE_GROUP --plan $APP_SERVICE_PLAN --name $WEB_APP_NAME --runtime "PYTHON|3.10"

# Configure app settings
az webapp config set --resource-group $RESOURCE_GROUP --name $WEB_APP_NAME --startup-file "gunicorn --bind=0.0.0.0 --timeout 600 app:app"

# Set environment variables
echo "Setting SECRET_KEY for the app..."
az webapp config appsettings set --resource-group $RESOURCE_GROUP --name $WEB_APP_NAME --settings SECRET_KEY=$(openssl rand -hex 24)

# Deploy the code
echo "Deploying code to Azure..."
az webapp deployment source config-local-git --name $WEB_APP_NAME --resource-group $RESOURCE_GROUP

# Get deployment URL
DEPLOYMENT_URL=$(az webapp deployment source config-local-git --name $WEB_APP_NAME --resource-group $RESOURCE_GROUP --query url -o tsv)

echo "========================================================="
echo "Your deployment URL is: $DEPLOYMENT_URL"
echo "Now run the following commands to push your code:"
echo "git remote add azure $DEPLOYMENT_URL"
echo "git push azure main"
echo "========================================================="

echo "Your app will be available at: https://$WEB_APP_NAME.azurewebsites.net"
