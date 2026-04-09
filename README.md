# 🏥 Multicare AI Hospital
## AI-Based Hospital Support Chatbot with Voice & WhatsApp Integration

---

## 📁 PROJECT STRUCTURE

```
multicare_hospital/
├── app.py                    ← Flask backend (all routes + chatbot logic)
├── requirements.txt          ← Python dependencies
├── README.md                 ← This file
├── instance/
│   └── hospital.db           ← SQLite database (auto-created on first run)
├── static/
│   ├── css/
│   │   └── style.css         ← Complete stylesheet
│   └── js/
│       └── main.js           ← All frontend logic (chatbot, voice, forms)
└── templates/
    ├── index.html            ← Main hospital website
    ├── login.html            ← Login page
    └── register.html         ← Registration page
```

---

## 🗄️ DATABASE SCHEMA

### Table: users
| Column     | Type    | Description             |
|------------|---------|-------------------------|
| id         | INTEGER | Primary key             |
| name       | TEXT    | Full name               |
| email      | TEXT    | Unique email (login)    |
| phone      | TEXT    | Phone number            |
| password   | TEXT    | SHA-256 hashed password |
| created_at | TEXT    | Registration timestamp  |

### Table: appointments
| Column       | Type    | Description              |
|--------------|---------|--------------------------|
| id           | INTEGER | Primary key              |
| user_id      | INTEGER | FK → users.id            |
| patient_name | TEXT    | Patient full name        |
| doctor       | TEXT    | Selected doctor          |
| department   | TEXT    | Selected department      |
| date         | TEXT    | Appointment date         |
| time         | TEXT    | Appointment time slot    |
| reason       | TEXT    | Reason / symptoms        |
| status       | TEXT    | Pending / Confirmed      |
| created_at   | TEXT    | Booking timestamp        |

### Table: chat_history
| Column     | Type    | Description                  |
|------------|---------|------------------------------|
| id         | INTEGER | Primary key                  |
| user_id    | INTEGER | FK → users.id (nullable)     |
| session_id | TEXT    | Browser session identifier   |
| role       | TEXT    | 'user' or 'bot'              |
| message    | TEXT    | Message content              |
| timestamp  | TEXT    | Message timestamp            |

---

## 🚀 HOW TO RUN IN VS CODE

