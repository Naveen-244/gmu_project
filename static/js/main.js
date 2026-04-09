/**
 * MULTICARE AI HOSPITAL – MAIN.JS
 * ════════════════════════════════
 * Handles: Chatbot UI, Voice (Web Speech API),
 *          Appointments, Auth, Search, Departments,
 *          Animations, WhatsApp button.
 */

// ══════════════════════════════════════════════
//  GLOBAL STATE
// ══════════════════════════════════════════════
const SESSION_ID = 'sess_' + Math.random().toString(36).substr(2, 9);
let isChatOpen    = false;
let ttsEnabled    = false;
let isListening   = false;
let speechRecog   = null;
let currentUser   = null;      // Populated from server session check

// ══════════════════════════════════════════════
//  DOM READY
// ══════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
  initScrollEffects();
  initNavHighlight();
  loadDepartments();
  loadAppointmentDropdowns();
  checkAuthStatus();
  countUpStats();
  sendWelcomeMessage();
  initVoiceSupport();

  // Set minimum date on appointment date input to today
  const dateInput = document.getElementById('appt_date');
  if (dateInput) {
    const today = new Date().toISOString().split('T')[0];
    dateInput.min = today;
  }

  // Close modals when clicking overlay
  document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', e => {
      if (e.target === overlay) closeModal(overlay.id);
    });
  });

  // Mobile hamburger menu
  const hamburger = document.getElementById('hamburger');
  const nav       = document.getElementById('nav');
  if (hamburger) {
    hamburger.addEventListener('click', () => {
      nav.classList.toggle('open');
    });
    nav.querySelectorAll('.nav-link').forEach(link => {
      link.addEventListener('click', () => nav.classList.remove('open'));
    });
  }
});


// ══════════════════════════════════════════════
//  SCROLL EFFECTS
// ══════════════════════════════════════════════
function initScrollEffects() {
  const header = document.getElementById('header');
  const links  = document.querySelectorAll('.nav-link');

  window.addEventListener('scroll', () => {
    // Sticky header style
    if (window.scrollY > 60) {
      header.classList.add('scrolled');
    } else {
      header.classList.remove('scrolled');
    }

    // Fade-in sections on scroll
    document.querySelectorAll('.service-card, .dept-card, .info-card, .contact-card').forEach(el => {
      const rect = el.getBoundingClientRect();
      if (rect.top < window.innerHeight - 60) {
        el.style.opacity   = '1';
        el.style.transform = 'translateY(0)';
      }
    });
  });

  // Initial state for animated elements
  document.querySelectorAll('.service-card, .dept-card, .info-card, .contact-card').forEach((el, i) => {
    el.style.opacity     = '0';
    el.style.transform   = 'translateY(24px)';
    el.style.transition  = `opacity 0.5s ${i * 0.05}s ease, transform 0.5s ${i * 0.05}s ease`;
  });
}

function initNavHighlight() {
  const sections = document.querySelectorAll('section[id]');
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
        const active = document.querySelector(`.nav-link[href="#${entry.target.id}"]`);
        if (active) active.classList.add('active');
      }
    });
  }, { threshold: 0.4 });
  sections.forEach(s => observer.observe(s));
}


// ══════════════════════════════════════════════
//  ANIMATED COUNT-UP STATS
// ══════════════════════════════════════════════
function countUpStats() {
  const statNums = document.querySelectorAll('.stat-num[data-target]');
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      const el     = entry.target;
      const target = parseInt(el.dataset.target);
      const dur    = 1600;
      const step   = 16;
      const inc    = target / (dur / step);
      let current  = 0;
      const timer  = setInterval(() => {
        current += inc;
        if (current >= target) { current = target; clearInterval(timer); }
        el.textContent = current >= 1000
          ? (current / 1000).toFixed(1) + 'K'
          : Math.floor(current).toString();
      }, step);
      observer.unobserve(el);
    });
  }, { threshold: 0.5 });
  statNums.forEach(el => observer.observe(el));
}


// ══════════════════════════════════════════════
//  SEARCH
// ══════════════════════════════════════════════
let searchTimeout = null;
const searchInput   = document.getElementById('searchInput');
const searchResults = document.getElementById('searchResults');

