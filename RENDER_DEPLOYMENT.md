# LifeGPT Render Deployment Guide

## Prerequisites
- GitHub repository with code pushed
- Render free account (https://render.com)
- Azure OpenAI credentials

## Deployment Steps

1. **Connect to Render:**
   - Go to https://render.com
   - Create a new account or sign in
   - Connect your GitHub repository

2. **Create Web Service:**
   - Click "New +" → "Web Service"
   - Select your GitHub repository
   - Name: `lifegpt`
   - Region: Oregon (or your preference)
   - Plan: FREE

3. **Environment Variables:**
   - Add the following to Render's Environment tab:
     - `AZURE_OPENAI_API_KEY` = your Azure OpenAI key
     - `AZURE_OPENAI_ENDPOINT` = your Azure endpoint
     - `AZURE_OPENAI_DEPLOYMENT_NAME` = gpt-4o
     - `AZURE_OPENAI_API_VERSION` = 2024-02-01

4. **Deploy:**
   - Render will automatically detect `Procfile`
   - Build and deployment will start
   - Service will be available at `https://lifegpt.onrender.com`

## Notes for Free Tier

- **Cold starts:** Free tier services go to sleep after 15 minutes of inactivity
- **Speed:** First request after sleep will take 30+ seconds to wake up
- **Resources:** Limited to 512MB RAM
- **Storage:** Temporary file uploads will be cleaned up
- **Timeout:** 30 second request timeout

## Limitations & Workarounds

### Large PDF Processing
- For very large PDFs on free tier, consider:
  - Splitting documents into smaller pages
  - Using lower DPI settings in translation
  - Optimizing batch sizes

### Model Loading
- NLLB-200 model (~2GB) may struggle on 512MB free tier
- Consider fallback to Azure OpenAI for translations if model loading fails

## Monitoring

- Check logs in Render dashboard
- Monitor dyno metrics for memory/CPU usage
- Free tier services may restart daily

## Upgrade Options

If free tier isn't sufficient:
- **Paid tier:** $12.50/month for starter plan with more resources
- **Alternative:** Use Hugging Face Spaces for model serving + separate FastAPI instance