### Step 1 – Prerequisites
- Install [Python 3.10+](https://python.org/downloads)
- Install [VS Code](https://code.visualstudio.com/)
- Install VS Code extension: **Python** (by Microsoft)

### Step 2 – Open Project
```bash
# Open the project folder in VS Code
File → Open Folder → select multicare_hospital/
```

### Step 3 – Create Virtual Environment
Open the VS Code Terminal (`Ctrl + ~`) and run:
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac / Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 4 – Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 5 – Run the Server
```bash
python app.py
```

You should see:
```
✅ Database initialized.
🏥 Multicare AI Hospital server starting on http://127.0.0.1:5000
```

### Step 6 – Open in Browser
Go to: **http://127.0.0.1:5000**

---

## 🤖 CHATBOT – HOW TO TEST

1. Open the site → click the **green robot button** (bottom-right)
2. Type any of these to test:
   - `hello` → Welcome message
   - `timings` → OPD hours
   - `departments` → All specialties
   - `doctors` → Doctor list
   - `book appointment` → Booking guidance
   - `emergency` → Emergency info
   - `I have fever and cough` → Symptom checker
   - `chest pain` → Urgent cardiac alert
   - `I feel sad and anxious` → Mental health support
   - `bye` → Goodbye

3. Use the **quick chips** (Timings, Departments, Book, Emergency)

---

## 🎤 VOICE INPUT – HOW TO TEST

1. Open the chatbot widget
2. Click the **🎤 microphone button**
3. Allow microphone permission in browser
4. Speak clearly (e.g. "I have a headache")
5. The AI will transcribe and respond

**Text-to-Speech (TTS):**
- Click the **🔊 speaker icon** in the chat header
- The bot will read its responses aloud
- Works best in Chrome / Edge

**Browser Support:** Chrome ✅ | Edge ✅ | Firefox ⚠️ | Safari ⚠️

---

## 📅 APPOINTMENT BOOKING – HOW TO TEST

1. Click **"Book Appointment"** in navbar or hero
2. Fill in the form:
   - Patient Name
   - Select Department (loads doctors dynamically)
   - Select Doctor
   - Pick Date & Time
   - Add Reason (optional)
3. Click **"Confirm Appointment"**
4. A success popup shows your **Booking ID** (e.g. #MC0001)

---

## 🔐 AUTH – HOW TO TEST

**Register:**
1. Go to `http://127.0.0.1:5000/register`
2. Fill in name, email, phone, password
3. Auto-redirects to homepage

**Login:**
1. Go to `http://127.0.0.1:5000/login`
2. Enter registered email + password
3. Navbar shows your name

**Logout:**
- Click **Logout** in the navbar

---

## 📱 WHATSAPP INTEGRATION (Twilio Setup)

### Step 1 – Install Twilio
```bash
pip install twilio
```

### Step 2 – Create a Twilio Account
- Go to [twilio.com](https://www.twilio.com) → Sign up for free
- Navigate to **Messaging → Try WhatsApp**

### Step 3 – Configure Environment Variables
Create a `.env` file (never commit this!):
```
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
```

### Step 4 – Expose Localhost (for Twilio webhook)
```bash
# Install ngrok
ngrok http 5000
# Copy the HTTPS URL e.g. https://abc123.ngrok.io
```

### Step 5 – Set Webhook in Twilio Console
- Go to: Messaging → Settings → WhatsApp Sandbox
- Set **"When a message comes in"** to:
  `https://abc123.ngrok.io/whatsapp`

### Step 6 – Enable Code in app.py
Uncomment lines in the `/whatsapp` route:
```python
from twilio.twiml.messaging_response import MessagingResponse
incoming_msg = request.values.get("Body", "").strip()
reply_text   = chatbot_reply(incoming_msg)
resp = MessagingResponse()
resp.message(reply_text)
return str(resp)
```

### Step 7 – Test on WhatsApp
- Save Twilio sandbox number
- Send: `join <sandbox-keyword>` to activate
- Now text normally and the bot replies!

---

## 🔌 FRONTEND ↔ BACKEND CONNECTION

| Frontend Action       | JS Function          | API Endpoint              |
|-----------------------|----------------------|---------------------------|
| Chat message sent     | `sendMessage()`      | `POST /api/chat`          |
| Department loaded     | `loadDepartments()`  | `GET  /api/departments`   |
| Doctor list loaded    | `loadDoctors()`      | `GET  /api/doctors?dept=` |
| Search bar typed      | `doSearch()`         | `GET  /api/search?q=`     |
| Appointment submitted | `submitAppointment()`| `POST /api/book-appointment` |
| Login submitted       | `doLogin()`          | `POST /login`             |
| Register submitted    | `doRegister()`       | `POST /register`          |

---

## 🏥 HOSPITAL BRANDING

**Name:** Multicare AI Hospital

**Logo Concept:**
- A circle (representing care, completeness)
- Inside: a medical cross (+) with 4 small circles at each arm tip (representing AI nodes / connectivity)
- Color: White on gradient green-to-blue background
- Font: SYNE (bold, modern) for "Multicare" + DM Sans (clean) for "AI Hospital"

**Tagline:** *"Smart Healthcare for a Better Tomorrow"*

**Color Theme:**
- Primary: `#0a8f6e` (Medical Green)
- Secondary: `#0f6fbd` (Trust Blue)
- Accent: `#00d9a6` (AI Teal)
- Dark BG: `#062a20` (Deep Forest Green)

---

## 🧪 QUICK TEST CHECKLIST (PBL Demo)

- [ ] Open website: http://127.0.0.1:5000
- [ ] Register a new user
- [ ] Login with credentials
- [ ] Use search bar → type "cardio"
- [ ] Click a department card → scrolls to booking form
- [ ] Book an appointment → see success popup
- [ ] Open chatbot → type "I have fever and cough"
- [ ] Enable TTS → bot speaks the response
- [ ] Click mic button → speak a question
- [ ] Test emergency: type "emergency" in chatbot
- [ ] View on mobile (resize browser) → responsive layout

---

## ⚠️ IMPORTANT NOTES

1. **NOT for real medical use** – This is an educational/PBL project.
2. Voice features work best in **Google Chrome**.
3. WhatsApp requires a Twilio account + ngrok for local testing.
4. In production, change `app.secret_key` to a secure random string.
5. Store Twilio credentials in environment variables, never in code.

---

*Built for PBL Presentation | Multicare AI Hospital © 2024*
