# MOIL Mining Intelligence – frontend
npm install && cp .env.example .env && npm run dev   (http://localhost:5173)
Set VITE_USE_MOCK=false and VITE_API_BASE_URL to use a real backend; the service layer falls back to mock data if it is unreachable.
Login accepts any email and a 6+ character password; pick a demo role to see role-based navigation.
