# Virtual Family Bank - Frontend

React + TypeScript + Vite frontend application for the Virtual Family Bank.

## Quick Start

```bash
# Install dependencies
npm install

# Copy environment template
cp .env.example .env

# Edit .env with your AWS configuration

# Start development server
npm run dev
```

## Tech Stack

- React 19 + TypeScript
- Vite (build tool)
- Tailwind CSS
- React Router
- AWS Amplify (Cognito Auth)
- Axios (API client)

## Project Structure

```
src/
├── components/      # Reusable UI components
├── config/          # AWS Amplify configuration
├── context/         # React context (Auth)
├── pages/           # Page components
├── services/        # API service layer
├── types/           # TypeScript definitions
├── hooks/           # Custom hooks
└── utils/           # Utilities
```

## Features Implemented

✅ Authentication with AWS Cognito
✅ Protected routes & role-based access
✅ API service layer with auth tokens
✅ Parent & Child dashboards (basic)
✅ Tailwind CSS styling

## Environment Variables

Create `.env` file:

```env
VITE_API_ENDPOINT=https://your-api.execute-api.us-east-1.amazonaws.com/dev
VITE_AWS_REGION=us-east-1
VITE_USER_POOL_ID=us-east-1_xxxxxxxxx
VITE_USER_POOL_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
VITE_COGNITO_DOMAIN=https://familybank-dev-xxx.auth.us-east-1.amazoncognito.com
```

## Development

```bash
npm run dev      # Start dev server
npm run build    # Build for production
npm run preview  # Preview production build
npm run lint     # Run ESLint
```

## API Integration

All API calls go through `src/services/api.ts` which:
- Automatically adds JWT tokens
- Handles errors consistently
- Provides typed methods

```typescript
import { apiService } from './services/api';

// Example usage
const children = await apiService.getChildren();
const user = await apiService.getUser();
```

## Authentication Flow

1. User visits `/` → Login Page
2. Click "Sign In" → Cognito Hosted UI
3. OAuth callback → `/callback`
4. Fetch user profile from API
5. Route to dashboard based on role

## Next Steps

See [TASKS.md](../TASKS.md) for implementation roadmap.

Priority:
1. Parent dashboard - list children, adjust balances
2. Child dashboard - transaction history
3. Forms & validation
4. Loading states & error handling

## Troubleshooting

**Authentication not working?**
- Check `.env` has correct Cognito settings
- Verify Cognito callback URLs include `http://localhost:5173/callback`

**API calls failing?**
- Verify `VITE_API_ENDPOINT` is correct
- Check backend is deployed
- Look at browser Network tab for errors

##Resources

- [Vite](https://vite.dev/)
- [React Router](https://reactrouter.com/)
- [Tailwind CSS](https://tailwindcss.com/)
- [AWS Amplify Auth](https://docs.amplify.aws/react/build-a-backend/auth/)
