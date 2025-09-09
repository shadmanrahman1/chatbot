# Railway Deployment Status
This file is to track Railway deployments.

## Version History
- v1.0: Initial deployment
- v2.0: Added seeding endpoints
- v2.1: Force deployment with Procfile change
- v2.2: Added deployment tracking file

Current deployment should include:
- /seed endpoint (POST)
- /health endpoint with seeding (GET/POST with ?seed=true or {"seed": true})
- Version 2.1 message in home endpoint
