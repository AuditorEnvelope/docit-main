# 🚀 Multi-Org Support - Quick Start Guide

## ✅ WHAT'S BEEN IMPLEMENTED

### Backend Changes (DONE ✅)

1. **GitHub App Token Support** - `src/smart_processor.py` (lines 52-60)
   - Automatically gets app token if installation_id available
   - Falls back to env GITHUB_TOKEN
   - No breaking changes

2. **Webhook Registration Endpoint** - `src/main.py` (lines 433-469)
   - `POST /webhook/register` - Register org for multi-org support
   - Stores org_id + user_id mapping
   - Returns webhook URL for user to configure

3. **Database Migration** - `migrations/003_org_registrations.sql`
   - Creates `org_registrations` table
   - Tracks which user registered which org

---

## 🔧 SETUP STEPS

### Step 1: Run Database Migration
```bash
psql -U postgres -d lekhak_ai < migrations/003_org_registrations.sql
```

Verify:
```bash
psql -U postgres -d lekhak_ai -c "\dt org_registrations"
```

### Step 2: Restart Backend
```bash
python src/main.py
```

Backend is now ready for multi-org!

---

## 🎨 FRONTEND IMPLEMENTATION (NEEDED)

### What Needs to Be Built:

1. **ConnectOrganizationModal Component**
   - Input field for organization name
   - Submit button
   - Loading state
   - Success/error messages

2. **Dashboard Button**
   - "🔗 Connect Organization" button
   - Opens modal on click
   - Shows registered orgs

### Quick Implementation:

```typescript
// In pustak/src/components/ConnectOrganizationModal.tsx

import { useState } from 'react';

export function ConnectOrganizationModal({ isOpen, onClose, onSuccess }) {
  const [orgId, setOrgId] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleRegister = async () => {
    setLoading(true);
    setError('');
    
    try {
      const token = localStorage.getItem('pustak_access_token');
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_URL}/webhook/register?org_id=${orgId}`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );

      const data = await response.json();
      
      if (response.ok) {
        alert(`✅ Organization registered!\n\nWebhook URL: ${data.webhook_url}`);
        onSuccess();
        onClose();
      } else {
        setError(data.detail || 'Failed to register');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal">
      <div className="modal-content">
        <h2>🔗 Connect Organization</h2>
        
        <input
          type="text"
          placeholder="Organization name (e.g., Testing-Org-For-Pustak)"
          value={orgId}
          onChange={(e) => setOrgId(e.target.value)}
        />
        
        {error && <div className="error">{error}</div>}
        
        <button
          onClick={handleRegister}
          disabled={loading || !orgId}
        >
          {loading ? 'Registering...' : 'Register Organization'}
        </button>
        
        <button onClick={onClose}>Cancel</button>
      </div>
    </div>
  );
}
```

### Add to Dashboard:

```typescript
// In pustak/src/app/dashboard/page.tsx

import { ConnectOrganizationModal } from '@/components/ConnectOrganizationModal';
import { useState } from 'react';

export default function DashboardPage() {
  const [showModal, setShowModal] = useState(false);

  return (
    <div>
      {/* Existing dashboard content */}
      
      <button 
        onClick={() => setShowModal(true)}
        className="btn btn-primary"
      >
        🔗 Connect Organization
      </button>

      <ConnectOrganizationModal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        onSuccess={() => {
          // Refresh repos list
          window.location.reload();
        }}
      />
    </div>
  );
}
```

---

## 🧪 TESTING

### Test the Flow:

1. **Start backend:**
   ```bash
   python src/main.py
   ```

2. **Start frontend:**
   ```bash
   cd pustak
   npm run dev
   ```

3. **Test registration:**
   - Go to dashboard
   - Click "🔗 Connect Organization"
   - Enter org name: `Testing-Org-For-Pustak`
   - Click "Register Organization"
   - Should see: `✅ Organization registered!`

4. **Verify in database:**
   ```bash
   psql -U postgres -d lekhak_ai -c "SELECT * FROM org_registrations;"
   ```

5. **Push code to test org:**
   - Make a commit to `Testing-Org-For-Pustak/Testing`
   - Webhook should trigger
   - Docs should generate

---

## 🎯 HOW IT WORKS

```
1. User registers org via modal
   ↓
2. Backend stores in org_registrations table
   ↓
3. GitHub sends webhook to /webhook
   ↓
4. Webhook handler processes event
   ↓
5. Event stored in commit_events
   ↓
6. Event consumer picks it up
   ↓
7. Gets GitHub App token (if available)
   ↓
8. Generates docs and pushes
   ↓
✅ Docs appear in GitHub!
```

---

## 📊 CURRENT STATUS

| Component | Status | Notes |
|-----------|--------|-------|
| GitHub App Support | ✅ Done | smart_processor.py |
| Webhook Registration | ✅ Done | main.py endpoint |
| Database | ✅ Done | Migration ready |
| Frontend Modal | ⏳ Needed | Simple component |
| Dashboard Button | ⏳ Needed | One button |
| Testing | ⏳ Needed | Manual testing |

---

## 🚀 NEXT STEPS

1. **Create ConnectOrganizationModal component** (10 min)
2. **Add button to dashboard** (5 min)
3. **Run database migration** (2 min)
4. **Test end-to-end** (10 min)

**Total time: ~30 minutes**

---

## ❓ QUESTIONS?

- **How does GitHub App token work?** - Automatically generated from app private key
- **Do users need to install the app?** - Yes, must be installed in their org first
- **What if app not installed?** - Falls back to env GITHUB_TOKEN
- **Can users register multiple orgs?** - Yes! Each org can be registered separately
- **Is it backward compatible?** - Yes! Single-org setup still works

---

## 🎉 READY TO GO!

All backend code is done. Just need to:
1. Create the frontend modal
2. Add button to dashboard
3. Run migration
4. Test!

**Let's build it!** 🚀
