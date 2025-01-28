# ServiceNow Environment Setup Guide

This guide provides instructions for setting up a ServiceNow environment for WorkArena in two scenarios:
1. Initial Setup (First-time setup)
2. Development Setup (Reactivating an existing instance)

## 1. Initial Setup

### Prerequisites
- ServiceNow Developer Account
- Python environment
- Terminal/Command Prompt

### A. Create ServiceNow Developer Instance

1. Visit [ServiceNow Developer Portal](https://developer.servicenow.com/) and create an account
2. Click on "Request an instance" and select the Washington release
   > Note: Instance initialization takes a few minutes

3. Once ready, locate your instance URL and credentials
   - If not visible, go to "Return to the Developer Portal" → "Manage instance password" → "Reset instance password"

4. Set up the following environment variables in your terminal:
   ```bash
   export SNOW_INSTANCE_URL="https://dev201251.service-now.com/"
   export SNOW_INSTANCE_UNAME="admin"
   export SNOW_INSTANCE_PWD="7tzYS@M1lZs-"
   ```

5. Log into your instance via browser using the admin credentials
   > Note: Close any popups that appear on the main screen (e.g., analytics agreement)

⚠️ **Warning**: While exploring the platform, please revert any UI changes (list views, pinned menus, etc.) as these persist and may affect benchmarking.

### B. Install and Initialize WorkArena

1. Install BrowserGym environment:
   ```bash
   pip install browsergym
   ```

2. Install Playwright:
   ```bash
   playwright install
   ```

3. Upload benchmark data:
   ```bash
   workarena-install
   ```

🎉 Initial setup is now complete!

## 2. Development Setup

For subsequent development sessions, follow these steps to reactivate your environment:

1. Wake up your ServiceNow instance:
   - Log into [ServiceNow Developer Portal](https://developer.servicenow.com/)
   - Access your instance through the portal
   > Note: Instance wake-up typically takes 2-3 minutes

2. Set environment variables in your terminal:
   ```bash
   export SNOW_INSTANCE_URL="https://dev201251.service-now.com/"
   export SNOW_INSTANCE_UNAME="admin"
   export SNOW_INSTANCE_PWD="7tzYS@M1lZs-"
   ```

3. Set up OpenAI API key:
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```

Your development environment is now ready to use! 🚀

## Troubleshooting

If you encounter any issues:
- Ensure all environment variables are correctly set
- Verify your instance is fully awake before attempting connections
- Check your internet connection
- Confirm your ServiceNow instance credentials are current
