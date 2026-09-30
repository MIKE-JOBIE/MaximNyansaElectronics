# Maxim Nyansa Electronics — Web Portal

Official web portal for **Maxim Nyansa Electronics SL** — vocational training, electronics repair, youth enterprise development, and community impact in Sierra Leone.

## Features

- 🎓 **Training portal** — programs, applications, online venue
- 🛒 **Electronics shop** — cart, checkout, order history
- 📚 **E-Library** — learning resources, video testimonials
- 💚 **Donor portal** — pledge form, impact page
- ⚙️ **Admin CMS** — programs, products, orders, applicants, news, videos
- 💳 **Paystack payments** — orders and donations (optional)
- ☁️ **Cloudinary uploads** — persistent media (optional)

## Tech Stack

- **Backend:** Flask 3.0, SQLAlchemy, Flask-Login, Flask-Migrate
- **Database:** PostgreSQL (production) / SQLite (local dev)
- **Frontend:** Jinja2, custom CSS (no framework bloat)
- **Payments:** Paystack
- **Media:** Cloudinary (optional)
- **Deployment:** Render, Koyeb, Hugging Face Spaces, PythonAnywhere

## Local Development

```bash
# Clone
git clone https://github.com/YOUR-USERNAME/MaximNyansaElectronics.git
cd MaximNyansaElectronics

# Setup
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

pip install -r requirements.txt

# Configure
copy .env.example .env         # Windows
# cp .env.example .env         # macOS/Linux
# Edit .env — set SECRET_KEY, ADMIN_EMAIL, ADMIN_PASSWORD

# Database
set FLASK_APP=wsgi.py          # Windows
# export FLASK_APP=wsgi.py     # macOS/Linux

flask db upgrade
flask seed

# Run
python wsgi.py