if (searchInput) {
  searchInput.addEventListener('input', () => {
    clearTimeout(searchTimeout);
    const q = searchInput.value.trim();
    if (!q) { searchResults.innerHTML = ''; return; }
    searchTimeout = setTimeout(() => doSearch(q), 250);
  });
  // Close on outside click
  document.addEventListener('click', e => {
    if (!searchInput.contains(e.target)) searchResults.innerHTML = '';
  });
}

async function doSearch(q) {
  q = q || searchInput.value.trim();
  if (!q) return;
  try {
    const res  = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
    const data = await res.json();
    renderSearchResults(data.results || []);
  } catch { renderSearchResults([]); }
}

function renderSearchResults(results) {
  if (!results.length) {
    searchResults.innerHTML = '<div class="search-result-item"><span>No results found</span></div>';
    return;
  }
  searchResults.innerHTML = results.map(r => `
    <div class="search-result-item" onclick="handleSearchClick('${r.type}','${r.name}')">
      <span class="tag ${r.type === 'department' ? 'tag-dept' : 'tag-doctor'}">
        ${r.type === 'department' ? '🏥 Dept' : '👨‍⚕️ Doctor'}
      </span>
      <span>${r.name}</span>
      ${r.department ? `<span style="color:var(--text-l);font-size:0.78rem;">– ${r.department}</span>` : ''}
    </div>
  `).join('');
}

function handleSearchClick(type, name) {
  searchResults.innerHTML = '';
  searchInput.value = '';
  if (type === 'department') {
    document.getElementById('departments').scrollIntoView({ behavior: 'smooth' });
  } else {
    document.getElementById('book').scrollIntoView({ behavior: 'smooth' });
  }
}


// ══════════════════════════════════════════════
//  DEPARTMENTS
// ══════════════════════════════════════════════
const DEPT_ICONS = {
  'Cardiology':       'fas fa-heartbeat',
  'Neurology':        'fas fa-brain',
  'Orthopedics':      'fas fa-bone',
  'Pediatrics':       'fas fa-baby',
  'Dermatology':      'fas fa-hand-dots',
  'Oncology':         'fas fa-ribbon',
  'Gynecology':       'fas fa-venus',
  'Ophthalmology':    'fas fa-eye',
  'ENT':              'fas fa-ear-listen',
  'Psychiatry':       'fas fa-head-side-brain',
  'General Medicine': 'fas fa-stethoscope',
  'Emergency':        'fas fa-truck-medical',
};

async function loadDepartments() {
  const grid = document.getElementById('deptGrid');
  if (!grid) return;
  try {
    const res  = await fetch('/api/departments');
    const data = await res.json();
    grid.innerHTML = data.departments.map(d => `
      <div class="dept-card" onclick="scrollToBook('${d}')">
        <i class="${DEPT_ICONS[d] || 'fas fa-hospital'}"></i>
        <span>${d}</span>
      </div>
    `).join('');
  } catch {
    grid.innerHTML = '<p style="color:var(--text-l)">Unable to load departments.</p>';
  }
}

function scrollToBook(dept) {
  document.getElementById('book').scrollIntoView({ behavior: 'smooth' });
  setTimeout(() => {
    const sel = document.getElementById('appt_dept');
    if (sel) { sel.value = dept; loadDoctors(); }
  }, 600);
}


// ══════════════════════════════════════════════
//  APPOINTMENT FORM
// ══════════════════════════════════════════════
async function loadAppointmentDropdowns() {
  try {
    const res  = await fetch('/api/departments');
    const data = await res.json();
    const sel  = document.getElementById('appt_dept');
    if (!sel) return;
    data.departments.forEach(d => {
      const opt = document.createElement('option');
      opt.value = d; opt.textContent = d;
      sel.appendChild(opt);
    });
  } catch {}
}

async function loadDoctors() {
  const dept    = document.getElementById('appt_dept').value;
  const docSel  = document.getElementById('appt_doctor');
  docSel.innerHTML = '<option value="">-- Select Doctor --</option>';
  if (!dept) return;
  try {
    const res  = await fetch(`/api/doctors?department=${encodeURIComponent(dept)}`);
    const data = await res.json();
    data.doctors.forEach(d => {
      const opt = document.createElement('option');
      opt.value = d; opt.textContent = d;
      docSel.appendChild(opt);
    });
  } catch {}
}

