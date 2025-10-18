You are an expert Python developer and system architect. Help me build a scalable, gamified habit-reward system using Python (FastAPI or Flask), Airtable, a Telegram Bot, and OpenAI for NLP.

I am the only user for now, but the system should be scalable for multiple users via Telegram ID. The goal is to make habit tracking engaging by using **variable ratio rewards**, **streak multipliers**, and **cumulative rewards**.

---

🧱 **Stack**
- Python (Flask or FastAPI)
- Airtable (for Users, Habits, Rewards, Logs, Reward Progress)
- Telegram Bot (via python-telegram-bot)
- OpenAI (for habit detection from text input)

---

✅ **Core User Flow – `/habit_done` Command**
1. I send `/habit_done` to the Telegram bot.
2. Bot checks my Telegram ID in the Airtable Users table.
3. Bot prompts me to select a habit from a list or enter a custom text.
4. If custom text is provided:
   - Use OpenAI GPT to classify the input and match to the closest habit from the Airtable Habits table.
5. Once the habit is identified:
   - Pull the habit’s weight.
   - Pull the user's weight from Users table.
   - Calculate streak multiplier (default: `1 + (streak × 0.1)`).
   - Total reward multiplier = `habit_weight × user_weight × streak_multiplier`.
6. Pull all active rewards from Airtable:
   - Include rewards of type `none` to simulate "no reward"
   - Include cumulative rewards (`is_cumulative = true`)
7. Run weighted random draw using the adjusted weights.
8. If the reward is cumulative:
   - Update Reward Progress table (increment pieces)
   - If pieces >= pieces_required, mark it as `⏳ Achieved`
9. Log entry to Habit Log table (with habit_id, reward_id, streak count, total weight applied, etc.)
10. Respond on Telegram with:
   - ✅ Habit confirmation
   - 🎁 Reward result (or ❌ No reward this time)
   - 🔥 Streak status
   - ⏳ Cumulative reward progress (if applicable)
   - 🧠 Motivational quote (optional)

---

📊 **Airtable Tables & Key Fields**

1. **Users**
   - `telegram_id`, `name`, `weight`, `active`, etc.

2. **Habits**
   - `name`, `weight`, `category`, `active`, etc.

3. **Rewards**
   - `name`, `weight`, `type` (virtual, real, none, cumulative), `is_cumulative`, `pieces_required`, `piece_value`

4. **Reward Progress**
   - `user_id`, `reward_id`, `pieces_earned`, `status` (Pending, Achieved, Completed), `progress_percent`, `status_emoji`, `actionable_now`

5. **Habit Log**
   - `user_id`, `habit_id`, `timestamp`, `reward_id`, `got_reward`, `streak_count`, `habit_weight`, `total_weight_applied`

---

🎯 **Reward Status Logic**
Track cumulative reward lifecycle using these statuses in the Reward Progress table:
- `🕒 Pending`: Not yet completed (pieces < required)
- `⏳ Achieved`: Fully earned, waiting to be claimed
- `✅ Completed`: Reward has been claimed (e.g., MacBook bought)

Let me view all `⏳ Achieved` rewards to decide what I can now buy or enjoy. I want to mark rewards as `✅ Completed` manually.

---

🔁 **Per-Habit Streak Reset Logic**
Track the last completed date for each habit. If a habit is not completed on a consecutive day, reset its streak to 1. Streaks are tracked per habit, not globally.

---

🤖 **Telegram Bot Commands**
- `/habit_done` → Trigger habit flow
- `/add_reward` → Add new reward via message
- `/list_rewards` → List all active rewards
- `/my_rewards` → Show cumulative reward progress
- `/claim_reward reward_name` → Mark reward as Completed
- `/set_reward_status reward_name status` → Manually update reward status
- `/streaks` → Show current streaks per habit

---

📊 **Dashboard (via Streamlit)**
Build a Streamlit dashboard to visualize:
- Habit logs and streaks
- Cumulative reward progress with status and emojis
- “Actionable now” rewards (i.e., ⏳ Achieved)
- Buttons to mark rewards as completed
- Reward value overview (total value earned, claimed, etc.)

---

⚖️ **Ethical + Data Considerations**
- User data must be private and exportable
- Avoid manipulative reward timing
- Emphasize motivation and clarity, not addiction
- Use transparent reward logic
- System should be easy to extend (SQLite/Postgres later)

---

🧠 **LLM Prompt Example for Habit Classification**
If user sends:  
> `/habit_done I walked 5km and meditated`  
Use OpenAI to match to closest habit(s) from the Habits table.

Sample prompt:
You are an AI that maps user habit logs to known habits.
Available habits:

Walking

Journaling

Meditation

Coding

Reading

User input: “I walked 5km and meditated”
Match to one or more habits from the list above.

---

🎯 Final goal: A modular, gamified habit tracking + reward system using Python, Airtable, Telegram, and OpenAI — supporting weighted rewards, per-habit streaks, cumulative reward progress, and reward lifecycle status tracking.

Return Python code, Airtable API logic, and Telegram integration using `python-telegram-bot`. Modularize each function clearly. Respond only with code unless asked otherwise.
