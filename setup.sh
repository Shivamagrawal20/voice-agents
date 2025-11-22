#!/bin/bash

# Setup script for Day 1 - Voice Agent Challenge
# This script helps set up the environment files

set -e

echo "🚀 Setting up Voice Agent Challenge - Day 1"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env.local files exist, if not create from .env.example
if [ ! -f "backend/.env.local" ]; then
    echo "📝 Creating backend/.env.local from template..."
    cp backend/.env.example backend/.env.local
    echo -e "${GREEN}✓${NC} Created backend/.env.local"
    echo -e "${YELLOW}⚠${NC}  Please edit backend/.env.local and add your API keys!"
else
    echo -e "${GREEN}✓${NC} backend/.env.local already exists"
fi

if [ ! -f "frontend/.env.local" ]; then
    echo "📝 Creating frontend/.env.local from template..."
    cp frontend/.env.example frontend/.env.local
    echo -e "${GREEN}✓${NC} Created frontend/.env.local"
    echo -e "${YELLOW}⚠${NC}  Please edit frontend/.env.local and add your LiveKit credentials!"
else
    echo -e "${GREEN}✓${NC} frontend/.env.local already exists"
fi

echo ""
echo "📋 Next steps:"
echo "1. Edit backend/.env.local and add your API keys:"
echo "   - LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET"
echo "   - MURF_API_KEY (from https://murf.ai/api)"
echo "   - GOOGLE_API_KEY (from https://aistudio.google.com/app/apikey)"
echo "   - DEEPGRAM_API_KEY (from https://console.deepgram.com/)"
echo ""
echo "2. Edit frontend/.env.local and add your LiveKit credentials"
echo "   (should match backend/.env.local)"
echo ""
echo "3. Install dependencies:"
echo "   cd backend && uv sync"
echo "   cd frontend && pnpm install"
echo ""
echo "4. Download models:"
echo "   cd backend && uv run python src/agent.py download-files"
echo ""
echo "5. Run the app:"
echo "   ./start_app.sh"
echo ""
echo "📖 See SETUP_GUIDE.md for detailed instructions!"

