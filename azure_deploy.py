#!/usr/bin/env python3
"""
Azure deployment script for the PDF Parser application
"""
import os
import subprocess
import json
import secrets
from datetime import datetime

try:
    # Check if user is logged in to Azure
    print("Checking if you're logged in to Azure...")
    result = subprocess.run(
        ['az', 'account', 'show'], 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE, 
        text=True
    )
    
    if result.returncode != 0:
        print("You need to log in to Azure first.")
        subprocess.run(['az', 'login'], check=True)
    else:
        print("Already logged in to Azure.")
        account_info = json.loads(result.stdout)
        print(f"Using subscription: {account_info['name']} ({account_info['id']})")

    # Get subscription list
    print("\nAvailable Azure subscriptions:")
    subprocess.run(['az', 'account', 'list', '--output', 'table'], check=True)
    
    # Ask for subscription ID
    subscription_id = input("\nEnter the subscription ID to use (press Enter to use current): ")
    if subscription_id:
        print(f"Setting subscription to: {subscription_id}")
        subprocess.run(['az', 'account', 'set', '--subscription', subscription_id], check=True)
    
    # Generate unique suffix for resources
    timestamp = datetime.now().strftime("%Y%m%d%H%M")
    rand_suffix = secrets.token_hex(3)
    unique_suffix = f"{timestamp}-{rand_suffix}"
    
    # Ask for resource names
    print("\nEnter names for Azure resources (press Enter for defaults):")
    resource_group = input(f"Resource group name [pdfparser-rg-{unique_suffix}]: ") or f"pdfparser-rg-{unique_suffix}"
    location = input("Azure region [eastus]: ") or "eastus"
    app_service_plan = input(f"App Service plan name [pdfparser-plan-{unique_suffix}]: ") or f"pdfparser-plan-{unique_suffix}"
    web_app_name = input(f"Web App name [pdfparser-{unique_suffix}]: ") or f"pdfparser-{unique_suffix}"
    
    # Create resource group
    print(f"\nCreating resource group: {resource_group} in {location}")
    subprocess.run([
        'az', 'group', 'create',
        '--name', resource_group,
        '--location', location
    ], check=True)
    
    # Create App Service plan
    print(f"\nCreating App Service plan: {app_service_plan}")
    subprocess.run([
        'az', 'appservice', 'plan', 'create',
        '--name', app_service_plan,
        '--resource-group', resource_group,
        '--sku', 'B1',
        '--is-linux'
    ], check=True)
    
    # Create Web App
    print(f"\nCreating Web App: {web_app_name}")
    subprocess.run([
        'az', 'webapp', 'create',
        '--resource-group', resource_group,
        '--plan', app_service_plan,
        '--name', web_app_name,
        '--runtime', 'PYTHON|3.10'
    ], check=True)
    
    # Configure Web App settings
    print("\nConfiguring Web App settings")
    
    # Generate a random secret key
    secret_key = secrets.token_hex(24)
    
    subprocess.run([
        'az', 'webapp', 'config', 'set',
        '--resource-group', resource_group,
        '--name', web_app_name,
        '--startup-file', 'gunicorn --bind=0.0.0.0 --timeout 600 app:app'
    ], check=True)
    
    subprocess.run([
        'az', 'webapp', 'config', 'appsettings', 'set',
        '--resource-group', resource_group,
        '--name', web_app_name,
        '--settings', f'SECRET_KEY={secret_key}'
    ], check=True)
    
    # Configure local Git deployment
    print("\nSetting up local Git deployment")
    
    deployment_result = subprocess.run([
        'az', 'webapp', 'deployment', 'source', 'config-local-git',
        '--name', web_app_name,
        '--resource-group', resource_group,
        '--output', 'tsv'
    ], check=True, stdout=subprocess.PIPE, text=True)
    
    git_url = deployment_result.stdout.strip()
    
    # Create deployment user if needed
    try:
        username = input("\nEnter a username for deployment: ")
        password = input("Enter a password for deployment: ")
        
        subprocess.run([
            'az', 'webapp', 'deployment', 'user', 'set',
            '--user-name', username,
            '--password', password
        ], check=True)
    except:
        print("Warning: Couldn't set deployment user. You may need to set it in the Azure Portal.")
    
    # Print deployment instructions
    print("\n===========================================================")
    print(f"PDF Parser application setup complete!")
    print("===========================================================")
    print(f"Web App URL: https://{web_app_name}.azurewebsites.net")
    print(f"Git deployment URL: {git_url}")
    print("\nTo deploy your code, run:")
    print(f"git remote add azure {git_url}")
    print("git push azure main")
    print("===========================================================")
    
    # Ask if user wants to deploy now
    deploy_now = input("\nDeploy the application now? (y/n): ")
    if deploy_now.lower() == 'y':
        print("\nAdding Azure git remote...")
        subprocess.run(['git', 'remote', 'add', 'azure', git_url], check=True)
        
        print("\nPushing code to Azure...")
        subprocess.run(['git', 'push', 'azure', 'main'], check=True)
        
        print(f"\nDeployment complete! Your app should be available at: https://{web_app_name}.azurewebsites.net")
        print("Note: It may take a few minutes for the app to be fully deployed and started.")

except Exception as e:
    print(f"Error: {str(e)}")
    print("\nManual deployment instructions:")
    print("1. Log in to the Azure Portal: https://portal.azure.com")
    print("2. Create a new Web App with Python 3.10 on Linux")
    print("3. Configure the startup command: gunicorn --bind=0.0.0.0 --timeout 600 app:app")
    print("4. Set up deployment via GitHub or local Git")
    print("5. Push your code to the deployment source")
