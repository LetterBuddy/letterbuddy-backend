# LetterBuddy Backend
## To run locally, follow these steps
## 1. Clone the Repository
Run the following command in your terminal to clone the repository: \
`git clone https://github.com/LetterBuddy/letterbuddy-backend.git`

## 2. Make sure you have a .env file(or have these env vars on your machine) with: 
### SECRET_KEY, DATABASE_URL, JWT_SECRET_KEY, CLOUDINARY_URL, GROQ_API_KEY, AZURE_TOKEN(GitHub token with GitHub models read access)

## 3. Install requirements(preferably on a virtual environment of Python) 
Run this command for installing the requirements: \
`pip install -r requirements.txt`

## 4. Run the server locally:
Run this command: \
`python manage.py runserver`

## To run the automation tests via the terminal:
`python manage.py test --keepdb`
