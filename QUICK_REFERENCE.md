# Quick Reference - Start Here

## 📚 Documentation Overview

This folder contains complete refactoring documentation for your biometric system:

| Document | Purpose | Audience |
|----------|---------|----------|
| **REFACTORING_PLAN.md** | High-level architecture strategy, 7-phase migration approach | Decision makers, architects |
| **IMPLEMENTATION_GUIDE.md** | Detailed code implementations, copy-paste ready | Developers |
| **ADVANCED_GUIDE.md** | Production patterns: logging, testing, deployment, monitoring | DevOps, senior developers |
| **QUICK_REFERENCE.md** (this file) | Start here - overview and common tasks | Everyone |

---

## 🎯 What You're Doing

**Current State:** Backend assumes single web portal (hardcoded CORS to localhost:5500)

**Target State:** Backend is standalone service that multiple clients can use (portal, banking app, mobile app, etc.)

**Key Architecture Change:**

```
BEFORE:                          AFTER:
Portal <-> Backend              Portal
                                   |
                                   |-- Backend (Service)
                                   |
                                   |-- Banking App
                                   |
                                   |-- Mobile App
                                   |
                                   └-- Admin Panel
```

---

## 🚀 Quick Start - 5 Steps to Get Started

### Step 1: Understand the Scope (15 min)
Read: **REFACTORING_PLAN.md**, Section "PHASE 1: BACKEND RESTRUCTURING" → "1.2 Database Schema Changes"

This will give you the big picture.

### Step 2: Prepare Your Database (30 min)
Follow: **IMPLEMENTATION_GUIDE.md** → "PHASE 1: DATABASE SCHEMA"

```bash
# In backend folder:
cd backend

# Create alembic migrations directory (if not exists)
alembic init alembic

# Copy the migration file from guide into: alembic/versions/001_add_client_model.py
# Then run:
alembic upgrade head
```

### Step 3: Update Core Files (60 min)
Follow: **IMPLEMENTATION_GUIDE.md** → "PHASE 1: CORE APPLICATION CHANGES"

These files MUST be updated in order:
1. `app/core/config.py` - Add client configuration
2. `app/core/security.py` - Add client token logic  
3. `app/db/models.py` - Add Client model
4. `app/api/dependencies/client.py` - NEW file for client auth

### Step 4: Create v1 API Routes (90 min)
Follow: **IMPLEMENTATION_GUIDE.md** → "PHASE 1: NEW v1 API ROUTES"

Create these new files:
- `app/api/v1/__init__.py`
- `app/api/v1/routes_auth.py`
- `app/api/v1/routes_verify.py`
- `app/api/v1/routes_admin.py`
- `app/api/v1/routes_health.py`

Update: `app/main.py` for new routing

### Step 5: Update Frontend (60 min)
Follow: **IMPLEMENTATION_GUIDE.md** → "PHASE 2: FRONTEND DECOUPLING"

Create these new files:
- `frontend/shared/api-client.js` - Generic HTTP client
- `frontend/portal/config.js` - Environment config
- `frontend/portal/js/app.js` - Main entry point

Update: `frontend/portal/js/auth.js` and `verify.js` to use new client

---

## 🔧 Implementation Order

**Don't get overwhelmed!** Follow this sequence:

### Week 1: Backend Database & Config
1. Add `Client` model to `app/db/models.py`
2. Run Alembic migration
3. Update `app/core/config.py`
4. Add client authentication dependency

### Week 2: Backend API Routes
5. Create `app/api/v1/` folder structure
6. Implement v1 routes (auth, verify, enroll, admin)
7. Test with Postman/curl
8. Verify old routes still work (backward compatibility)

### Week 3: Frontend Update
9. Create frontend API client abstraction
10. Update portal to use new client
11. Test portal with v1 API
12. Document changes

### Week 4: Testing & Docs
13. Write integration tests (see ADVANCED_GUIDE.md)
14. Create Docker setup
15. Document API endpoints
16. Plan migration for other clients

