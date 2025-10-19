# Habit Reward System

A gamified habit-reward system that tracks habits with per-habit streaks, uses variable ratio rewards with streak multipliers, and supports cumulative rewards with lifecycle status tracking.

## Features

- **Per-Habit Streak Tracking**: Each habit maintains its own streak independently
- **Weighted Random Rewards**: Variable ratio reward system with streak multipliers
- **Cumulative Rewards**: Collect pieces toward larger rewards with status tracking (🕒 Pending, ⏳ Achieved, ✅ Completed)
- **Telegram Bot Interface**: Easy-to-use bot for logging habits and managing rewards
- **OpenAI NLP Integration**: Natural language processing for habit classification
- **Streamlit Dashboard**: Visual analytics and progress tracking
- **Airtable Backend**: Cloud-based data storage with easy access and export

## Architecture

```
habit_reward/
├── src/
│   ├── models/          # Pydantic data models
│   ├── airtable/        # Airtable client and repositories
│   ├── services/        # Business logic layer
│   ├── bot/             # Telegram bot handlers
│   └── dashboard/       # Streamlit dashboard components
├── tests/               # Unit tests
├── pyproject.toml       # Project configuration and dependencies (uv)
└── .env                 # Environment configuration
```

## Installation

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) - Fast Python package installer
- Airtable account and API key
- Telegram Bot Token (from @BotFather)
- OpenAI API Key

### Setup Steps

1. **Install uv** (if not already installed)
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   # Or on macOS: brew install uv
   ```

2. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd habit_reward
   ```

3. **Install dependencies**
   ```bash
   uv sync
   ```
   This will create a virtual environment and install all dependencies automatically.

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

5. **Set up Airtable**

   Create the following tables in your Airtable base:

   **Users Table**
   - `telegram_id` (Single line text, unique)
   - `name` (Single line text)
   - `weight` (Number, default: 1.0)
   - `active` (Checkbox)

   **Habits Table**
   - `name` (Single line text)
   - `weight` (Number, default: 1.0)
   - `category` (Single line text)
   - `active` (Checkbox)

   **Rewards Table**
   - `name` (Single line text)
   - `weight` (Number, default: 1.0)
   - `type` (Single select: virtual/real/none/cumulative)
   - `is_cumulative` (Checkbox)
   - `pieces_required` (Number)
   - `piece_value` (Number)

   **Reward Progress Table**
   - `user_id` (Link to Users)
   - `reward_id` (Link to Rewards)
   - `pieces_earned` (Number)
   - `status` (Single select: 🕒 Pending/⏳ Achieved/✅ Completed)
   - `actionable_now` (Checkbox)
   - `pieces_required` (Number)

   **Habit Log Table**
   - `user_id` (Link to Users)
   - `habit_id` (Link to Habits)
   - `timestamp` (Date with time)
   - `reward_id` (Link to Rewards)
   - `got_reward` (Checkbox)
   - `streak_count` (Number)
   - `habit_weight` (Number)
   - `total_weight_applied` (Number)
   - `last_completed_date` (Date)

## Usage

### Running the Telegram Bot

```bash
./run_bot.sh
# Or: uv run python -m src.bot.main
```

**Available Bot Commands:**
- `/start` - Welcome message and help
- `/habit_done` - Log a completed habit
- `/streaks` - View current streaks for all habits
- `/list_rewards` - See all available rewards
- `/my_rewards` - Check cumulative reward progress
- `/claim_reward <name>` - Claim an achieved reward
- `/set_reward_status <name> <status>` - Update reward status

### Running the Dashboard

```bash
./run_dashboard.sh
# Or: uv run streamlit run src/dashboard/app.py
```

The dashboard will open in your browser at `http://localhost:8501`

**Dashboard Features:**
- Recent habit completions table
- Cumulative reward progress cards with progress bars
- Actionable rewards section with claim buttons
- Reward value overview (total earned, claimed, pending)
- Per-habit streak chart

## How It Works

### Streak Calculation

