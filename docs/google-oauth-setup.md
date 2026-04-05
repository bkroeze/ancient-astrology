# Google OAuth Setup Guide

This guide walks you through setting up Google OAuth for Ancient Astrology.

## Prerequisites

- A Google Cloud account
- Access to the [Google Cloud Console](https://console.cloud.google.com/)

## Step 1: Create a New Project (or select existing)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" dropdown in the top bar
3. Click "New Project"
4. Enter a project name (e.g., "Ancient Astrology")
5. Click "Create"

## Step 2: Configure OAuth Consent Screen

1. In the sidebar, go to "APIs & Services" > "OAuth consent screen"
2. Select "External" and click "Create"
3. Fill in the required fields:
   - App name: Ancient Astrology
   - User support email: your email
   - Developer contact information: your email
4. Click "Save and Continue"
5. On Scopes page, click "Add or Remove Scopes":
   - Select: `../auth/userinfo.email`
   - Select: `../auth/userinfo.profile`
6. Click "Save and Continue"
7. Add test users (optional, for development)
8. Click "Save and Continue"

## Step 3: Create OAuth 2.0 Credentials

1. In the sidebar, go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. Application type: "Web application"
4. Name: "Ancient Astrology Web Client"
5. **Authorized JavaScript origins:**
   - `http://localhost:8000` (for development)
   - `https://your-production-domain.com` (for production)
6. **Authorized redirect URIs:**
   - `http://localhost:8000/accounts/google/login/callback/` (development)
   - `https://your-production-domain.com/accounts/google/login/callback/` (production)
7. Click "Create"
8. Copy the **Client ID** and **Client Secret** values

## Step 4: Configure Environment Variables

Create or update your `.env` file with:

```bash
# Google OAuth credentials
GOOGLE_OAUTH_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret
```

**Important:** For django-allauth, you need to create a JSON file with the OAuth credentials:

```bash
# Create credentials directory
mkdir -p credentials

# Create the JSON file (one method)
echo '{"web": {"client_id": "your-client-id.apps.googleusercontent.com", "client_secret": "your-client-secret", "auth_uri": "https://accounts.google.com/o/oauth2/auth", "token_uri": "https://oauth2.googleapis.com/token", "redirect_uris": ["http://localhost:8000/accounts/google/login/callback/"]}}' > credentials/google_client_secret.json

# Then in settings.py, use:
# GOOGLE_OAUTH_CLIENT_SECRET_FILE=credentials/google_client_secret.json
```

## Step 5: Set Up Social Account in Django Admin

1. Run migrations: `python manage.py migrate`
2. Start the development server: `python manage.py runserver`
3. Go to Admin panel: `http://localhost:8000/admin/`
4. Navigate to "Social Accounts" > "Social applications"
5. Click "Add social application"
6. Select provider: "Google"
7. Enter name: "Google"
8. Paste the Client ID and Secret Key
9. In "Sites", select both sites (or just the appropriate one)
10. Click "Save"

## Verification

After setup:

1. Go to `http://localhost:8000/accounts/login/`
2. You should see "Sign in with Google" button
3. Click it and complete the OAuth flow
4. Check the admin panel to see the created social account

## Troubleshooting

### Redirect URI Mismatch Error

- Ensure the redirect URI in Google Console exactly matches: `http://localhost:8000/accounts/google/login/callback/`
- The trailing slash matters!
- For HTTPS in production, make sure to use HTTPS URI

### "Not a valid origin" Error

- Add your domain to "Authorized JavaScript origins"
- For localhost, use `http://localhost:8000` (not just `http://localhost`)

### User Already Exists Error

- If a user with the same email already exists, they can't link a Google account via social login
- Use SOCIALACCOUNT_EMAIL_REQUIRED = True in settings to prevent this
- Or merge accounts through the admin interface

### Email Not Received / Not Verified

- Set `ACCOUNT_EMAIL_REQUIRED = True` and `ACCOUNT_EMAIL_VERIFICATION = 'mandatory'`
- In development, emails are printed to console

## Production Checklist

1. ✅ Use HTTPS (required by Google)
2. ✅ Update ALLOWED_HOSTS in settings
3. ✅ Set DEBUG=False
4. ✅ Update redirect URIs in Google Console with production URLs
5. ✅ Consider publishing your OAuth app (for external users)

## Security Notes

- Never commit credentials to version control
- Use environment variables or secure credential storage
- Rotate secrets periodically
- Monitor the Google Cloud Console for unusual activity
