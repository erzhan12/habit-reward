# Quick Start Guide

Get your Habit Reward System up and running in minutes!

## Step 1: Install uv and Dependencies

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh
# Or on macOS: brew install uv

# Install project dependencies
uv sync
```

## Step 2: Configure Environment

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your credentials:
   ```bash
   # Get from https://airtable.com/account
   AIRTABLE_API_KEY=keyXXXXXXXXXXXXXX
   AIRTABLE_BASE_ID=appXXXXXXXXXXXXXX

   # Get from @BotFather on Telegram
   TELEGRAM_BOT_TOKEN=123456789:XXXXXXXXXXXXXXXXXXXXXXXXXXX

   # LLM Configuration
   LLM_PROVIDER=openai  # or "anthropic", "ollama", etc.
   LLM_MODEL=gpt-3.5-turbo  # or "gpt-4", "claude-3-sonnet", etc.
   LLM_API_KEY=sk-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX  # Get from https://platform.openai.com/api-keys

   # Optional: Your Telegram ID (get from @userinfobot)
   DEFAULT_USER_TELEGRAM_ID=123456789
   ```

## Step 3: Set Up Airtable

1. Go to [Airtable](https://airtable.com) and create a new base
2. Create 5 tables with these exact names and fields:

### Users
- telegram_id (Single line text)
- name (Single line text)
- active (Checkbox)

### Habits
- name (Single line text)
- weight (Number, default: 1)
- category (Single line text)
- active (Checkbox)

### Rewards
- name (Single line text)
- weight (Number, default: 1)
- type (Single select: virtual, real, none, cumulative)
- is_cumulative (Checkbox)
- pieces_required (Number)
- piece_value (Number)

### Reward Progress
- user_id (Link to Users)
- reward_id (Link to Rewards)
- pieces_earned (Number)
- status (Single select: 🕒 Pending, ⏳ Achieved, ✅ Completed)
- pieces_required (Number)

### Habit Log
- user_id (Link to Users)
- habit_id (Link to Habits)
- timestamp (Date with time)
- reward_id (Link to Rewards)
- got_reward (Checkbox)
- streak_count (Number)
- habit_weight (Number)
- total_weight_applied (Number)
- last_completed_date (Date)

3. Add initial data:

**Add yourself to Users:**
- telegram_id: (your Telegram ID from @userinfobot)
- name: Your Name
- weight: 1
- active: ✓

**Add some habits:**
- name: Walking, weight: 1, category: health, active: ✓
- name: Reading, weight: 1, category: learning, active: ✓
- name: Meditation, weight: 1, category: mindfulness, active: ✓

**Add some rewards:**
- name: Coffee at favorite cafe, weight: 2, type: cumulative, is_cumulative: ✓, pieces_required: 10, piece_value: 0.5
- name: Watch a movie, weight: 3, type: real
- name: No reward, weight: 5, type: none

## Step 4: Run the Bot

```bash
./run_bot.sh
# Or: uv run python -m src.bot.main
```

## Step 5: Test the Bot

1. Open Telegram
2. Find your bot (search for the bot username you created)
3. Send `/start` to begin
4. Try `/habit_done` to log your first habit!

## Step 6: Run the Dashboard (Optional)

In a new terminal:

```bash
./run_dashboard.sh
# Or: uv run streamlit run src/dashboard/app.py
```

The dashboard will open at http://localhost:8501

## Common Commands

**Telegram Bot:**
- `/habit_done` - Log a habit (with auto-complete!)
- `/streaks` - See your current streaks
- `/my_rewards` - Check reward progress
- `/list_rewards` - View all rewards

**Dashboard:**
- View recent completions
- Track cumulative rewards
- Claim achieved rewards
- Visualize streaks

## Troubleshooting

### Bot doesn't respond
- Check TELEGRAM_BOT_TOKEN is correct
- Make sure bot is running
- Try `/start` command first

### Dashboard shows "User not found"
- Set DEFAULT_USER_TELEGRAM_ID in .env
- Make sure you added yourself to Users table
- Verify telegram_id matches exactly

### No rewards showing up
- Add rewards to Rewards table in Airtable
- Include at least one "none" type reward
- Check reward weights are > 0

### Import errors
- Run `uv sync` again to reinstall dependencies
- Check Python version is 3.13+
- The virtual environment is automatically managed by uv in `.venv/`
- If issues persist, delete `.venv/` and run `uv sync` again

## Next Steps

1. **Customize habits** - Add your own habits in Airtable
2. **Configure rewards** - Set up rewards that motivate you
3. **Adjust weights** - Tune habit and reward weights to your preference
4. **Build streaks** - Complete habits daily to increase rewards
5. **Track progress** - Use the dashboard to visualize your journey

## Tips for Success

- Start with 3-5 habits you actually want to build
- Include a mix of cumulative and instant rewards
- Keep "no reward" weight high enough to maintain variable ratio
- Check the dashboard weekly to track progress
- Claim achieved rewards to keep yourself motivated!

Enjoy building your habits! 🎯🔥
