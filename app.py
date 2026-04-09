"""
Multicare AI Hospital - Flask Backend
=====================================
Main application file - handles all routes, authentication, chatbot, and WhatsApp.
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
import sqlite3
import hashlib
import os
import json
from datetime import datetime
import re

# ── Optional: Twilio for WhatsApp ──────────────────────────────────────────
# pip install twilio
# Uncomment when you have Twilio credentials
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client

app = Flask(__name__)
app.secret_key = "multicare_secret_key_2024"   # Change in production!
CORS(app)

DB_PATH = "instance/hospital.db"

# Global state for WhatsApp conversations
user_states = {}

# ══════════════════════════════════════════════════════════════
#  DATABASE SETUP
# ══════════════════════════════════════════════════════════════

def get_db():
    """Return a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create all tables if they don't exist."""
    os.makedirs("instance", exist_ok=True)
    conn = get_db()
    cur = conn.cursor()

    # Users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT    NOT NULL,
            email      TEXT    UNIQUE NOT NULL,
            phone      TEXT,
            password   TEXT    NOT NULL,
            created_at TEXT    DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Appointments table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER,
            patient_name TEXT   NOT NULL,
            doctor      TEXT    NOT NULL,
            department  TEXT    NOT NULL,
            date        TEXT    NOT NULL,
            time        TEXT    NOT NULL,
            reason      TEXT,
            status      TEXT    DEFAULT 'Pending',
            created_at  TEXT    DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Chat history table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER,
            session_id TEXT,
            role       TEXT    NOT NULL,
            message    TEXT    NOT NULL,
            timestamp  TEXT    DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Database initialized.")


# ══════════════════════════════════════════════════════════════
#  CHATBOT ENGINE  (rule-based + symptom checker)
# ══════════════════════════════════════════════════════════════

HOSPITAL_INFO = {
    "timings":     "🕐 OPD: Mon–Sat 8 AM–8 PM | Emergency: 24/7 | Sunday: Emergency only",
    "departments": ["Cardiology", "Neurology", "Orthopedics", "Pediatrics",
                    "Dermatology", "Oncology", "Gynecology", "Ophthalmology",
                    "ENT", "Psychiatry", "General Medicine", "Emergency"],
    "doctors": {
        "Cardiology":      ["Dr. Arjun Sharma", "Dr. Priya Nair"],
        "Neurology":       ["Dr. Rajesh Kumar", "Dr. Sneha Patel"],
        "Orthopedics":     ["Dr. Vikram Singh", "Dr. Anita Rao"],
        "Pediatrics":      ["Dr. Meera Iyer", "Dr. Suresh Menon"],
        "Dermatology":     ["Dr. Kavya Reddy"],
        "General Medicine":["Dr. Ramesh Gupta", "Dr. Lakshmi Devi"],
    },
    "location":  "📍 123 Health Avenue, Bengaluru, Karnataka – 560001",
    "phone":     "📞 Helpline: +91-80-12345678 | Emergency: 108",
    "email":     "✉️  care@multicareai.com",
    "facilities":["24/7 Emergency", "ICU & NICU", "Advanced Diagnostics",
                  "Pharmacy", "Ambulance Service", "Blood Bank", "Cafeteria"],
}

