# Frontend: the recruiter's screen

Vite + React + TypeScript. No UI library: plain CSS tokens in `src/index.css`.

```bash
npm install
VITE_API_URL=http://localhost:8000 npm run dev   # http://localhost:5173
npm test                                        # Vitest, no API needed
npm run build                                   # static files in dist/, deployed to Vercel
```

Screens (hash routes): `#/` candidates, `#/c/:id` review, `#/add` add a reply, `#/role` role setup.
If the API has `DEMO_ACCESS_CODE` set, the app asks for the code once and keeps it in localStorage.
