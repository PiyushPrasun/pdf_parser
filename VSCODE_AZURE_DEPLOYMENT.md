# Deploying PDF Parser using VS Code Azure Extensions

This guide shows you how to deploy the PDF Parser application using VS Code Azure extensions instead of Azure CLI.

## 📋 Prerequisites

### Required VS Code Extensions
Make sure you have these extensions installed:
- **Azure Container Apps** (`ms-azuretools.vscode-azurecontainerapps`)
- **Azure App Service** (`ms-azuretools.vscode-azureappservice`) 
- **Docker** (`ms-azuretools.vscode-docker`)
- **Azure Resources** (`ms-azuretools.vscode-azureresourcegroups`)
- **Azure Tools** (`ms-vscode.azure-tools`)

### Azure Account Setup
1. Press `Ctrl+Shift+P` (Windows/Linux) or `Cmd+Shift+P` (Mac)
2. Type "Azure: Sign In" and follow the authentication process
3. Select your subscription in the Azure extension

## 🚀 Deployment Methods

### Method 1: Container Apps Deployment (Recommended)

#### Step 1: Prepare Docker Image
1. Open the **Docker** extension panel (Docker icon in Activity Bar)
2. Right-click on your workspace folder
3. Select **"Docker: Initialize Docker files"**
4. Choose **"Python: Flask"** as the application type
5. Choose port **5000**

#### Step 2: Build Docker Image
1. Open Command Palette (`Ctrl+Shift+P`)
2. Type **"Docker Images: Build Image"**
3. Select the Dockerfile in your workspace
4. Tag your image (e.g., `pdf-parser:latest`)

#### Step 3: Deploy to Container Apps
1. Open the **Azure Container Apps** extension panel
2. Right-click on your subscription
3. Select **"Create Container App"**
4. Follow the wizard:
   - **Subscription**: Select your Azure subscription
   - **Resource Group**: Create new or select existing
   - **Container App Name**: `pdf-parser-app`
   - **Location**: Choose your preferred region (e.g., East US)
   - **Environment**: Create new managed environment
   - **Container Source**: Select **"Docker Hub or other registries"**
   - **Image**: Use your built image or `python:3.12-slim`
   - **Target Port**: `5000`

#### Step 4: Configure Environment Variables
1. In Azure Container Apps panel, find your deployed app
2. Right-click and select **"Edit in Portal"**
3. Add environment variables:
   - `SECRET_KEY`: Generate a secure key
   - `PORT`: `5000`

### Method 2: App Service Deployment (Web App)

#### Step 1: Create App Service
1. Open **Azure App Service** extension panel
2. Right-click on your subscription  
3. Select **"Create New Web App"**
4. Configure:
   - **App Name**: `pdf-parser-webapp` (must be globally unique)
   - **Resource Group**: Create new or select existing
   - **Location**: Choose your preferred region
   - **Pricing Tier**: Select **"Free (F1)"** for testing

#### Step 2: Deploy from VS Code
1. Right-click on your workspace folder in Explorer
2. Select **"Deploy to Web App"**
3. Choose the App Service you just created
4. Select **"Deploy"** to confirm

#### Step 3: Configure App Service
1. In Azure App Service panel, right-click your app
2. Select **"Open in Portal"**
3. Go to **Configuration** → **Application Settings**
4. Add:
   - `SECRET_KEY`: Your secure key
   - `SCM_DO_BUILD_DURING_DEPLOYMENT`: `true`
   - `WEBSITE_RUN_FROM_PACKAGE`: `1`

### Method 3: Docker Hub + Container Apps

#### Step 1: Push to Docker Hub
1. Build your image locally:
   ```bash
   docker build -t yourusername/pdf-parser:latest .
   ```
2. Push to Docker Hub:
   ```bash
   docker push yourusername/pdf-parser:latest
   ```

#### Step 2: Deploy from Docker Hub
1. In Azure Container Apps panel
2. Create new Container App
3. Select **"Docker Hub"** as source
4. Enter your image: `yourusername/pdf-parser:latest`

## 🔧 VS Code Command Palette Quick Actions

Press `Ctrl+Shift+P` and use these commands:

### Azure Container Apps
- `Azure Container Apps: Create Container App`
- `Azure Container Apps: Deploy Container App`
- `Azure Container Apps: View Container App Logs`
- `Azure Container Apps: Browse Container App`

### Azure App Service  
- `Azure App Service: Create New Web App`
- `Azure App Service: Deploy to Web App`
- `Azure App Service: Browse Web App`
- `Azure App Service: View Streaming Logs`

### Docker Operations
- `Docker Images: Build Image`
- `Docker Images: Push Image`
- `Docker Containers: Run`
- `Docker Compose: Up`

## 🎯 Step-by-Step Visual Guide

### Using Azure Container Apps Extension

1. **Open Azure Panel**
   - Click Azure icon in Activity Bar (left sidebar)
   - Expand "Container Apps" section

2. **Create Container App**
   - Right-click your subscription
   - Select "Create Container App"
   - Fill in the creation wizard

3. **Monitor Deployment**
   - Watch the output window for deployment progress
   - Check Azure panel for the new container app

4. **Test Application**
   - Right-click the deployed app
   - Select "Browse" to open in browser

### Using Azure App Service Extension

1. **Open Azure Panel**
   - Click Azure icon in Activity Bar
   - Expand "App Service" section

2. **Deploy Workspace**
   - Right-click workspace folder in Explorer
   - Select "Deploy to Web App"
   - Choose or create App Service

3. **Monitor Deployment**
   - Watch the deployment progress in Output window
   - Check for any errors or warnings

## 📊 Monitoring and Management

### View Logs
1. Right-click your deployed app in Azure panel
2. Select **"View Streaming Logs"**
3. Monitor real-time application logs

### Application Settings
1. Right-click app → **"Edit in Portal"**
2. Navigate to **Configuration**
3. Add/modify application settings

### Scaling
1. Open app in Azure Portal
2. Go to **"Scale up (App Service plan)"**
3. Choose appropriate pricing tier

## 🔍 Troubleshooting

### Common Issues

**1. Deployment Fails**
- Check Output window for detailed error messages
- Verify Azure subscription permissions
- Ensure Docker is running (for container deployments)

**2. App Won't Start**
- Check Application Settings in Azure Portal
- Verify environment variables are set correctly
- Review application logs for startup errors

**3. Port Issues**
- Ensure your app listens on the correct port (5000)
- Set PORT environment variable if needed
- Check ingress/networking configuration

### VS Code Debugging
1. Set breakpoints in your Python code
2. Use **"Docker: Run"** with debug configuration
3. Attach VS Code debugger to running container

## 📝 Best Practices

1. **Use Container Apps** for microservices and containerized applications
2. **Use App Service** for traditional web applications
3. **Set up monitoring** with Application Insights
4. **Use deployment slots** for staging environments
5. **Configure custom domains** for production
6. **Set up CI/CD** with GitHub Actions or Azure DevOps

## 🚀 Quick Deploy Commands

For fastest deployment, use these VS Code commands:

1. `Ctrl+Shift+P` → **"Azure Container Apps: Create Container App"**
2. Follow the wizard to deploy your PDF parser
3. `Ctrl+Shift+P` → **"Azure Container Apps: Browse Container App"** to test

Your PDF parser will be available at the generated Azure URL!