# Symptom → possible conditions mapping
SYMPTOM_MAP = {
    ("fever", "cold", "cough", "runny nose", "sore throat"):
        ("Common Cold / Flu", "General Medicine", "Rest, fluids, paracetamol. See a doctor if fever > 3 days."),
    ("chest pain", "shortness of breath", "palpitations", "dizziness"):
        ("Possible Cardiac Issue ⚠️", "Cardiology", "Seek IMMEDIATE medical attention. Call 108."),
    ("headache", "migraine", "nausea", "blurred vision", "seizure"):
        ("Neurological Concern", "Neurology", "Avoid bright lights; consult a neurologist promptly."),
    ("joint pain", "knee pain", "back pain", "fracture", "sprain"):
        ("Musculoskeletal Issue", "Orthopedics", "Apply ice, rest. See orthopedics if pain persists > 48 h."),
    ("rash", "itching", "skin irritation", "acne", "eczema"):
        ("Dermatological Issue", "Dermatology", "Avoid scratching; use mild soap. Book a dermatology consult."),
    ("stomach pain", "vomiting", "diarrhea", "indigestion", "acidity"):
        ("Gastrointestinal Issue", "General Medicine", "Stay hydrated; avoid spicy food. See a doctor if > 24 h."),
    ("eye pain", "red eyes", "blurred vision"):
        ("Eye Concern", "Ophthalmology", "Avoid rubbing eyes. See an ophthalmologist soon."),
    ("ear pain", "hearing loss", "ear discharge"):
        ("ENT Issue", "ENT", "Avoid inserting objects in ear. Book ENT appointment."),
    ("sadness", "anxiety", "depression", "stress", "panic"):
        ("Mental Health Concern", "Psychiatry", "You are not alone. Talk to our psychiatrist – it helps."),
    ("pregnancy", "missed period", "prenatal"):
        ("Gynecological / Obstetric Care", "Gynecology", "Schedule a consultation with our gynecology team."),
    ("child fever", "child vomiting", "baby rash", "infant"):
        ("Pediatric Concern", "Pediatrics", "Book a pediatrician appointment for your child."),
}


def symptom_checker(text: str) -> dict | None:
    """Match user input against the symptom map and return advice."""
    text_lower = text.lower()
    for keywords, (condition, dept, advice) in SYMPTOM_MAP.items():
        if any(kw in text_lower for kw in keywords):
            doctors = HOSPITAL_INFO["doctors"].get(dept, ["Our specialist team"])
            return {
                "condition": condition,
                "department": dept,
                "advice": advice,
                "doctors": doctors,
            }
    return None


