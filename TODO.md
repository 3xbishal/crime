# Crime Map Project - Implementation Plan

## Part 1: Custom Admin Panel (NOT Django built-in admin)
- [ ] Custom admin authentication (login/logout views, admin_required decorator)
- [ ] CSV upload with deduplication (update existing records instead of duplicating)
- [ ] Admin dashboard with statistics
- [ ] Data management views (list, view, edit, delete records)
- [ ] Data export (CSV download)
- [ ] Admin templates

## Part 2: Visitor Features
- [ ] Interactive crime map (Google Maps + Leaflet fallback)
- [ ] Crime prediction feature (pure Python KNN-based prediction)
- [ ] Prediction form and results display
- [ ] Map with prediction overlay

## Part 3: Infrastructure
- [ ] Update models (add unique constraints for deduplication)
- [ ] Update forms (admin forms, prediction form)
- [ ] Update views (admin views, prediction views)
- [ ] Update URLs
- [ ] Update settings (static files, auth)
- [ ] Create all templates
- [ ] Run migrations and test
