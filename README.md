# 🤖 WhatsApp EdTech Bot - Railway Deployment

A WhatsApp chatbot for EdTech platform using Meta's official WhatsApp Business API, optimized for Railway deployment.

## ⭐ Features

- 📚 Course information and search
- ❓ FAQ system with intelligent matching
- 🤖 AI-powered responses via Groq
- 🗄️ MySQL database integration
- 🔐 Webhook signature verification
- 🚀 Railway cloud deployment ready

## 🚀 Quick Railway Deployment

### Step 1: Prepare Repository

1. **Push to GitHub:**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin <your-github-repo-url>
   git push -u origin main
   ```

### Step 2: Deploy to Railway

1. **Create Railway Project:**
   - Go to [Railway](https://railway.app/)
   - Click "Deploy from GitHub repo"
   - Select this repository
   - Railway will auto-detect Python and use the Procfile

2. **Add MySQL Database:**
   - In Railway dashboard: "Add service" → "Database" → "MySQL"
   - Railway will auto-generate connection details

3. **Configure Environment Variables:**
   
   In Railway dashboard → Your web service → "Variables":
   
   ```bash
   # Required WhatsApp API
   WHATSAPP_TOKEN=your_temporary_access_token
   PHONE_NUMBER_ID=your_phone_number_id  
   VERIFY_TOKEN=your_custom_verify_token
   
   # Optional (recommended)
   APP_SECRET=your_app_secret
   GROQ_API_KEY=your_groq_api_key
   
   # Database (auto-set by Railway MySQL service)
   DATABASE_URL=mysql://user:pass@host:port/dbname
   ```

4. **Deploy & Get URL:**
   - Railway auto-deploys on variable changes
   - Copy the public URL (e.g., `https://yourapp.up.railway.app`)

### Step 3: Seed Database

**Option A: Railway MySQL Console**
1. Open MySQL service → "Connect" → Use built-in SQL editor
2. Run the seed script manually or use Railway's shell

**Option B: Remote Connection**
1. Get connection details from Railway MySQL service
2. Run locally: `python seed_database.py`

### Step 4: Configure Meta Webhook

1. **In Meta Developer Console:**
   - Webhook URL: `https://yourapp.up.railway.app/webhook`
   - Verify Token: (exact match to VERIFY_TOKEN)
   - Subscribe to: `messages`

2. **Test:**
   - Send message from your linked WhatsApp
   - Check Railway logs for activity
   - Verify auto-reply

## 📁 Project Structure

```
whatsapp-bot-railway/
├── app.py                 # Main Flask application
├── Procfile              # Railway/Heroku deployment config
├── requirements.txt      # Python dependencies  
├── runtime.txt           # Python version specification
├── seed_database.py      # Database seeding script
├── .env.example         # Environment variables template
├── .gitignore           # Git ignore rules
└── README.md            # This file
```

## 🛠️ Local Development

1. **Setup:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your values
   ```

3. **Database:**
   ```bash
   # Start local MySQL or use Railway DATABASE_URL
   python seed_database.py
   ```

4. **Run:**
   ```bash
   python app.py
   # Or with gunicorn: gunicorn app:app --bind 0.0.0.0:5000
   ```

## 🔍 API Endpoints

- `GET /` - Service status
- `GET /health` - Health check with database status  
- `GET /webhook` - Meta webhook verification
- `POST /webhook` - Receive WhatsApp messages
- `POST /test` - Test message processing

## 📊 Database Schema

**Courses Table:**
- `id`, `title`, `description`, `price`, `duration`, `instructor`, `is_active`

**FAQs Table:**  
- `id`, `question`, `answer`, `keywords`, `course_id`, `is_active`

## ⚙️ Configuration

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `WHATSAPP_TOKEN` | Meta temporary access token | `EAAxxxxx...` |
| `PHONE_NUMBER_ID` | Meta phone number ID | `123456789` |
| `VERIFY_TOKEN` | Custom webhook verification token | `my_secure_token_123` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_SECRET` | Meta app secret for signature verification | `None` |
| `GROQ_API_KEY` | Groq AI API key | `None` |
| `DATABASE_URL` | Full database connection URL | Auto-detected |
| `API_VERSION` | Meta API version | `v18.0` |

## 🐛 Troubleshooting

**Webhook Verification Fails:**
- Ensure VERIFY_TOKEN matches exactly
- Check Railway logs for verification attempts
- Test URL accessibility: `curl https://yourapp.up.railway.app/health`

**Database Connection Issues:**
- Verify DATABASE_URL is set correctly
- Check Railway MySQL service is running
- Test connection: visit `/health` endpoint

**Messages Not Processing:**
- Check Railway logs for errors
- Verify webhook subscription in Meta console
- Test with `/test` endpoint first

**AI Responses Not Working:**
- Set GROQ_API_KEY in Railway variables
- Check Groq API quotas and billing

## 💰 Cost Optimization

**Railway Free Tier Tips:**
- Use 1 worker: `web: gunicorn app:app --workers 1`
- Monitor usage in Railway dashboard
- Consider PlanetScale for database if needed

**Alternative Hosting:**
- Render: Similar deployment, different pricing
- Heroku: No free tier, but stable
- Fly.io: Global deployment, volume persistence

## 📚 Next Steps

1. **Get Production Tokens:** Convert temporary WhatsApp token to permanent
2. **Add Features:** Group chat support, media handling, payment integration
3. **Monitoring:** Add logging service (LogTail, Papertrail)
4. **Scaling:** Implement Redis for session management
5. **Security:** Add rate limiting, input validation

## 📞 Support

- Check Railway logs for detailed error information
- Test endpoints: `/health`, `/test`
- Verify Meta webhook configuration
- Ensure all environment variables are set

---

**Made with ❤️ for EdTech learning platforms**