def chatbot_reply(message: str, user_id: int | None = None) -> str:
    """
    Rule-based chatbot that handles:
    - Hospital info queries
    - Symptom checking
    - Appointment guidance
    """
    msg = message.lower().strip()

    # ── Greetings ──────────────────────────────────────────────
    if any(w in msg for w in ["hello", "hi", "hey", "good morning", "good evening", "namaste"]):
        return ("👋 Hello! Welcome to **Multicare AI Hospital**!\n\n"
                "I'm your AI health assistant. I can help you with:\n"
                "• 🏥 Hospital information & timings\n"
                "• 👨‍⚕️ Doctor & department details\n"
                "• 📅 Booking appointments\n"
                "• 🩺 Symptom checking\n\n"
                "How can I assist you today?")

    # ── Timings ────────────────────────────────────────────────
    if any(w in msg for w in ["timing", "time", "hours", "open", "close", "schedule"]):
        return f"🕐 **Hospital Timings:**\n\n{HOSPITAL_INFO['timings']}\n\n📞 {HOSPITAL_INFO['phone']}"

    # ── Departments ────────────────────────────────────────────
    if any(w in msg for w in ["department", "dept", "speciality", "specialty", "services"]):
        depts = "\n".join(f"  • {d}" for d in HOSPITAL_INFO["departments"])
        return f"🏥 **Available Departments:**\n\n{depts}\n\nAsk me about any specific department!"

    # ── Doctors ────────────────────────────────────────────────
    if any(w in msg for w in ["doctor", "dr", "physician", "specialist", "who"]):
        result = []
        for dept, docs in HOSPITAL_INFO["doctors"].items():
            result.append(f"**{dept}:** {', '.join(docs)}")
        return "👨‍⚕️ **Our Doctors:**\n\n" + "\n".join(result) + "\n\nType a department name for specific info."

    # ── Location ───────────────────────────────────────────────
    if any(w in msg for w in ["location", "address", "where", "directions", "map"]):
        return f"{HOSPITAL_INFO['location']}\n\n{HOSPITAL_INFO['phone']}\n{HOSPITAL_INFO['email']}"

    # ── Appointment ────────────────────────────────────────────
    if any(w in msg for w in ["appointment", "book", "schedule", "consult", "visit"]):
        return ("📅 **Book an Appointment:**\n\n"
                "**Option 1:** Click the **'Book Appointment'** button on our website.\n"
                "**Option 2:** I'll help you right here!\n\n"
                "Please tell me:\n"
                "1️⃣ Your full name\n"
                "2️⃣ Preferred department / doctor\n"
                "3️⃣ Preferred date & time\n"
                "4️⃣ Reason for visit\n\n"
                f"Or call us: {HOSPITAL_INFO['phone']}")

    # ── Emergency ──────────────────────────────────────────────
    if any(w in msg for w in ["emergency", "urgent", "critical", "ambulance", "108"]):
        return ("🚨 **EMERGENCY SERVICES – 24/7**\n\n"
                "📞 **Ambulance / Emergency: 108**\n"
                f"📞 Hospital Direct: +91-80-12345678\n\n"
                f"{HOSPITAL_INFO['location']}\n\n"
                "Our emergency team is available **round-the-clock**. Please call immediately!")

    # ── Facilities ─────────────────────────────────────────────
    if any(w in msg for w in ["facilit", "service", "feature", "icu", "blood bank", "pharmacy"]):
        facs = "\n".join(f"  ✅ {f}" for f in HOSPITAL_INFO["facilities"])
        return f"🏨 **Our Facilities:**\n\n{facs}"

    # ── Symptom checker ────────────────────────────────────────
    result = symptom_checker(msg)
    if result:
        docs_str = ", ".join(result["doctors"])
        return (f"🩺 **Symptom Analysis:**\n\n"
                f"**Possible Condition:** {result['condition']}\n"
                f"**Recommended Department:** {result['department']}\n"
                f"**Advice:** {result['advice']}\n\n"
                f"**Suggested Doctors:** {docs_str}\n\n"
                f"⚠️ *This is AI guidance only – always consult a qualified doctor.*\n"
                f"📅 [Book Appointment](#book)")

    # ── Goodbye ────────────────────────────────────────────────
    if any(w in msg for w in ["bye", "goodbye", "thanks", "thank you", "ok"]):
        return "😊 Thank you for choosing **Multicare AI Hospital**! Stay healthy. Goodbye! 👋"

    # ── Fallback ───────────────────────────────────────────────
    return ("🤔 I didn't quite understand that. Here's what I can help with:\n\n"
            "• Type **'timings'** – Hospital hours\n"
            "• Type **'departments'** – All specialties\n"
            "• Type **'doctors'** – Our medical team\n"
            "• Type **'appointment'** – Book a visit\n"
            "• Type **'emergency'** – Emergency info\n"
            "• Describe your **symptoms** – AI checker\n\n"
            "Or call 📞 +91-80-12345678")


# ══════════════════════════════════════════════════════════════
#  HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def save_chat(session_id: str, role: str, message: str, user_id: int | None = None):
    conn = get_db()
    conn.execute(
        "INSERT INTO chat_history (user_id, session_id, role, message) VALUES (?,?,?,?)",
        (user_id, session_id, role, message)
    )
    conn.commit()
    conn.close()


# ══════════════════════════════════════════════════════════════
#  ROUTES – PAGES
# ══════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return render_template("index.html", user=session.get("user"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    data  = request.get_json() or request.form
    email = data.get("email", "").strip().lower()
    pwd   = data.get("password", "")

    conn  = get_db()
    user  = conn.execute(
        "SELECT * FROM users WHERE email=? AND password=?",
        (email, hash_password(pwd))
    ).fetchone()
    conn.close()

    if user:
        session["user"]    = {"id": user["id"], "name": user["name"], "email": user["email"]}
        session["user_id"] = user["id"]
        if request.is_json:
            return jsonify({"success": True, "name": user["name"]})
        return redirect(url_for("index"))

    if request.is_json:
        return jsonify({"success": False, "error": "Invalid email or password"}), 401
    return render_template("login.html", error="Invalid email or password")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    
    data = request.get_json() if request.content_type == 'application/json' else request.form
    name  = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    phone = data.get("phone", "").strip()
    pwd   = data.get("password", "")

    if not all([name, email, pwd]):
        msg = "Name, email, and password are required."
        if request.is_json:
            return jsonify({"success": False, "error": msg}), 400
        return render_template("register.html", error=msg)

    try:
        conn = get_db()
        conn.execute(
            "INSERT INTO users (name, email, phone, password) VALUES (?,?,?,?)",
            (name, email, phone, hash_password(pwd))
        )
        conn.commit()
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        conn.close()
        session["user"]    = {"id": user["id"], "name": user["name"], "email": user["email"]}
        session["user_id"] = user["id"]
        if request.is_json:
            return jsonify({"success": True, "name": name})
        return redirect(url_for("index"))
    except sqlite3.IntegrityError:
        msg = "Email already registered. Please login."
        if request.is_json:
            return jsonify({"success": False, "error": msg}), 409
        return render_template("register.html", error=msg)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/my-appointments")