async function submitAppointment(e) {
  e.preventDefault();
  const resultDiv = document.getElementById('apptResult');
  resultDiv.classList.add('hidden');

  const payload = {
    patient_name: document.getElementById('appt_name').value.trim(),
    doctor:       document.getElementById('appt_doctor').value,
    department:   document.getElementById('appt_dept').value,
    date:         document.getElementById('appt_date').value,
    time:         document.getElementById('appt_time').value,
    reason:       document.getElementById('appt_reason').value.trim(),
  };

  const btn = e.target.querySelector('button[type="submit"]');
  btn.disabled    = true;
  btn.textContent = '⏳ Booking...';

  try {
    const res  = await fetch('/api/book-appointment', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(payload),
    });
    const data = await res.json();

    if (data.success) {
      // Show success modal
      document.getElementById('apptDetails').textContent = data.message;
      openModal('apptModal');
      // Reset form
      e.target.reset();
      document.getElementById('appt_doctor').innerHTML = '<option value="">-- Select Doctor --</option>';
    } else {
      resultDiv.textContent = '❌ ' + (data.error || 'Booking failed. Please try again.');
      resultDiv.classList.remove('hidden');
    }
  } catch {
    resultDiv.textContent = '❌ Network error. Please try again.';
    resultDiv.classList.remove('hidden');
  } finally {
    btn.disabled    = false;
    btn.innerHTML   = '<i class="fas fa-calendar-check"></i> Confirm Appointment';
  }
}


// ══════════════════════════════════════════════
//  AUTH
// ══════════════════════════════════════════════
async function checkAuthStatus() {
  // Check by calling a lightweight endpoint or reading DOM-injected user info
  // For simplicity we use a meta approach: try /api/appointments (requires auth)
  const navAuth = document.getElementById('navAuth');
  if (!navAuth) return;

  // Check if Flask session passed user to template
  // (We'll re-use the window variable set inline if available)
  if (window.CURRENT_USER) {
    renderLoggedIn(window.CURRENT_USER.name);
  } else {
    renderLoggedOut();
  }
}

function renderLoggedIn(name) {
  const navAuth = document.getElementById('navAuth');
  if (!navAuth) return;
  navAuth.innerHTML = `
    <div class="nav-user">
      <i class="fas fa-user-circle"></i>
      <span>${name}</span>
    </div>
    <a href="/logout" class="btn btn-outline" style="padding:8px 16px;font-size:0.82rem;">
      <i class="fas fa-sign-out-alt"></i> Logout
    </a>`;
}

function renderLoggedOut() {
  const navAuth = document.getElementById('navAuth');
  if (!navAuth) return;
  navAuth.innerHTML = `
    <a href="/login" class="btn btn-outline" style="padding:8px 16px;font-size:0.82rem;">
      <i class="fas fa-sign-in-alt"></i> Login
    </a>
    <a href="/register" class="btn btn-primary" style="padding:8px 18px;font-size:0.82rem;">
      <i class="fas fa-user-plus"></i> Register
    </a>`;
}

// Modal-based login (from old hero)
function openAuthModal(tab = 'login') {
  openModal('authModal');
  switchTab(tab);
}

function switchTab(tab) {
  document.getElementById('loginForm').classList.toggle('hidden', tab !== 'login');
  document.getElementById('registerForm').classList.toggle('hidden', tab !== 'register');
  document.getElementById('loginTab').classList.toggle('active', tab === 'login');
  document.getElementById('registerTab').classList.toggle('active', tab === 'register');
}

async function doLogin() {
  const email    = document.getElementById('loginEmail').value.trim();
  const password = document.getElementById('loginPassword').value;
  const errDiv   = document.getElementById('loginError');
  errDiv.classList.add('hidden');

  if (!email || !password) {
    showError(errDiv, 'Please enter email and password.');
    return;
  }
  try {
    const res  = await fetch('/login', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ email, password }),
    });
    const data = await res.json();
    if (data.success) {
      closeModal('authModal');
      renderLoggedIn(data.name);
    } else {
      showError(errDiv, data.error || 'Invalid credentials.');
    }
  } catch {
    showError(errDiv, 'Server error. Please try again.');
  }
}

async function doRegister() {
  const name     = document.getElementById('regName').value.trim();
  const email    = document.getElementById('regEmail').value.trim();
  const phone    = document.getElementById('regPhone').value.trim();
  const password = document.getElementById('regPassword').value;
  const errDiv   = document.getElementById('regError');
  errDiv.classList.add('hidden');

  if (!name || !email || !password) {
    showError(errDiv, 'Name, email, and password are required.');
    return;
  }
  try {
    const res  = await fetch('/register', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ name, email, phone, password }),
    });
    const data = await res.json();
    if (data.success) {
      closeModal('authModal');
      renderLoggedIn(data.name);
    } else {
      showError(errDiv, data.error || 'Registration failed.');
    }
  } catch {
    showError(errDiv, 'Server error. Please try again.');
  }
}

