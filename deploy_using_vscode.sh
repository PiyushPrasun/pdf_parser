#!/bin/bash

echo "========================================================"
echo "PDF Parser Azure Deployment through VS Code"
echo "========================================================"
echo "Follow these steps to deploy through VS Code:"
echo ""
echo "1. Click on the Azure icon in the VS Code sidebar"
echo "2. Expand the APP SERVICE section"
echo "3. Right-click on your subscription and select 'Create new Web App...'"
echo "4. Follow the prompts to:"
echo "   - Enter a globally unique name for the web app"
echo "   - Select Python 3.10"
echo "   - Create a new resource group or select an existing one"
echo "   - Create a new App Service Plan or select an existing one"
echo "   - Choose the Basic B1 (or higher) pricing tier"
echo ""
echo "5. Once the web app is created, right-click on it and select 'Deploy to Web App...'"
echo "6. Select the current workspace folder when prompted"
echo "7. Confirm the deployment"
echo ""
echo "8. After deployment completes, you need to configure these settings in the Azure Portal:"
echo "   - Go to Configuration > General Settings"
echo "   - Set the Startup Command to: gunicorn --bind=0.0.0.0 --timeout 600 app:app"
echo "   - Go to Configuration > Application Settings"
echo "   - Add a setting named SECRET_KEY with a random value"
echo ""
echo "9. Your app should be available at: https://your-app-name.azurewebsites.net"
echo "========================================================"
echo ""
echo "Would you like me to try to open the Azure App Service panel in VS Code? (y/n)"
read response

if [[ "$response" == "y" ]]; then
    code --command workbench.view.extension.azure
    echo "Azure panel should now be open. Look for the App Service section."
fi
