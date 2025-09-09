# WhatsApp Business API Webhook Setup Guide

## 🚀 Your Railway App Details
- **Webhook URL**: `https://web-production-e9648.up.railway.app/webhook`
- **App Status**: ✅ Working (5 courses, 11 FAQs loaded)
- **Version**: v0.2.0 (commit: 080780b)

## 📋 Step-by-Step Webhook Configuration

### Step 1: Access Meta for Developers
1. Go to https://developers.facebook.com/
2. Navigate to your WhatsApp Business App
3. Go to **WhatsApp > Configuration** in the left sidebar

### Step 2: Configure Webhook
1. Click **"Edit"** next to Webhook
2. Enter these details:
   - **Callback URL**: `https://web-production-e9648.up.railway.app/webhook`
   - **Verify Token**: Use your `VERIFY_TOKEN` from Railway env vars
   - **Webhook Fields**: Select `messages`

### Step 3: Railway Environment Variables Check
Make sure these are set in Railway dashboard:

```bash
WHATSAPP_TOKEN=your_temporary_token_here
PHONE_NUMBER_ID=your_phone_number_id_here  
VERIFY_TOKEN=your_verify_token_here
GROQ_API_KEY=your_groq_api_key_here
DATABASE_URL=${{MySQL.MYSQL_URL}}  # Already set
```

### Step 4: Test Webhook Verification
Meta will send a GET request to verify your webhook. Your app should respond correctly.

### Step 5: Subscribe to Webhook
After verification, click **"Subscribe"** to start receiving messages.

---

## 🧪 Testing Commands

### Test Webhook Verification (Local Simulation)
```bash
# Test with your actual verify token
curl "https://web-production-e9648.up.railway.app/webhook?hub.mode=subscribe&hub.verify_token=YOUR_VERIFY_TOKEN&hub.challenge=test123"
```

### Test Bot Responses
Send these messages to your WhatsApp number:
- "What courses do you offer?"
- "How much does Python course cost?"
- "What are your office hours?"
- "hello"

---

## 🔧 Troubleshooting

### If Webhook Verification Fails:
1. Check Railway logs for errors
2. Verify `VERIFY_TOKEN` matches exactly
3. Ensure app is responding to GET requests

### If Messages Not Received:
1. Check webhook subscription status
2. Verify `PHONE_NUMBER_ID` is correct
3. Check Railway app logs

### If Responses Not Sent:
1. Verify `WHATSAPP_TOKEN` is valid
2. Check token permissions include `messages` scope
3. Monitor Railway logs for API errors

---

## 📱 Production Checklist

- [ ] Webhook URL configured in Meta dashboard
- [ ] Webhook verification successful  
- [ ] Environment variables set in Railway
- [ ] Test message sent and received
- [ ] Bot responds with course information
- [ ] Database queries working (5 courses, 11 FAQs)

---

## 🎯 Next Phase: Going Live

After webhook setup works:
1. **Replace temporary token** with permanent one
2. **Add phone number verification** 
3. **Set up business verification** (for production limits)
4. **Configure message templates** (optional)
5. **Monitor and optimize responses**

---

## 🔗 Quick Links

- **Railway App**: https://web-production-e9648.up.railway.app/
- **Health Check**: https://web-production-e9648.up.railway.app/health
- **Meta Dashboard**: https://developers.facebook.com/
- **WhatsApp Business API Docs**: https://developers.facebook.com/docs/whatsapp