def my_appointments():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM appointments 
        WHERE user_id = ?
        ORDER BY date, time
    """, (session["user_id"],))

    appointments = cur.fetchall()
    conn.close()

    return render_template("appointments.html", appointments=appointments)

@app.route("/cancel/<int:appt_id>")
def cancel_appointment(appt_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE appointments 
        SET status = 'Cancelled'
        WHERE id = ? AND user_id = ?
    """, (appt_id, session["user_id"]))

    conn.commit()
    conn.close()

    return redirect(url_for("my_appointments"))

@app.route("/diagnostics")
def diagnostics():
    return render_template("diagnostics.html")

@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    incoming_msg = request.form.get("Body").strip().lower()
    user = request.form.get("From")

    resp = MessagingResponse()
    msg = resp.message()

    state = user_states.get(user, {})

    # 🟢 1. GREETING MENU
    if incoming_msg in ["hi", "hello"]:
        msg.body("""
👋 Hello! Welcome to *Multicare AI Hospital*

I can help you with:

🏥 Hospital information & timings  
👨‍⚕️ Doctor & department details  
📅 Booking appointments  
🩺 Symptom checking  

👉 Type your choice
        """)
        return str(resp)

    # 🟢 2. HOSPITAL INFO
    if "hospital" in incoming_msg or "timing" in incoming_msg:
        msg.body("""
🏥 Hospital Timings:

🕘 OPD: Mon–Sat 8 AM – 8 PM  
🚨 Emergency: 24/7 Available  
📞 Helpline: +91-80-12345678
        """)
        return str(resp)

    # 🟢 3. DOCTORS
    if "doctor" in incoming_msg or "department" in incoming_msg:
        msg.body("""
👨‍⚕️ Available Doctors:

• Dr. Rajesh Kumar – Cardiology  
• Dr. Lakshmi Devi – General Medicine  
• Dr. Ramesh Gupta – Neurology  

👉 Type *Book* to schedule appointment
        """)
        return str(resp)

    # 🟢 4. START BOOKING
    if "book" in incoming_msg:
        user_states[user] = {"step": "name"}
        msg.body("👤 Please enter your full name:")
        return str(resp)

    # 🟢 5. BOOKING FLOW
    if state.get("step") == "name":
        state["name"] = incoming_msg
        state["step"] = "department"
        msg.body("🏥 Enter department (Cardiology, General, etc):")
        return str(resp)

    if state.get("step") == "department":
        state["department"] = incoming_msg
        state["step"] = "datetime"
        msg.body("📅 Enter date & time:")
        return str(resp)

    if state.get("step") == "datetime":
        state["datetime"] = incoming_msg
        state["step"] = "reason"
        msg.body("📝 Reason for visit:")
        return str(resp)

    if state.get("step") == "reason":
        state["reason"] = incoming_msg

        booking_id = "MC" + str(len(user_states)) + "04"

        msg.body(f"""
✅ Appointment Booked!

👤 Name: {state['name']}
🏥 Department: {state['department']}
📅 Date: {state['datetime']}
📝 Reason: {state['reason']}
🆔 Booking ID: #{booking_id}
        """)

        user_states.pop(user)
        return str(resp)

    # 🟢 6. SYMPTOM CHECKER START
    if "symptom" in incoming_msg or "check" in incoming_msg:
        user_states[user] = {"step": "symptom"}
        msg.body("🩺 Please tell your symptoms (e.g., fever, headache, cough):")
        return str(resp)

    # 🟢 7. HANDLE SYMPTOMS
    if state.get("step") == "symptom":

        symptoms = incoming_msg

        if "fever" in symptoms:
            reply = "🌡️ You may have a viral infection. Stay hydrated and consult a doctor if needed."

        elif "headache" in symptoms:
            reply = "🤕 It could be stress or migraine. Take rest and drink water."

        elif "cough" in symptoms:
            reply = "😷 Possible cold or infection. If it continues, consult a doctor."

        elif "stomach" in symptoms:
            reply = "🤢 Could be indigestion. Avoid oily food and drink fluids."

        else:
            reply = "⚠️ Symptoms unclear. Please consult a doctor."

        msg.body(f"{reply}\n\n👉 Type *Book* to consult a doctor.")
        user_states.pop(user)
        return str(resp)

    # 🟢 DEFAULT RESPONSE
    msg.body("👉 Type *Hi* to start, *Book* to schedule, or *Symptom checking*.")
    return str(resp)