Each habit maintains its own streak:
1. First completion: streak = 1
2. Completed yesterday: increment streak
3. Already completed today: return current streak
4. Missed days: reset to 1

### Reward Weight Formula

```
total_weight = habit_weight × streak_multiplier
where streak_multiplier = 1 + (streak_count × 0.1)
```

### Weighted Random Selection

1. Fetch all active rewards (including "none" type)
2. Adjust each reward weight by total_weight
3. Perform weighted random selection
4. If cumulative: increment pieces, check if achieved

### Cumulative Rewards

- **🕒 Pending**: Still collecting pieces
- **⏳ Achieved**: Pieces >= required, ready to claim
- **✅ Completed**: Claimed by user

## Development

### Running Tests

```bash
uv run pytest tests/
```

### Running Tests with Coverage

```bash
uv run pytest --cov=src tests/
```

### Project Structure

- **Models** (`src/models/`): Pydantic models for data validation
- **Repositories** (`src/airtable/`): Data access layer using repository pattern
- **Services** (`src/services/`): Business logic layer
  - `streak_service.py`: Streak calculation
  - `reward_service.py`: Reward selection and cumulative progress
  - `habit_service.py`: Main orchestration
  - `nlp_service.py`: OpenAI habit classification
- **Bot** (`src/bot/`): Telegram bot interface
- **Dashboard** (`src/dashboard/`): Streamlit visualization

## Configuration

All configuration is managed via environment variables in `.env`:

```env
# Required
AIRTABLE_API_KEY=your_key_here
AIRTABLE_BASE_ID=your_base_id_here
TELEGRAM_BOT_TOKEN=your_token_here
LLM_PROVIDER=openai
LLM_MODEL=gpt-3.5-turbo
LLM_API_KEY=your_key_here

# Optional
DEFAULT_USER_TELEGRAM_ID=your_telegram_id_here
```

## Algorithms

### Per-Habit Streak Algorithm

```
INPUT: user_id, habit_id
OUTPUT: current_streak

1. last_log = get_last_log(user_id, habit_id)
2. IF last_log is None: RETURN 1
3. last_date = last_log.last_completed_date
4. today = current_date()
5. IF last_date == today: RETURN last_log.streak_count
6. IF last_date == yesterday: RETURN last_log.streak_count + 1
7. ELSE: RETURN 1
```

### Weighted Random Reward Selection

```
INPUT: total_weight
OUTPUT: selected_reward

1. rewards = get_all_active_rewards()
2. adjusted_weights = [r.weight * total_weight for r in rewards]
3. selected = random.choices(rewards, weights=adjusted_weights, k=1)[0]
4. RETURN selected
```

### Cumulative Progress Update

```
INPUT: user_id, reward_id
OUTPUT: reward_progress

1. progress = get_or_create_progress(user_id, reward_id)
2. progress.pieces_earned += 1
3. IF progress.pieces_earned >= reward.pieces_required:
     progress.status = "⏳ Achieved"
4. ELSE:
     progress.status = "🕒 Pending"
5. RETURN progress
```

## Ethical Considerations

1. **Data Privacy**: Only telegram_id stored, full user control via Airtable
2. **Transparent Logic**: All calculations logged and visible
3. **Motivation vs Addiction**: "None" rewards always included, streak multiplier capped
4. **Extensibility**: Repository pattern enables easy database migration

## Future Enhancements

- [ ] Multi-user support with user registration flow
- [ ] Conversational reward creation via bot
- [ ] Custom habit categories and tags
- [ ] Weekly/monthly reports
- [ ] Social features (share achievements)
- [ ] Mobile app interface
- [ ] REST API for third-party integrations
- [ ] Analytics and insights (best times, patterns)

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run tests to ensure they pass
6. Submit a pull request

## License

[Choose appropriate license]

## Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Contact: [Your contact information]

## Acknowledgments

- Built with [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- Data storage via [Airtable](https://airtable.com)
- NLP powered by [OpenAI](https://openai.com)
- Dashboard created with [Streamlit](https://streamlit.io)