function showError(div, msg) {
  div.textContent = msg;
  div.classList.remove('hidden');
}


// ══════════════════════════════════════════════
//  MODAL HELPERS
// ══════════════════════════════════════════════
function openModal(id) {
  document.getElementById(id).classList.add('active');
  document.body.style.overflow = 'hidden';
}
function closeModal(id) {
  document.getElementById(id).classList.remove('active');
  document.body.style.overflow = '';
}


// ══════════════════════════════════════════════
//  CONTACT FORM SUBMIT (demo)
// ══════════════════════════════════════════════
function submitContact(e) {
  e.preventDefault();
  const btn = e.target.querySelector('button');
  btn.innerHTML = '<i class="fas fa-check"></i> Message Sent!';
  btn.style.background = 'linear-gradient(135deg,#10b981,#059669)';
  btn.disabled = true;
  e.target.reset();
  setTimeout(() => {
    btn.innerHTML = '<i class="fas fa-paper-plane"></i> Send Message';
    btn.style.background = '';
    btn.disabled = false;
  }, 4000);
}


// ══════════════════════════════════════════════
//  CHATBOT CORE
// ══════════════════════════════════════════════
function toggleChat() {
  isChatOpen = !isChatOpen;
  const win  = document.getElementById('chatWindow');
  const btn  = document.getElementById('chatToggle');
  win.classList.toggle('open', isChatOpen);
  btn.classList.toggle('open', isChatOpen);
}

function openChat() {
  if (!isChatOpen) toggleChat();
}

// Scroll anchor handler
document.getElementById('openChatBtn')?.addEventListener('click', (e) => {
  e.preventDefault();
  openChat();
});

function sendWelcomeMessage() {
  setTimeout(() => {
    appendBotMsg("👋 Hi! I'm **MediBot**, your AI health assistant at **Multicare AI Hospital**.\n\nHow can I help you today? You can ask about:\n• Timings & departments\n• Booking appointments\n• Your symptoms\n• Emergency contact");
  }, 700);
}

async function sendMessage() {
  const input = document.getElementById('chatInput');
  const msg   = input.value.trim();
  if (!msg) return;

  appendUserMsg(msg);
  input.value = '';

  // 🔥 HANDLE BOOK FROM TYPING / VOICE
if (msg.toLowerCase().includes("book")) {

  // Close chatbot (optional)
  const chatWin = document.getElementById('chatWindow');
  const chatBtn = document.getElementById('chatToggle');
  chatWin.classList.remove('open');
  chatBtn.classList.remove('open');

  // Scroll to booking section
  document.getElementById('book').scrollIntoView({
    behavior: 'smooth',
    block: 'start'
  });

  return; // ❗ STOP API CALL
}

  // Show typing
  const typingEl = appendTyping();

  try {
    const res  = await fetch('/api/chat', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ message: msg, session_id: SESSION_ID }),
    });
    const data = await res.json();
    typingEl.remove();
    const reply = data.reply || 'Sorry, I could not understand. Please try again.';
    appendBotMsg(reply);
    if (ttsEnabled) speakText(reply);
  } catch {
    typingEl.remove();
    appendBotMsg('⚠️ Network error. Please check your connection.');
  }
}

function sendChip(msg) {

  // 🔥 IF BOOK CLICKED → GO TO BOOK SECTION
  if (msg.toLowerCase().includes("book")) {

    // Close chatbot (optional)
    const chatWin = document.getElementById('chatWindow');
    const chatBtn = document.getElementById('chatToggle');
    chatWin.classList.remove('open');
    chatBtn.classList.remove('open');

    // Scroll to booking form
    document.getElementById('book').scrollIntoView({
      behavior: 'smooth'
    });

    return; // ❗ STOP chatbot message
  }

  // Default behavior
  document.getElementById('chatInput').value = msg;
  sendMessage();
}

  
function appendUserMsg(msg) {
  const div = document.createElement('div');
  div.className = 'chat-msg user';
  div.textContent = msg;
  document.getElementById('chatMessages').appendChild(div);
  scrollChatDown();
}

