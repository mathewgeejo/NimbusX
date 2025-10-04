# Deployment Guide

## 🚀 Deploying Your Application

### Option 1: Deploy Backend to Render

1. **Add Gunicorn to requirements.txt**
   ```bash
   cd backend
   echo gunicorn==21.2.0 >> requirements.txt
   ```

2. **Create Render Account**
   - Go to https://render.com
   - Sign up with GitHub

3. **Create New Web Service**
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Select the `backend` directory

4. **Configure Service**
   - **Name**: `will-it-rain-backend`
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Instance Type**: Free

5. **Add Environment Variables**
   - Go to "Environment" tab
   - Add: `GEMINI_API_KEY` = your_api_key

6. **Deploy**
   - Click "Create Web Service"
   - Wait for deployment (5-10 minutes)
   - Copy your backend URL (e.g., `https://will-it-rain-backend.onrender.com`)

### Option 2: Deploy Backend to Heroku

1. **Install Heroku CLI**
   ```bash
   # Download from: https://devcenter.heroku.com/articles/heroku-cli
   ```

2. **Login and Create App**
   ```bash
   heroku login
   cd backend
   heroku create will-it-rain-backend
   ```

3. **Add Gunicorn**
   ```bash
   echo "gunicorn==21.2.0" >> requirements.txt
   ```

4. **Create Procfile**
   ```bash
   echo "web: gunicorn app:app" > Procfile
   ```

5. **Set Environment Variables**
   ```bash
   heroku config:set GEMINI_API_KEY=your_api_key
   ```

6. **Deploy**
   ```bash
   git add .
   git commit -m "Prepare for Heroku deployment"
   git push heroku main
   ```

7. **Open Your App**
   ```bash
   heroku open
   ```

### Option 3: Deploy Frontend to Vercel

1. **Create Vercel Account**
   - Go to https://vercel.com
   - Sign up with GitHub

2. **Install Vercel CLI (Optional)**
   ```bash
   npm install -g vercel
   ```

3. **Deploy via Web Interface**
   - Click "Add New Project"
   - Import your GitHub repository
   - Select `frontend` directory
   - **Build Command**: `npm run build`
   - **Output Directory**: `build`
   - **Install Command**: `npm install`

4. **Add Environment Variable**
   - Go to "Settings" → "Environment Variables"
   - Add: `REACT_APP_API_URL` = your_backend_url
   - Example: `https://will-it-rain-backend.onrender.com`

5. **Deploy**
   - Click "Deploy"
   - Wait for build (2-5 minutes)
   - Your app is live!

**OR Deploy via CLI:**
```bash
cd frontend
vercel --prod
```

### Option 4: Deploy Frontend to Netlify

1. **Create Netlify Account**
   - Go to https://netlify.com
   - Sign up with GitHub

2. **Deploy via Web Interface**
   - Click "Add new site" → "Import an existing project"
   - Choose GitHub and authorize
   - Select your repository
   - **Base directory**: `frontend`
   - **Build command**: `npm run build`
   - **Publish directory**: `frontend/build`

3. **Add Environment Variables**
   - Go to "Site settings" → "Environment variables"
   - Add: `REACT_APP_API_URL` = your_backend_url

4. **Deploy**
   - Click "Deploy site"
   - Wait for build completion
   - Your site is live!

**OR Deploy via CLI:**
```bash
npm install -g netlify-cli
cd frontend
netlify deploy --prod
```

## 🔧 Production Configuration

### Backend Production Settings

Update `app.py` for production:
```python
import os

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)
```

### Frontend Production Settings

Update `.env.production`:
```env
REACT_APP_API_URL=https://your-actual-backend-url.com
```

### CORS Configuration

Make sure your backend allows your frontend domain:
```python
# In app.py
CORS(app, origins=[
    "http://localhost:3000",
    "https://your-frontend-domain.vercel.app",
    "https://your-frontend-domain.netlify.app"
])
```

## 🔒 Security Checklist

- [ ] Never commit `.env` files
- [ ] Use environment variables for all secrets
- [ ] Enable HTTPS (automatic on Vercel/Netlify/Render)
- [ ] Set proper CORS origins
- [ ] Rotate API keys periodically
- [ ] Monitor API usage limits
- [ ] Enable rate limiting if needed

## 📊 Monitoring

### Backend Monitoring
- Render: Built-in logs and metrics
- Heroku: `heroku logs --tail`

### Frontend Monitoring
- Vercel: Built-in analytics
- Netlify: Analytics dashboard

### API Usage
- Monitor Gemini API usage at https://makersuite.google.com
- NASA POWER API has no authentication (unlimited)

## 🎯 Performance Tips

1. **Backend**
   - Add caching for NASA API responses
   - Use connection pooling
   - Implement rate limiting

2. **Frontend**
   - Enable code splitting
   - Optimize images
   - Use lazy loading
   - Enable service workers for offline support

## 🔄 CI/CD Setup

### GitHub Actions (Auto-deploy)

Create `.github/workflows/deploy.yml`:
```yaml
name: Deploy

on:
  push:
    branches: [ main ]

jobs:
  deploy-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy to Render
        # Add Render deploy hook URL in GitHub Secrets
        run: curl ${{ secrets.RENDER_DEPLOY_HOOK }}

  deploy-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy to Vercel
        uses: amondnet/vercel-action@v20
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.ORG_ID }}
          vercel-project-id: ${{ secrets.PROJECT_ID }}
```

## 🌐 Custom Domain (Optional)

### Vercel
1. Go to "Settings" → "Domains"
2. Add your custom domain
3. Update DNS records as instructed

### Netlify
1. Go to "Domain settings"
2. Add custom domain
3. Follow DNS configuration steps

### Render
1. Go to "Settings" → "Custom Domains"
2. Add your domain
3. Configure DNS

## 📱 Mobile Optimization

The app is already responsive, but for best mobile experience:

1. **Test on real devices**
2. **Enable PWA features** (add manifest.json)
3. **Optimize touch targets**
4. **Test on slow 3G**

## 🆘 Troubleshooting Deployment

### Backend Won't Start
- Check logs for errors
- Verify all dependencies in requirements.txt
- Ensure PORT environment variable is used
- Check GEMINI_API_KEY is set

### Frontend Build Fails
- Check Node.js version (use 16+)
- Verify all dependencies in package.json
- Check for TypeScript errors
- Ensure REACT_APP_API_URL is set

### CORS Errors
- Add frontend URL to CORS allowed origins
- Check protocol (http vs https)
- Verify API URL in frontend .env

### API Key Issues
- Verify Gemini API key is valid
- Check key has not expired
- Ensure key is properly set in environment variables

## 📦 Backup & Recovery

1. **Database** (if you add one later)
   - Regular automated backups
   - Test restore procedures

2. **Environment Variables**
   - Keep encrypted backup of .env
   - Document all variables

3. **Code**
   - Use Git for version control
   - Tag releases
   - Maintain changelog

---

**Your app is now ready for production! 🎉**

Need help? Check the logs first, then consult:
- Render docs: https://render.com/docs
- Vercel docs: https://vercel.com/docs
- Heroku docs: https://devcenter.heroku.com
