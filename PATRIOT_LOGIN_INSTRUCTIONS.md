# 🔐 Patriot Login Access - OmniReach AI

## ✅ Account Created Successfully

**Account Details:**
- **Email:** patriot@liquidsmarts.com
- **Name:** Patriot
- **Role:** Admin (Full Access)
- **Session Expires:** 30 days from creation
- **User ID:** 9615cda0-11b0-444b-9351-064ab65bd2b6

---

## 🚀 OPTION 1: Quick Access Page (EASIEST)

Simply navigate to:

```
http://localhost:3000/patriot-access.html
```

OR if accessing via external URL:

```
YOUR_APP_URL/patriot-access.html
```

Click the "🔐 Login as patriot@liquidsmarts.com" button and you'll be automatically logged in!

---

## 🔧 OPTION 2: Manual Login (Browser Console)

1. Open your browser and go to: `http://localhost:3000`
2. Press **F12** to open Developer Tools
3. Go to the **Console** tab
4. Paste and run this code:

```javascript
localStorage.setItem('session_token', 'session_7f878ed4ce2a4dbea35013aaefc11a55');
localStorage.setItem('user', JSON.stringify({
    id: '9615cda0-11b0-444b-9351-064ab65bd2b6',
    email: 'patriot@liquidsmarts.com',
    name: 'Patriot',
    role: 'admin'
}));
window.location.href = '/dashboard';
```

5. Press Enter - you'll be redirected to the dashboard!

---

## 📋 Session Token

Your permanent session token (valid for 30 days):
```
session_7f878ed4ce2a4dbea35013aaefc11a55
```

---

## 🎯 What You Can Test Now

### Phase 1 Features:
1. ✅ **AI Agent Tab** - First tab in Campaign Builder
2. ✅ **Product Info Upload** - Upload PDF/DOCX for AI auto-fill
3. ✅ **Lead Limit** - Set max leads per campaign
4. ✅ **Campaign Steps** - 3-step message sequences

### Task 1: AI Auto-Fill Product Info
1. Go to **Campaign Builder** → **📦 Product Info** tab
2. Upload a PDF/DOCX product document
3. Watch AI extract and auto-fill all fields:
   - Product Name
   - Summary
   - Key Differentiators
   - Call-to-Action
   - Main Features
4. Review and save!

### Task 2: Enhanced AI Message Generation
1. Go to **Campaign Builder** → **🪜 Message Steps** tab
2. For each step, upload a best practices document (PDF/DOCX)
3. Navigate to **Leads** tab
4. Generate AI message for a lead
5. Check AI scores: clarity, personalization, relevance
6. Review AI reasoning

---

## 🛠️ Troubleshooting

**If login doesn't work:**
1. Clear browser cache and localStorage
2. Try incognito/private mode
3. Use the quick access page: `/patriot-access.html`

**Need to reset session:**
Run in browser console:
```javascript
localStorage.clear();
window.location.href = '/patriot-access.html';
```

---

## 📞 Support

If you encounter any issues:
- Check backend logs: `tail -f /var/log/supervisor/backend.err.log`
- Check frontend logs: `tail -f /var/log/supervisor/frontend.out.log`
- Services status: `sudo supervisorctl status`

---

**Happy Testing! 🚀**