---

## 📋 File Creation Checklist

### Backend New Files
```
app/core/
  └── [ ] logging_config.py (from ADVANCED_GUIDE.md)
  
app/middleware/
  ├── [ ] request_context.py (from ADVANCED_GUIDE.md)
  └── [ ] exception_handler.py (from ADVANCED_GUIDE.md)

app/api/
  └── v1/
      ├── [ ] __init__.py
      ├── [ ] routes_auth.py
      ├── [ ] routes_verify.py
      ├── [ ] routes_enroll.py
      ├── [ ] routes_admin.py
      └── [ ] routes_health.py

app/api/dependencies/
  └── [ ] client.py

alembic/
  └── versions/
      └── [ ] 001_add_client_model.py

tests/
  ├── [ ] conftest.py
  ├── [ ] test_auth.py
  ├── [ ] test_verify.py
  └── integration/
      └── [ ] test_auth_flow.py

[ ] Dockerfile
[ ] .env.example
```

### Frontend New Files
```
shared/
  ├── [ ] api-client.js
  └── [ ] constants.js

portal/
  ├── [ ] config.js
  ├── [ ] .env.example
  └── js/
      └── [ ] app.js
```

---

## 🧪 Testing Your Changes

### After Backend Changes:
```bash
# Test health endpoint
curl http://localhost:8000/v1/health/

# Register a test client (admin action)
curl -X POST http://localhost:8000/v1/admin/clients \
  -H "Authorization: Bearer {admin_token}" \
  -H "X-API-Key: admin-key" \
  -d '{"name":"test-portal"}'

# Test authentication with new client
curl -X POST http://localhost:8000/v1/auth/verify \
  -H "X-API-Key: test-portal-key" \
  -d '{"username":"testuser","password":"password"}'
```

### After Frontend Changes:
```bash
# Test portal with new API client
# Open browser console and run:
const client = new BiometricServiceClient({
  API_BASE: "http://localhost:8000",
  API_KEY: "test-portal-key",
  VERSION: "v1",
});

// Test login
await client.authenticate("testuser", "password");
console.log(client.token);  // Should show JWT token
```

---

## 🔒 Security Checklist

Before going to production:

