cat > README.md <<'EOF'
# Biometric System (Face + Voice) - Demo

## Structure
- backend/ : FastAPI backend
- frontend/ : HTML/CSS/JS demo UI

## Run Backend
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000

## Run Frontend
cd frontend
python3 -m http.server 5500
EOF
