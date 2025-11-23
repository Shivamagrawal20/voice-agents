# Day 2 Setup Status ✅

## ✅ Completed Implementation

### 1. **Barista Persona Created**
   - ✅ Transformed the generic assistant into a friendly coffee shop barista
   - ✅ Updated agent instructions with barista personality and ordering flow
   - ✅ Agent greets customers warmly and guides them through ordering

### 2. **Order State Management**
   - ✅ Implemented order state object with all required fields:
     - `drinkType`: Type of drink (latte, cappuccino, espresso, etc.)
     - `size`: Size of drink (small, medium, large, etc.)
     - `milk`: Type of milk (whole, almond, oat, etc.)
     - `extras`: Array of extras (whipped cream, caramel, etc.)
     - `name`: Customer's name for the order

### 3. **Order Management Tools**
   - ✅ `update_order_field`: Updates individual order fields as customer provides information
   - ✅ `get_order_status`: Checks what information is still needed
   - ✅ `save_order`: Saves completed orders to JSON files in `backend/orders/` directory

### 4. **Order Persistence**
   - ✅ Orders are saved to JSON files with timestamps
   - ✅ File naming format: `order_YYYYMMDD_HHMMSS_CustomerName.json`
   - ✅ Each order includes all fields plus timestamp
   - ✅ Orders directory is automatically created

## 🎯 How It Works

### Order Flow:
1. **Greeting**: Barista greets the customer warmly
2. **Collecting Information**: Barista asks one question at a time:
   - What type of drink would you like?
   - What size?
   - What type of milk?
   - Any extras? (optional, can be multiple)
   - What's your name?
3. **Saving**: Once all required fields are collected, the order is saved to a JSON file
4. **Confirmation**: Barista confirms the order back to the customer

### Example Order JSON:
```json
{
  "drinkType": "latte",
  "size": "large",
  "milk": "oat",
  "extras": ["whipped cream", "vanilla"],
  "name": "John",
  "timestamp": "2025-01-23T10:30:45.123456"
}
```

## 🚀 Testing Your Barista Agent

### Step 1: Start the Application

Make sure your API keys are set in `backend/.env.local`, then:

```bash
# From the root directory
./start_app.sh
```

Or run services separately:
```bash
# Terminal 1 - LiveKit Server
livekit-server --dev

# Terminal 2 - Backend
cd backend
uv run python src/agent.py dev

# Terminal 3 - Frontend
cd frontend
pnpm dev
```

### Step 2: Place an Order

1. Open **http://localhost:3000** in your browser
2. Click "Start call"
3. Allow microphone permissions
4. Start placing your order! Example conversation:
   - Barista: "Hi! Welcome! What can I get for you today?"
   - You: "I'd like a latte"
   - Barista: "Great! What size would you like?"
   - You: "Large"
   - Barista: "What type of milk?"
   - You: "Oat milk"
   - Barista: "Any extras?"
   - You: "Whipped cream and vanilla"
   - Barista: "Perfect! What's your name?"
   - You: "John"
   - Barista: "Order saved! Here's your order: latte (large) with oat milk and whipped cream, vanilla for John."

### Step 3: Check Your Order

After placing an order, check the `backend/orders/` directory:

```bash
cd backend
ls orders/
cat orders/order_*.json
```

You should see a JSON file with your order details!

## 📹 Recording Your Video

Record a short video (1-2 minutes) showing:

1. ✅ The application running in your browser
2. ✅ You placing a coffee order with the barista
3. ✅ The barista asking clarifying questions
4. ✅ The order being completed
5. ✅ Show the JSON file with the order summary

**Tips:**
- Speak clearly so viewers can hear the conversation
- Show the browser with the app running
- After the order, open the JSON file to show the saved order
- Keep it engaging and demonstrate the full flow

## 📱 Post on LinkedIn

Create a LinkedIn post with all required elements:

### Required Content:

1. **Your video** (the one you just recorded)

2. **Description** that includes:
   - What you built for Day 2 (coffee shop barista agent)
   - Mention you're building voice agents using **Murf Falcon** - the fastest TTS API
   - Say you're part of the **"Murf AI Voice Agent Challenge"**

3. **Tag @Murf AI** (the official handle)

4. **Hashtags:**
   - `#MurfAIVoiceAgentsChallenge`
   - `#10DaysofAIVoiceAgents`

### Example Post Template:

```
🎙️ Day 2 Complete! Built a coffee shop barista voice agent! ☕

Transformed my voice agent into a friendly barista that can take orders via voice! The agent:
✅ Guides customers through ordering (drink type, size, milk, extras, name)
✅ Maintains order state throughout the conversation
✅ Saves completed orders to JSON files
✅ Uses Murf Falcon - the fastest TTS API - for natural voice responses

The barista asks clarifying questions one at a time, just like a real coffee shop experience. Orders are automatically saved with timestamps!

This is Day 2 of 10 - building 10 AI voice agents in 10 days! 🚀

Excited to be part of the Murf AI Voice Agent Challenge!

@Murf AI #MurfAIVoiceAgentsChallenge #10DaysofAIVoiceAgents #VoiceAI #AIAgents

[Your video here]
```

## 🎉 Day 2 Complete!

Once you:
1. ✅ Have the barista agent running
2. ✅ Successfully placed an order
3. ✅ Verified the order was saved to JSON
4. ✅ Recorded your video
5. ✅ Posted on LinkedIn

**Day 2 is complete!** 🎊

## 🆘 Troubleshooting

### Order not saving
- ✅ Check that all required fields are filled (drinkType, size, milk, name)
- ✅ Verify the `backend/orders/` directory exists and is writable
- ✅ Check backend terminal logs for any errors

### Agent not asking the right questions
- ✅ Make sure the agent is using the tools (`update_order_field`, `get_order_status`, `save_order`)
- ✅ Check backend logs to see if tools are being called
- ✅ Verify the agent instructions are correct

### JSON file not created
- ✅ Check file permissions in the backend directory
- ✅ Verify the orders directory was created
- ✅ Check backend terminal for error messages

## 📚 Resources

- **Day 2 Task**: `challenges/Day 2 Task.md`
- **LiveKit Tools Docs**: https://docs.livekit.io/agents/build/tools/
- **LiveKit State Management**: https://docs.livekit.io/agents/build/agents-handoffs/#passing-state
- **Drive-thru Example**: https://github.com/livekit/agents/blob/main/examples/drive-thru/agent.py

---

**You're ready to test your barista agent!** 🚀☕