- [ ] Change `SECRET_KEY` in `.env`
- [ ] Use strong API keys (not "test-key")
- [ ] Enable rate limiting (see ADVANCED_GUIDE.md)
- [ ] Set `DEBUG=false` in production
- [ ] Use HTTPS (not HTTP)
- [ ] Add CORS whitelist (don't use `["*"]`)
- [ ] Implement request logging with correlation IDs
- [ ] Set up monitoring/alerting (see ADVANCED_GUIDE.md)
- [ ] Perform security audit (API keys, token handling)
- [ ] Test rate limiting and error handling

---

## 📊 Data Model Summary

### New Client Table
```sql
client
├── client_id (PK)
├── name (e.g., "portal", "banking-app")
├── api_key (unique identifier)
├── secret (for future HMAC)
├── scopes (e.g., "enroll,verify")
├── can_manage_users (boolean)
├── rate_limit_rpm (default 1000)
├── is_active (boolean)
└── created_at (timestamp)
```

### Updated User Table
```sql
user
├── ... existing fields ...
├── client_id (FK to client) -- NEW
└── username + client_id (unique constraint) -- NEW
```

### Updated AuditLog Table
```sql
audit_log
├── ... existing fields ...
├── client_id (FK to client) -- NEW
├── request_id (correlation ID) -- NEW
├── source (e.g., "portal", "banking-app") -- NEW
└── ip_address -- NEW
```

---

## 🔑 Key Concepts

### Client Registration (Admin Does This Once)
```
1. Admin calls: POST /admin/clients with app name
2. System generates: api_key, secret
3. Admin gives api_key to app developer
4. Developer stores in: .env or config
```

### Client Request Flow
```
1. Client sends request with: X-API-Key: {api_key}
2. Backend verifies: api_key exists and is active
3. On auth endpoint: Client gets JWT token
4. On verify endpoint: Client sends JWT in Authorization header
5. Backend verifies: Token belongs to this client
```

### Why This Matters
- **Portal can't see Banking App's users** (different client_id)
- **Different rate limits per app** (1000 rpm for portal, 100 rpm for banking)
- **Audit trail shows which app made requests** (client_id in logs)
- **Easy to revoke access** (set is_active = false)

---

## 🐛 Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| "Invalid API key" error | Make sure X-API-Key header is set and matches registered client |
| "Token client mismatch" | JWT token must be obtained via same client that makes verify request |
| "User not found" | Users are scoped to clients; user from portal won't exist in banking app |
| "CORS error" in browser | Check CORS_ALLOWED_ORIGINS in .env matches frontend URL |
| Old portal still works? | Good! v0 routes still exist for backward compatibility |
| Database migration fails | Ensure you have proper DB URL in .env and alembic.ini |

---

## 📈 Scaling Your System

After initial refactoring:

**For 2-3 Clients:**
- Current setup works fine
- Use Docker Compose for dev/staging
- PostgreSQL for production

**For 5+ Clients:**
- Consider: Rate limiting middleware improvement
- Use Redis for distributed rate limiting
- Scale backend horizontally (multiple instances)
- Load balancer in front
- Separate read/write databases

**For 100+ Clients:**
- Multi-tenant isolation at database level
- Client-specific configuration service
- Separate microservices per client (optional)
- Full Kubernetes deployment

---

## 📞 Support Resources

### Within This Project:
- **Architecture questions?** → Read REFACTORING_PLAN.md
- **Code implementation?** → Check IMPLEMENTATION_GUIDE.md
- **Production setup?** → See ADVANCED_GUIDE.md

### General FastAPI:
- FastAPI docs: https://fastapi.tiangolo.com/
- SQLAlchemy async: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html

### General Python:
- JWT tokens: https://pyjwt.readthedocs.io/
- Pydantic: https://docs.pydantic.dev/

---

## 🎓 Learning Path (Recommended)

1. **Read:** REFACTORING_PLAN.md (understand "why")
2. **Review:** IMPLEMENTATION_GUIDE.md code samples (understand "what")
3. **Implement:** Follow Step-by-step guide above (understand "how")
4. **Test:** Use test examples from ADVANCED_GUIDE.md
5. **Deploy:** Follow Docker/K8s examples from ADVANCED_GUIDE.md
6. **Maintain:** Set up logging and monitoring (from ADVANCED_GUIDE.md)

---

## ❓ FAQ

**Q: Do I need to change my existing portal?**
A: No initially - it can keep using v0 routes. Gradually migrate to v1 endpoints.

**Q: Can I support both old and new clients?**
A: Yes! v0 routes stay alongside v1. Clients can migrate at their own pace.

**Q: What if I don't want multiple clients now?**
A: Still do the refactoring! It makes your code cleaner and prepares for growth.

**Q: Should I use mono-repo or multiple repos?**
A: **Mono-repo recommended** for easier coordination. Each client can be in its own folder.

**Q: How do I handle different verification thresholds per client?**
A: See ADVANCED_GUIDE.md - create ClientSettings model that overrides defaults.

**Q: What about API versioning?**
A: Done! Use `/v1/` prefix. When you need v2, create `/v2/` routes alongside.

---

## 🎉 Next Steps

1. **Read** REFACTORING_PLAN.md (30 min)
2. **Pick a team member** to lead implementation
3. **Create dev branch** in git
4. **Start with Step 1** from "Quick Start" section above
5. **Ask questions** as you go (refer to docs)
6. **Test thoroughly** before staging
7. **Celebrate** when complete! 🚀

---

**Last Updated:** April 4, 2024
**Status:** Ready for Implementation