function appendBotMsg(msg) {
  const div = document.createElement('div');
  div.className  = 'chat-msg bot';
  div.innerHTML  = formatBotMsg(msg);
  document.getElementById('chatMessages').appendChild(div);
  scrollChatDown();
  return div;
}

function appendTyping() {
  const div = document.createElement('div');
  div.className = 'chat-typing';
  div.innerHTML = '<span></span><span></span><span></span>';
  document.getElementById('chatMessages').appendChild(div);
  scrollChatDown();
  return div;
}

function formatBotMsg(text) {
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br/>')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" style="color:var(--primary);font-weight:600;">$1</a>');
}

function scrollChatDown() {
  const msgs = document.getElementById('chatMessages');
  if (msgs) msgs.scrollTop = msgs.scrollHeight;
}

function clearChat() {
  document.getElementById('chatMessages').innerHTML = '';
  sendWelcomeMessage();
}


// ══════════════════════════════════════════════
//  TEXT-TO-SPEECH (TTS)
// ══════════════════════════════════════════════
function toggleTTS() {
  ttsEnabled = !ttsEnabled;
  const btn = document.getElementById('ttsBtn');
  if (btn) {
    btn.style.color = ttsEnabled ? 'var(--accent)' : '';
    btn.title = ttsEnabled ? 'TTS ON – click to disable' : 'Enable Text to Speech';
  }
  if (!ttsEnabled && window.speechSynthesis) {
    window.speechSynthesis.cancel();
  }
}

function speakText(text) {
  if (!window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  // Strip markdown
  const clean = text.replace(/\*\*(.*?)\*\*/g, '$1').replace(/[•→]/g, '').replace(/\n/g, ' ');
  const utt   = new SpeechSynthesisUtterance(clean.substring(0, 500)); // limit length
  utt.rate  = 0.95;
  utt.pitch = 1.05;
  utt.lang  = 'en-IN';
  window.speechSynthesis.speak(utt);
}


// ══════════════════════════════════════════════
//  VOICE INPUT (Speech-to-Text)
// ══════════════════════════════════════════════
function initVoiceSupport() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    const micBtn = document.getElementById('micBtn');
    if (micBtn) {
      micBtn.title = 'Voice input not supported in this browser';
      micBtn.style.opacity = '0.4';
      micBtn.disabled = true;
    }
    return;
  }
  speechRecog            = new SpeechRecognition();
  speechRecog.lang       = 'en-IN';
  speechRecog.continuous = false;
  speechRecog.interimResults = false;

  speechRecog.onresult = (e) => {
    const transcript = e.results[0][0].transcript;
    document.getElementById('chatInput').value = transcript;
    stopVoiceInput();
    sendMessage();
  };

  speechRecog.onerror = (e) => {
    console.warn('Speech error:', e.error);
    stopVoiceInput();
    if (e.error === 'not-allowed') {
      appendBotMsg('🎤 Microphone permission denied. Please allow mic access in your browser settings.');
    }
  };

  speechRecog.onend = () => stopVoiceInput();
}

function toggleVoiceInput() {
  if (isListening) {
    stopVoiceInput();
  } else {
    startVoiceInput();
  }
}

function startVoiceInput() {
  if (!speechRecog) return;
  isListening = true;
  document.getElementById('micBtn').classList.add('active');
  document.getElementById('voiceStatus').classList.remove('hidden');
  document.getElementById('chatInput').placeholder = 'Listening...';
  try {
    speechRecog.start();
  } catch (e) {
    stopVoiceInput();
  }
}

function stopVoiceInput() {
  isListening = false;
  const micBtn = document.getElementById('micBtn');
  if (micBtn) micBtn.classList.remove('active');
  const vs = document.getElementById('voiceStatus');
  if (vs) vs.classList.add('hidden');
  const ci = document.getElementById('chatInput');
  if (ci) ci.placeholder = 'Type or speak your message...';
  try { speechRecog?.stop(); } catch {}
}


// ══════════════════════════════════════════════
//  WHATSAPP FLOAT BUTTON (bonus)
// ══════════════════════════════════════════════
// WhatsApp integration is available via the /whatsapp webhook (Twilio)
// Frontend direct link for demo:
window.openWhatsApp = function() {
  window.open('https://wa.me/918012345678?text=Hello+Multicare+AI+Hospital', '_blank');
};
