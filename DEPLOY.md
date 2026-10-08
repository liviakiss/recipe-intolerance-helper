# Deploying

The whole thing runs free, and none of the three services asks for a card.

| Part | Service | What it hosts |
|---|---|---|
| Database | [Neon](https://neon.com) | PostgreSQL |
| Backend | [Render](https://render.com) | The FastAPI app in Docker (with Tesseract) |
| Frontend | [Vercel](https://vercel.com) | The Next.js app, and forwards `/api/...` to the backend |

Sign up for all three with "Continue with GitHub". Free-tier terms change, so check each pricing page when you sign up.

## 1. Database (Neon)

1. Create a project. Pick the region closest to you (Frankfurt for the Netherlands).
2. Click **Connect**. Turn **Connection pooling off** and copy the connection string. It looks like:
   `postgresql://user:password@ep-something.eu-central-1.aws.neon.tech/neondb?sslmode=require`
3. Keep it private. It contains the password. Never put it in a file that gets committed.

## 2. Create the tables and load the dictionary

From the `backend` folder, with the virtual environment active. Setting the variable in the terminal overrides your local `.env` for this window only.

```powershell
cd D:\Code\recipe-intolerance-helper\backend
.\venv\Scripts\Activate.ps1
$env:DATABASE_URL = "postgresql://...paste the Neon string here..."
$env:SECRET_KEY = "only-needed-to-run-these-commands"
alembic upgrade head
python seed.py
```

`seed.py` prints how many tags, presets, ingredients and substitutes it added (619 ingredients). Then close that terminal window, so you can't run anything against Neon by accident later.

## 3. Backend (Render)

1. **New** → **Web Service** → connect the GitHub repository.
2. Settings:
   - **Language:** Docker
   - **Root Directory:** `backend`
   - **Region:** same as the database
   - **Instance type:** Free
   - **Health Check Path:** `/`
3. Environment variables:

| Name | Value |
|---|---|
| `DATABASE_URL` | the Neon string from step 1 |
| `SECRET_KEY` | a long random string: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `COOKIE_SECURE` | `true` |
| `CORS_ORIGINS` | your Vercel address (add it in step 5; for now put `http://localhost:3000`) |

4. Deploy. The first build takes a few minutes. In the logs, look for `Application startup complete`.
5. Open `https://<your-service>.onrender.com/ingredient-tags`. You should see the list of tags as JSON.

## 4. Frontend (Vercel)

1. **Add New** → **Project** → import the same repository.
2. **Root Directory:** `frontend`. The framework is detected as Next.js.
3. Environment variables (set them *before* the first deploy, because `NEXT_PUBLIC_` values are baked in at build time):

| Name | Value |
|---|---|
| `NEXT_PUBLIC_API_URL` | `/api` |
| `BACKEND_URL` | `https://<your-service>.onrender.com` (no trailing slash needed) |

4. Deploy, then copy the address Vercel gives you.

## 5. Tell the backend where the frontend lives

In Render, change `CORS_ORIGINS` to the Vercel address (`https://<your-app>.vercel.app`, no trailing slash). Render redeploys by itself.

## 6. Check it

Open the Vercel address. The first load may show "The demo server is waking up" for up to a minute. Then:

- the restriction buttons appear
- paste a recipe and check it
- register, log in, reload the page (you should stay logged in), save a recipe
- upload a photo of a recipe

## 7. Keep it awake (optional, recommended for job hunting)

Render's free service sleeps after 15 minutes without traffic, and a recruiter will only click once. A free pinger fixes that: on [cron-job.org](https://cron-job.org) create a job that opens `https://<your-service>.onrender.com/` every 10 minutes. Use `/`, which doesn't touch the database, so Neon can still sleep.

One always-awake service uses about 744 of the 750 free instance-hours in a month, so don't run a second free service on the same Render account.

## 8. Add the link

Put the Vercel address at the top of the README, and in the repository's **About** gear → **Website**. While you're there, remove the `practice-project` topic.

## If something goes wrong

- **Page loads but no restriction buttons:** open `https://<your-service>.onrender.com/ingredient-tags`. If that fails, read the Render logs. A wrong `DATABASE_URL` or a missing `SECRET_KEY` stops the server at startup, with a message saying which.
- **Logs show a database error on start:** the Neon string needs `?sslmode=require` at the end.
- **Login works but you are logged out on reload:** `COOKIE_SECURE` must be `true`, and `NEXT_PUBLIC_API_URL` must be `/api` (redeploy Vercel after changing it).
- **Photo scan fails on large photos:** the free server has 512 MB of memory. The browser already shrinks big photos before sending; if Render logs say it ran out of memory, try a smaller photo or a paid instance.
- **Error 429:** a rate limit was hit. The message says how long to wait.

## Good to know

- Vercel's free Hobby plan is for personal, non-commercial use, which fits a portfolio. A project meant to earn money needs a different plan or host.
- Photos are processed in memory and never stored.
- To change a limit, edit the `RateLimiter(...)` lines near the top of `backend/app/main.py`.
