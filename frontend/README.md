# Deep MTG Frontend

## Development Setup

### Prerequisites
- Docker and Docker Compose installed
- Google OAuth credentials (Client ID and Secret)

### Environment Variables

1. Copy the example environment file:
```bash
cp frontend/.env.example frontend/.env
```

2. Edit `frontend/.env` and add your credentials:
- `GOOGLE_CLIENT_ID`: Your Google OAuth Client ID
- `GOOGLE_CLIENT_SECRET`: Your Google OAuth Client Secret
- `NEXTAUTH_SECRET`: A random secret string (at least 32 characters)
- `NEXTAUTH_URL`: Should be `http://localhost:3000` for local dev
- `BACKEND_MOCK`: Set to `true` to use mock API, `false` to connect to Django backend

### Running the Application

1. Start all services (backend, frontend, and proxy):
```bash
docker compose up
```

2. Open your browser and navigate to:
```
http://localhost:3000
```

The reverse proxy (Caddy) handles routing:
- `/` → Next.js frontend
- `/api/auth/*` → NextAuth (Next.js)
- `/api/*` → Django backend (or mock in Next.js if BACKEND_MOCK=true)

### Mock Mode

When `BACKEND_MOCK=true`, the frontend uses in-memory mock data for development without requiring the Django backend to be fully implemented. The mock simulates:
- Deck generation jobs with progress tracking
- Job status polling
- Deck retrieval with sample card data

### Production Build

To build for production:
```bash
cd frontend
npm run build
npm run start
```

### Tech Stack

- **Next.js 16** with App Router
- **React 19**
- **TypeScript** (strict mode)
- **Tailwind CSS** for styling
- **shadcn/ui** for UI components
- **NextAuth** for Google OAuth authentication
- **Caddy** as reverse proxy in development

### Project Structure

```
frontend/
├── app/
│   ├── api/              # API route handlers (mock mode)
│   ├── dashboard/        # Dashboard page (protected)
│   ├── decks/           # Deck view pages (protected)
│   ├── login/           # Login page
│   ├── layout.tsx       # Root layout
│   └── globals.css      # Global styles
├── components/
│   └── ui/              # shadcn/ui components
├── lib/
│   ├── auth.ts          # NextAuth configuration
│   └── utils.ts         # Utility functions
├── middleware.ts        # Route protection middleware
└── package.json
```

### Features

1. **Authentication**: Google OAuth login with NextAuth
2. **Deck Generation**: Prompt-based AI deck creation with real-time progress
3. **Deck Viewing**: Display generated decks with card lists
4. **Protected Routes**: Automatic redirect to login for unauthenticated users

### Development Notes

- Frontend runs on internal port 3001
- Proxy exposes port 3000 to host
- Hot reload is enabled via volume mounts
- All API calls are same-origin to avoid CORS issues
