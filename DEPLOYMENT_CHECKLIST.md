# Unity Enhancement Deployment Checklist

**Date**: December 17, 2025  
**Status**: Ready for Deployment

---

## ✅ Pre-Deployment Checklist

### 1. Database Migrations

```bash
cd backend
alembic upgrade head
```

**Expected Migration**: `a1b2c3d4e5f6_add_marketplace_and_dashboard_tables.py`

**Tables Created**:
- `marketplace_plugins`
- `plugin_reviews`
- `plugin_installations`
- `plugin_downloads`
- `dashboards`
- `dashboard_widgets`

**Columns Added**:
- `alert_rules.conditions_json` (for advanced alerting)

---

### 2. Dependencies

#### Backend
```bash
cd backend
pip install -r requirements.txt
```

**New Dependencies**:
- `numpy>=1.24.0` (for AI insights)

#### Frontend
```bash
cd frontend
npm install
```

**No new dependencies** (uses existing packages)

---

### 3. Environment Variables

Ensure these are set in `.env`:

```bash
# Redis (optional, for caching)
REDIS_URL=redis://localhost:6379/0

# Database
DATABASE_URL=postgresql://user:pass@host:5432/db

# Other existing variables...
```

---

### 4. Service Restart

```bash
# Docker Compose
docker-compose restart backend frontend

# Or manual
cd backend && uvicorn app.main:app --reload
cd frontend && npm run dev
```

---

## 🧪 Testing Checklist

### WebSocket
- [ ] Connect to `/ws/metrics`
- [ ] Test subscription message
- [ ] Verify real-time updates
- [ ] Test reconnection

### Marketplace
- [ ] List plugins: `GET /api/v1/marketplace/plugins`
- [ ] Get categories: `GET /api/v1/marketplace/categories`
- [ ] Get tags: `GET /api/v1/marketplace/tags`
- [ ] Test plugin installation (when implemented)

### Dashboard Builder
- [ ] Create dashboard: `POST /api/v1/dashboards`
- [ ] List dashboards: `GET /api/v1/dashboards`
- [ ] Add widget: `POST /api/v1/dashboards/{id}/widgets`
- [ ] Get widget templates: `GET /api/v1/dashboards/templates/widgets`

### AI Insights
- [ ] Detect anomalies: `GET /api/v1/ai/insights/anomalies?plugin_id=system_info&metric_name=cpu_percent`
- [ ] Forecast metric: `GET /api/v1/ai/insights/forecast?plugin_id=system_info&metric_name=cpu_percent`
- [ ] Get recommendations: `GET /api/v1/ai/insights/recommendations?plugin_id=system_info&metric_name=cpu_percent`

### Advanced Alerting
- [ ] Verify `AdvancedAlertEvaluator` can be imported
- [ ] Verify `AlertCorrelator` can be imported
- [ ] Verify `AutomatedRemediation` can be imported

### Performance
- [ ] Verify cache middleware is active
- [ ] Test API response caching
- [ ] Check frontend bundle size (should be optimized)

---

## 🐛 Troubleshooting

### Migration Fails
- Check database connection
- Verify Alembic version
- Check for conflicting migrations

### WebSocket Not Connecting
- Check CORS settings
- Verify WebSocket endpoint is accessible
- Check browser console for errors

### Marketplace Empty
- This is expected - marketplace starts empty
- Add plugins via API or populate manually

### AI Insights Return Errors
- Ensure numpy is installed
- Check that metrics exist for the plugin/metric
- Verify plugin_id and metric_name are correct

---

## 📊 Post-Deployment Verification

1. **Health Check**
   ```bash
   curl http://localhost:8000/health
   ```

2. **API Docs**
   - Visit: http://localhost:8000/docs
   - Verify all new endpoints are listed

3. **Frontend**
   - Visit: http://localhost:3000
   - Check for new routes:
     - `/marketplace`
     - `/dashboards`
   - Verify WebSocket connection indicator on dashboard

4. **Database**
   ```sql
   -- Verify tables exist
   SELECT table_name FROM information_schema.tables 
   WHERE table_schema = 'public' 
   AND table_name IN (
     'marketplace_plugins',
     'dashboards',
     'plugin_reviews'
   );
   ```

---

## 🎯 Success Criteria

- ✅ All migrations run successfully
- ✅ All API endpoints respond
- ✅ WebSocket connects and receives messages
- ✅ Frontend loads without errors
- ✅ No console errors in browser
- ✅ Database tables created correctly

---

## 📝 Notes

- All enhancements are backward compatible
- Existing functionality remains unchanged
- New features are opt-in (marketplace, dashboards, etc.)
- WebSocket enhancements work alongside existing polling

---

**Ready to Deploy!** 🚀