from flask import render_template, url_for

@app.route('/diagnostic/<name>')
def diagnostic_detail(name):
    data = {

        "xray": {
            "title": "X-Ray",
            "image": url_for('static', filename='images/xray.jpg'),
            "description": "X-rays are imaging tests that use small amounts of radiation to view bones and internal organs.",
            "who_needs": "People with fractures, chest pain, infections, dental issues, or joint problems.",
            "how_it_works": "X-ray beams pass through the body. Bones appear white, soft tissues appear darker.",
            "procedure": "You will stand or lie still while the machine takes images.",
            "preparation": "Remove metal objects. No fasting required.",
            "risks": "Low radiation exposure. Generally safe."
        },

        "mri": {
            "title": "MRI Scan",
            "image": url_for('static', filename='images/mri.jpg'),
            "description": "MRI uses magnetic fields and radio waves to create detailed images.",
            "who_needs": "Brain disorders, spinal issues, joint injuries.",
            "how_it_works": "Magnetic field produces detailed images.",
            "procedure": "You lie inside a tunnel machine.",
            "preparation": "Remove all metal items.",
            "risks": "Not safe for metal implants."
        },

        "ct": {
            "title": "CT Scan",
            "image": url_for('static', filename='images/ct.jpg'),
            "description": "CT scans combine X-rays to create detailed images.",
            "who_needs": "Tumors, internal injuries, infections.",
            "how_it_works": "Multiple X-rays create 3D images.",
            "procedure": "Lie on moving table.",
            "preparation": "Avoid food if needed.",
            "risks": "Higher radiation exposure."
        },

        "lab": {
            "title": "Laboratory Tests",
            "image": url_for('static', filename='images/laboratory.jpg'),
            "description": "Lab tests analyze blood and fluids.",
            "who_needs": "Routine checkups, infections, diabetes.",
            "how_it_works": "Samples tested in lab.",
            "procedure": "Blood or urine sample collected.",
            "preparation": "Fasting may be required.",
            "risks": "Minimal pain."
        },

        "ultrasound": {
            "title": "Ultrasound",
            "image": url_for('static', filename='images/ultrasound.jpg'),
            "description": "Ultrasound uses sound waves to create images.",
            "who_needs": "Pregnancy, organ evaluation.",
            "how_it_works": "Sound waves create images.",
            "procedure": "Gel + probe scan.",
            "preparation": "Drink water.",
            "risks": "Completely safe."
        }
    }

    return render_template("diagnostic_detail.html", data=data[name])

@app.route("/test")
def test():
    return "Working"


# ══════════════════════════════════════════════════════════════
#  ROUTES – API
# ══════════════════════════════════════════════════════════════

