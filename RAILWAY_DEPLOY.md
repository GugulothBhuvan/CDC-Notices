# Railway.app Deployment Guide

## Quick Setup

1. **Sign up/Login to Railway:**
   - Go to https://railway.app
   - Sign up with GitHub

2. **Create New Project:**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository: `GugulothBhuvan/CDC-Notices`

3. **Set Environment Variables:**
   - Go to your project → Variables tab
   - Add these variables:
     ```
     ERP_COOKIE=your_cookie_string_here
     EMAIL_USER=youremail@gmail.com
     EMAIL_PASS=your_app_password
     GOOGLE_GROUP_EMAIL=your-group@googlegroups.com
     POLL_INTERVAL=300
     SMTP_HOST=smtp.gmail.com
     SMTP_PORT=587
     ```

4. **Deploy:**
   - Railway will automatically detect the `Procfile`
   - It will run `python monitor_notices.py` as a worker
   - The service will start automatically

5. **Monitor Logs:**
   - Go to your project → Deployments
   - Click on the deployment → View logs
   - You should see the monitor starting up

## Important Notes

- **Worker Process:** This runs as a worker (not a web service), so it will run continuously
- **Restart Policy:** Configured to restart on failure (up to 10 times)
- **Environment Variables:** Make sure all required variables are set in Railway dashboard
- **Logs:** Check logs regularly to ensure it's working

## Troubleshooting

### Service Keeps Restarting

- Check logs for errors
- Verify all environment variables are set correctly
- Check if cookie is expired (update `ERP_COOKIE`)

### No Emails Being Sent

- Verify `EMAIL_PASS` is a Gmail App Password (not regular password)
- Check `GOOGLE_GROUP_EMAIL` is correct
- Verify Google Group allows external senders

### Service Not Starting

- Check Railway logs
- Verify `Procfile` is in the root directory
- Ensure `monitor_notices.py` exists

## Updating Cookie

1. Re-login to ERP
2. Copy fresh cookie
3. Go to Railway → Variables
4. Update `ERP_COOKIE` value
5. Service will automatically restart

## Cost

- Railway free tier: $5 credit/month
- Worker processes: ~$0.01/hour
- Should run for ~500 hours/month on free tier

## Alternative: Use Railway's Cron Jobs

If you want to run it on a schedule instead of continuously:

1. Remove `Procfile`
2. Use Railway's Cron feature
3. Set schedule: `*/5 * * * *` (every 5 minutes)
4. Command: `python monitor_notices.py`

But continuous worker is recommended for real-time monitoring.

