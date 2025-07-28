# 📝 GoalContract

**GoalContract** is a system that helps you commit to a goal, lock in your habits, and receive daily reminders — like a digital contract between you and your better self.

Built in 72 hours for the [Boot.dev Hackathon](https://boot.dev), GoalContract combines FastAPI + Alpine.js + OpenAI + Vercel + Railway for a full-stack accountability system.


## Features

- 🧠 AI-generated motivational messages (morning, midday, night)
- 📆 Smart goal + habit configuration (fixed or recurring goals)
- 📲 Daily SMS and/or email reminders
- 💬 Personalized tone, trigger habits, and accountability buddy
- ⚡ Fully serverless deploy: Vercel frontend + Railway backend


## 🚀 Live Demo

Visit https://goalcontract.vercel.app and enter an email / and or phone number to receieve messages!

**Frontend**: [https://goalcontract.vercel.app](https://goalcontract.vercel.app)  
**Backend**: [https://goalcontract-production.up.railway.app](https://goalcontract-production.up.railway.app)

Use the frontend form to generate your contract. The AI will handle the rest.

---

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, Resend (email), OpenAI
- **Frontend**: Alpine.js, HTML, CSS
- **Deployment**: Vercel (frontend) + Railway (backend)
- **Storage**: PostgreSQL (Railway)

---

## Setup (Local Dev)

```bash
git clone https://github.com/your-username/goalcontract.git
cd goalcontract
pip install -r requirements.txt

# In one terminal
uvicorn app.main:app --reload

# In another terminal, open frontend/index.html in browser
