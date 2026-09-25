
# NIVADA

## AI-Powered Civic Complaint Management Platform

NIVADA is an AI-powered civic complaint management system that helps citizens submit complaints and enables officers to manage, track, and resolve them efficiently.

It combines **AI, NLP, Geospatial Intelligence, FastAPI, PostgreSQL, PostGIS, and interactive maps**.

---

## 🚀 Features

### Citizen
- Registration and Login
- Submit complaints
- Track complaints
- View complaint history
- Verify resolved complaints
- Notifications
- Interactive complaint map
- Civic insights

### Officer
- Officer registration and login
- View assigned complaints
- Update complaint status
- Manage complaint priority
- Location-based complaint management

### AI
- Complaint classification
- Department routing
- AI confidence score
- Priority analysis

### GIS
- Country → State → District → Taluka → Village hierarchy
- Latitude/Longitude support
- Complaint markers
- Heatmaps
- Geographic filtering
- PostGIS spatial queries

### Analytics
- Total complaints
- Pending / In Progress / Resolved
- Resolution rate
- Category distribution
- Department distribution
- Priority distribution
- Complaint trends
- CSV export

---

## 🏗️ Architecture

```text
Citizen
   ↓
Frontend
   ↓
FastAPI Backend
   ↓
AI Classification
   ↓
Geographic Processing
   ↓
PostgreSQL + PostGIS
   ↓
Officer Dashboard
   ↓
Complaint Resolution
   ↓
Citizen Verification
   ↓
Analytics + Maps
````

---

## 🤖 AI Workflow

```text
Complaint Text
      ↓
Text Processing
      ↓
Transformer Model
      ↓
Category + Confidence
      ↓
Department Routing
```

Example:

```text
"There is no water supply in our village."

        ↓

Category: Water
Department: Water Department
Priority: High
Confidence: 94%
```

---

## 🌍 Geographic Hierarchy

```text
Country
   ↓
State
   ↓
District
   ↓
Taluka
   ↓
Village
```

PostGIS can be used to identify and query geographic boundaries using latitude and longitude.

---

## 🗄️ Database

Main entities:

```text
Users
Officers
Departments
Complaint Categories
Countries
States
Districts
Talukas
Villages
Complaints
```

Complaint relationships:

```text
User
 ↓
Complaint
 ├── Category
 ├── Department
 ├── Officer
 └── Location
      ├── Country
      ├── State
      ├── District
      ├── Taluka
      └── Village
```

---

## 🛠️ Tech Stack

| Category   | Technology            |
| ---------- | --------------------- |
| Backend    | FastAPI               |
| Language   | Python                |
| Database   | PostgreSQL            |
| GIS        | PostGIS               |
| ORM        | SQLAlchemy            |
| AI         | PyTorch, Transformers |
| ML         | Scikit-learn          |
| Data       | Pandas, NumPy         |
| Frontend   | HTML, JavaScript      |
| UI         | Tailwind CSS          |
| Maps       | Leaflet.js            |
| MLOps      | MLflow                |
| Monitoring | Prometheus, Grafana   |

---

## 📁 Project Structure

```text
nivadaAI/
│
├── backend/
│   └── app/
│       ├── auth/
│       ├── complaint/
│       ├── dashboard/
│       ├── geo/
│       ├── db/
│       └── main.py
│
├── frontend/
│   ├── user/
│   └── officer/
│
├── requirements.txt
├── .gitignore
└── README.md
```

---

## ⚙️ Installation

### Clone

```bash
git clone https://github.com/Prajwal7896/nivada_off.git
cd nivada_off
```

### Virtual Environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Install Dependencies

```powershell
pip install -r requirements.txt
```

---

## 🗄️ Database Setup

Create PostgreSQL database:

```sql
CREATE DATABASE nivada;
```

Enable PostGIS:

```sql
CREATE EXTENSION postgis;
```

Configure `.env`:

```env
DATABASE_URL=postgresql://username:password@localhost:5432/nivada
SECRET_KEY=your-secret-key
```

---

## ▶️ Run

```powershell
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000/
```

API documentation:

```text
http://127.0.0.1:8000/docs
```

Health check:

```text
http://127.0.0.1:8000/health
```

---

## 🔄 Complaint Lifecycle

```text
Submitted
   ↓
Pending
   ↓
Assigned
   ↓
In Progress
   ↓
Resolved
   ↓
Citizen Verification
   ↓
Solved / Not Solved
```

---

## 📊 Future Improvements

* Multilingual AI
* Image-based complaint detection
* RAG for similar complaints
* Automated village detection
* AI priority prediction
* Model monitoring
* Automated retraining
* Large-scale deployment
* Redis and background workers

---

## 🎯 Vision

NIVADA aims to transform citizen complaints into **AI-powered, location-aware civic intelligence**.

```text
AI + GIS + Data + Automation
          ↓
   Civic Intelligence
```

---

## 👨‍💻 Developer

**Prajwal Sankpal**

B.Tech Computer Engineering
D.Y. Patil College of Engineering, Akurdi

GitHub:
[https://github.com/Prajwal7896](https://github.com/Prajwal7896)

---

## 📄 License

This project is currently intended for educational, research, and portfolio purposes.

```
```