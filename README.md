# 🏠 Property Comparison App

A Streamlit app to compare Norwegian properties from FINN.no

## Features
- Compare up to 5 properties
- Distance calculations to Asker/Sandvika stations
- Area-based price adjustments
- Interactive radar charts
- Detailed property analysis
- **Browser back button works!** (URL-based navigation)

## Local Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the app:
```bash
streamlit run app.py
```

## Deployment to Streamlit Cloud

1. Push this repository to GitHub
2. Go to https://streamlit.io/cloud
3. Click "New app"
4. Select your repository
5. Set main file: `app.py`
6. Deploy!

## Usage

1. Add FINN.no property links
2. Choose station (Asker or Sandvika)
3. Click Analyze for each property
4. View details or compare all properties
