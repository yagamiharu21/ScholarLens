# ScholarLens

ScholarLens is a scholarship discovery and eligibility-matching web app built for the SerpApi India Hackathon 2026.

## What it does

ScholarLens allows students to enter their:

- Age
- State
- Category
- Education level
- Annual family income
- Academic percentage

It then uses **SerpApi Google Search** to discover scholarship opportunities and ranks them based on:

- Profile eligibility match
- Source trust
- Government and institutional source priority
- Available deadline information

Each result also explains **why the student may match** the scholarship.

## Tech Stack

- Python
- Flask
- SerpApi
- HTML/CSS
- BeautifulSoup
- PyPDF

## How to Run

### 1. Clone the repository

```bash
git clone https://github.com/yagamiharu21/ScholarLens.git
cd ScholarLens
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

### 3. Activate the virtual environment

```bash
venv\Scripts\activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Add your SerpApi key

Create a `.env` file in the project folder and add:

```text
SERPAPI_KEY=your_serpapi_key_here
```

### 6. Run ScholarLens

```bash
python app.py
```

Then open:

```text
http://127.0.0.1:5000
```

## Important

ScholarLens provides an estimated eligibility match. Users should always verify the final eligibility requirements, deadline, and application instructions on the official scholarship source.

## Project Structure

```text
ScholarLens/
├── app.py
├── requirements.txt
├── .gitignore
└── templates/
    ├── index.html
    └── results.html
```
