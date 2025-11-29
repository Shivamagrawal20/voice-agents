# 🎲 How to Play the Voice Game Master (D&D-Style Adventure)

Complete step-by-step guide to set up and play your interactive voice adventure game.

---

## 📋 Prerequisites

Before you start, make sure you have:

1. **Python 3.9+** with [uv](https://docs.astral.sh/uv/) package manager
2. **Node.js 18+** with [pnpm](https://pnpm.io/)
3. **LiveKit Server** installed:
   ```bash
   brew install livekit
   ```
4. **API Keys** for:
   - LiveKit (URL, API Key, API Secret)
   - Murf AI (for TTS)
   - Google (for Gemini LLM)
   - Deepgram (for STT)

---

## 🚀 Step 1: Environment Setup

### 1.1 Backend Environment

```bash
cd backend

# Copy the example environment file
cp .env.example .env.local
```

Edit `backend/.env.local` and add your credentials:

```env
# LiveKit Configuration
LIVEKIT_URL=wss://your-livekit-server.com
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret

# Murf AI (for TTS)
MURF_API_KEY=your-murf-api-key

# Google (for Gemini LLM)
GOOGLE_API_KEY=your-google-api-key

# Deepgram (for STT)
DEEPGRAM_API_KEY=your-deepgram-api-key
```

**OR** if using LiveKit Cloud, auto-populate credentials:

```bash
lk cloud auth
lk app env -w -d .env.local
```

### 1.2 Frontend Environment

```bash
cd frontend

# Copy the example environment file
cp .env.example .env.local
```

Edit `frontend/.env.local` and add the same LiveKit credentials:

```env
LIVEKIT_URL=wss://your-livekit-server.com
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret
```

---

## 📦 Step 2: Install Dependencies

### 2.1 Backend Dependencies

```bash
cd backend

# Install Python dependencies
uv sync

# Download required models (VAD, turn detector, etc.)
uv run python src/agent.py download-files
```

### 2.2 Frontend Dependencies

```bash
cd frontend

# Install Node.js dependencies
pnpm install
```

---

## 🎮 Step 3: Start the Game

You have **two options** to start everything:

### Option A: Use the Convenience Script (Easiest)

From the root directory:

```bash
# Make the script executable (first time only)
chmod +x start_app.sh

# Start everything
./start_app.sh
```

This will start:

- ✅ LiveKit Server (in dev mode)
- ✅ Backend Game Master Agent
- ✅ Frontend Web App

### Option B: Run Services Manually (3 Terminal Windows)

**Terminal 1 - LiveKit Server:**

```bash
livekit-server --dev
```

**Terminal 2 - Backend Agent:**

```bash
cd backend
uv run python src/agent.py dev
```

**Terminal 3 - Frontend:**

```bash
cd frontend
pnpm dev
```

---

## 🌐 Step 4: Open the Game

1. Open your browser and go to: **http://localhost:3000**

2. You should see the **Welcome Screen** with:
   - "Voice Game Master" title
   - "D&D-Style Adventure" subtitle
   - "Begin Adventure" button

---

## 🎯 Step 5: How to Play

### 5.1 Starting Your Adventure

1. Click the **"Begin Adventure"** button
2. Allow microphone access when prompted
3. Wait for the Game Master's opening greeting
4. The GM will describe your starting location and situation

### 5.2 Playing the Game

**Speak your actions naturally!** Here are examples:

#### Exploration Actions:

- "I look around"
- "I examine the door"
- "I search the room"
- "What do I see?"

#### Movement Actions:

- "I go north"
- "I walk down the path"
- "I enter the cave"
- "I climb the stairs"

#### Interaction Actions:

- "I talk to the merchant"
- "I pick up the sword"
- "I open the chest"
- "I read the scroll"

#### Combat Actions:

- "I attack the goblin"
- "I cast a fireball"
- "I dodge the attack"
- "I use my sword"

#### Character Management:

- "What's in my inventory?"
- "How much health do I have?"
- "What are my stats?"
- "Show me my character sheet"

### 5.3 Game Features

**The Game Master will:**

- ✅ Describe scenes with vivid details
- ✅ Respond to your actions
- ✅ Track your inventory and stats
- ✅ Remember NPCs and locations
- ✅ Create challenges and obstacles
- ✅ Roll dice for skill checks
- ✅ Guide you through an 8-15 turn adventure

**You can:**

- ✅ Speak naturally (no special commands needed)
- ✅ Ask questions about your character
- ✅ Make any action you can think of
- ✅ Restart the adventure anytime

---

## 🎲 Step 6: Game Controls

### Control Bar Features:

1. **🎤 Microphone Toggle** - Turn your mic on/off
2. **📹 Camera Toggle** - Enable/disable camera (optional)
3. **💬 Chat Toggle** - View the conversation transcript
4. **🔄 Restart Button** - Start a fresh adventure
5. **📞 End Call** - Disconnect from the game

### Using the Restart Button:

- Click the **🔄 button** in the control bar
- The Game Master will start a completely new adventure
- Your previous game state will be cleared

---

## 🎨 Step 7: Understanding the Game

### Game Structure:

A typical adventure lasts **8-15 exchanges**:

- **Turns 1-3**: Introduction and scene setting
- **Turns 4-8**: Rising action, obstacles, choices
- **Turns 9-12**: Climax, major challenge or discovery
- **Turns 13-15**: Resolution or cliffhanger ending

### World State Tracking:

The Game Master tracks:

- **Your Character**: HP, attributes (strength, intelligence, dexterity, luck), inventory
- **NPCs**: Characters you meet, their attitudes toward you
- **Locations**: Places you've visited, paths between locations
- **Events**: Important things that have happened
- **Quests**: Active and completed objectives

### Dice Rolls:

When you attempt risky actions, the GM will:

- Roll dice (usually a d20)
- Apply modifiers based on your attributes
- Determine outcomes: Critical Success, Success, Partial Success, or Failure
- Describe the results dramatically

---

## 🐛 Troubleshooting

### Problem: "Cannot connect to LiveKit"

**Solution:**

- Make sure LiveKit server is running (`livekit-server --dev`)
- Check your `LIVEKIT_URL` in `.env.local` files
- Verify your API keys are correct

### Problem: "Microphone not working"

**Solution:**

- Check browser permissions (allow microphone access)
- Make sure your mic is not muted
- Check the microphone toggle in the control bar

### Problem: "Agent not responding"

**Solution:**

- Check that the backend agent is running (`uv run python src/agent.py dev`)
- Look for errors in the backend terminal
- Verify all API keys are set correctly

### Problem: "No audio from Game Master"

**Solution:**

- Check your browser's audio settings
- Make sure your speakers/headphones are working
- Verify Murf API key is correct in `backend/.env.local`

### Problem: "Game state not saving"

**Solution:**

- Check that `shared-data/` directory exists
- Verify write permissions for the directory
- Check backend logs for save errors

---

## 🎮 Example Game Session

Here's what a typical session might look like:

**GM:** "Welcome, adventurer, to the world of Classic Fantasy. You find yourself in a misty forest clearing. Ancient trees tower overhead, and strange sounds echo from the shadows. A worn path leads deeper into the woods, while another trail seems to head toward distant mountains. The story begins now. What do you do?"

**You:** "I look around to see what's in the clearing."

**GM:** "As you scan the clearing, you notice a weathered stone marker partially covered in moss. Strange runes are carved into its surface, glowing faintly in the dim light. To your left, you spot what looks like a small leather pouch half-hidden under a fallen log. The forest around you seems to be watching, waiting. What do you do?"

**You:** "I pick up the pouch and examine the stone marker."

**GM:** "You carefully retrieve the pouch - it contains three gold coins and a small crystal that pulses with a soft blue light. As you approach the stone marker, the runes begin to glow brighter, and you hear a whisper on the wind: 'The path of courage leads to treasure, but the path of wisdom reveals truth.' What do you do?"

...and so on!

---

## 🎯 Tips for Best Experience

1. **Speak Clearly**: Enunciate your words for better speech recognition
2. **Be Specific**: Instead of "I go", say "I walk north" or "I enter the cave"
3. **Ask Questions**: The GM can tell you about your stats, inventory, or the world
4. **Be Creative**: Try unexpected actions - the GM will adapt!
5. **Use Natural Language**: No need for special commands, just talk normally
6. **Check Your Stats**: Ask "What's my health?" or "What do I have?" anytime

---

## 🔄 Changing the Universe

Want to play in a different setting? Edit `backend/src/agent.py`:

Find this line (around line 670):

```python
game_master = GameMasterAgent(universe="fantasy")
```

Change to:

- `universe="fantasy"` - Classic fantasy (dragons, magic, kingdoms)
- `universe="sci_fi"` - Space opera (starships, aliens, cyberpunk)
- `universe="post_apocalypse"` - Post-apocalyptic survival (wastelands, scavenging)

Then restart the backend agent.

---

## 📝 Next Steps

1. **Record Your Session**: Use screen recording to capture your adventure
2. **Share on LinkedIn**: Post about your Day 8 completion with hashtags:
   - `#MurfAIVoiceAgentsChallenge`
   - `#10DaysofAIVoiceAgents`
   - Tag `@Murf AI`
3. **Experiment**: Try different actions, explore the world state, test the dice rolls
4. **Customize**: Modify the system prompts, add new universes, or create custom NPCs

---

## 🎉 You're Ready!

Everything is set up! Just:

1. Start the services
2. Open http://localhost:3000
3. Click "Begin Adventure"
4. Start speaking your actions!

**Have fun and may your dice rolls be high!** 🎲✨