@app.route("/api/chat", methods=["POST"])
def chat():
    """Main chatbot endpoint."""
    data       = request.get_json()
    message    = data.get("message", "").strip()
    session_id = data.get("session_id", "anonymous")
    user_id    = session.get("user_id")

    if not message:
        return jsonify({"error": "Empty message"}), 400

    # Save user message
    save_chat(session_id, "user", message, user_id)

    # Generate bot reply
    reply = chatbot_reply(message, user_id)

    # Save bot reply
    save_chat(session_id, "bot", reply, user_id)

    return jsonify({"reply": reply})


@app.route("/api/book-appointment", methods=["POST"])
def book_appointment():
    """Book an appointment."""
    data = request.get_json()
    required = ["patient_name", "doctor", "department", "date", "time"]

    for field in required:
        if not data.get(field):
            return jsonify({"success": False, "error": f"'{field}' is required"}), 400

    try:
        conn = get_db()
        cur  = conn.cursor()
        cur.execute("""
            INSERT INTO appointments
                (user_id, patient_name, doctor, department, date, time, reason)
            VALUES (?,?,?,?,?,?,?)
        """, (
            session.get("user_id"),
            data["patient_name"],
            data["doctor"],
            data["department"],
            data["date"],
            data["time"],
            data.get("reason", "")
        ))
        appt_id = cur.lastrowid
        conn.commit()
        conn.close()
        return jsonify({
            "success": True,
            "appointment_id": appt_id,
            "message": (f"✅ Appointment confirmed!\n"
                        f"Patient: {data['patient_name']}\n"
                        f"Doctor: {data['doctor']} ({data['department']})\n"
                        f"Date: {data['date']} at {data['time']}\n"
                        f"Booking ID: #MC{appt_id:04d}")
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/appointments", methods=["GET"])
def get_appointments():
    """Get appointments for logged-in user."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Login required"}), 401
    conn   = get_db()
    rows   = conn.execute(
        "SELECT * FROM appointments WHERE user_id=? ORDER BY created_at DESC",
        (user_id,)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/doctors", methods=["GET"])
def get_doctors():
    """Return doctor list, optionally filtered by department."""
    dept = request.args.get("department", "")
    if dept:
        docs = HOSPITAL_INFO["doctors"].get(dept, [])
        return jsonify({"doctors": docs})
    return jsonify({"doctors": HOSPITAL_INFO["doctors"]})


@app.route("/api/departments", methods=["GET"])
def get_departments():
    return jsonify({"departments": HOSPITAL_INFO["departments"]})


@app.route("/api/search", methods=["GET"])
def search():
    """Search doctors and departments."""
    q = request.args.get("q", "").lower()
    if not q:
        return jsonify({"results": []})

    results = []
    for dept in HOSPITAL_INFO["departments"]:
        if q in dept.lower():
            results.append({"type": "department", "name": dept})

    for dept, docs in HOSPITAL_INFO["doctors"].items():
        for doc in docs:
            if q in doc.lower():
                results.append({"type": "doctor", "name": doc, "department": dept})

    return jsonify({"results": results})


# ══════════════════════════════════════════════════════════════
#  WHATSAPP (TWILIO) WEBHOOK
# ══════════════════════════════════════════════════════════════

@app.route("/twilio/whatsapp", methods=["POST"])
def whatsapp_webhook():
    """
    Twilio WhatsApp webhook.
    Steps to enable:
      1. pip install twilio
      2. Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN in env
      3. In Twilio Console → Messaging → WhatsApp Sandbox
         set webhook URL to: https://your-domain.com/whatsapp
    """
    # Uncomment the block below after installing twilio:
    # ------------------------------------------------------
    # incoming_msg = request.values.get("Body", "").strip()
    # sender       = request.values.get("From", "")
    # reply_text   = chatbot_reply(incoming_msg)
    # resp = MessagingResponse()
    # resp.message(reply_text)
    # return str(resp)
    # ------------------------------------------------------
    return "WhatsApp webhook active. Install twilio and uncomment the code in app.py.", 200


# ══════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    init_db()
    print("🏥 Multicare AI Hospital server starting on http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
