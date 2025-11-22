#!/bin/bash

# Create .env.local files for backend and frontend

echo "Creating environment files..."

# Backend .env.local
cat > backend/.env.local << 'ENVEOF'
# LiveKit Configuration - For local development
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret

# API Keys - Replace with your actual keys
MURF_API_KEY=your_murf_api_key_here
GOOGLE_API_KEY=your_google_api_key_here
DEEPGRAM_API_KEY=your_deepgram_api_key_here
ENVEOF

echo "✓ Created backend/.env.local"

# Frontend .env.local
cat > frontend/.env.local << 'ENVEOF'
# LiveKit Configuration - For local development
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret
ENVEOF

echo "✓ Created frontend/.env.local"
echo ""
echo "⚠️  IMPORTANT: Edit backend/.env.local and add your actual API keys:"
echo "   - MURF_API_KEY (from https://murf.ai/api)"
echo "   - GOOGLE_API_KEY (from https://aistudio.google.com/app/apikey)"
echo "   - DEEPGRAM_API_KEY (from https://console.deepgram.com/)"
