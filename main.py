# A bot that tracks the reputation of members in a telegram group

from contextlib import contextmanager
import datetime
import logging
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import (
    Updater,
    Defaults,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    Filters,
)

from models.User import (
    reset_weekly,
    reset_votes,
    weekly_leaderboard,
    top_leaderboard,
    reputation_stats,
    maintain_user,
    voting,
    create_new_user,
    Base_User,
)

# ======================= SOME GLOBALS =======================
BASEDIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = BASEDIR + os.sep + "reputation.db"
TOKEN_FILE = BASEDIR + os.sep + "token"
CHATID_FILE = BASEDIR + os.sep + "chatid"

with open(TOKEN_FILE) as token_file:
    TOKEN = (token_file.read()).strip()

with open(CHATID_FILE) as chatid_file:
    CHATID = (chatid_file.read()).strip()

# ======================= DATABASE SETUP =======================
engine = create_engine("sqlite:///" + DATABASE)
Session = sessionmaker(bind=engine)
Base_User.metadata.create_all(engine)


@contextmanager
def session_scope():
    """Contextmanager for sqlalchemy sessions"""
    session = Session()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


# ======================= LOGGING SETUP =======================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.DEBUG
)
logger = logging.getLogger(__name__)


# ======================= LOGIC FOR THE TELEGRAM BOT =======================
def toprep(update, context):
    """Show the reputation of the top 10 people"""
    with session_scope() as session:
        html_string = top_leaderboard(session)
    update.message.reply_html(html_string)


def weekly(update, context):
    """Show the weekly leaderboard"""
    with session_scope() as session:
        html_string = weekly_leaderboard(session)
    update.message.reply_html(html_string)


def myrep(update, context):
    """Display the reputation of a certain user and their votes"""
    userid = update.message.from_user.id
    username = update.message.from_user.username
    with session_scope() as session:
        html_string = reputation_stats(session, userid, username)
    update.message.reply_html(html_string)


def vote(update, context):
    """Can the bot react to non commands"""
    # get the IDs and usernames of voter and votee

    msg = update.message.text
    if msg.startswith("+") or msg.startswith("-"):
        from_userid = update.message.from_user.id
        from_username = update.message.from_user.username
        to_userid = update.message.reply_to_message.from_user.id
        to_username = update.message.reply_to_message.from_user.username
        if update.message.reply_to_message is None:
            pass
        elif update.message.reply_to_message.text:
            if (
                update.message.reply_to_message.text == "-"
                or update.message.reply_to_message.text == "+"
            ):
                update.message.reply_text(text="Sorry, you cannot vote for votes.")
            elif update.message.reply_to_message.text.startswith("/"):
                update.message.reply_text(text="Sorry, you cannot vote for commands.")
            elif update.message.reply_to_message.from_user.is_bot:
                update.message.reply_text(text="Sorry, you cannot vote for bots.")
            else:
                # You cannot vote for yourself
                if from_username == to_username:
                    update.message.reply_text(text="You cannot vote for yourself.")
                else:
                    if msg.startswith("+") or msg.startswith("-"):
                        with session_scope() as session:
                            # prepare the queries from_user and to_user
                            from_user = maintain_user(
                                session, from_userid, from_username
                            )
                            to_user = maintain_user(session, to_userid, to_username)

                            for char in msg:
                                if char == "+":
                                    up = True
                                    html_string = voting(
                                        session, to_user, from_user, up
                                    )
                                elif char == "-":
                                    up = False
                                    html_string = voting(
                                        session, to_user, from_user, up
                                    )
                    update.message.reply_html(html_string)


def manual_reset(update, context):
    """Manually replenish votes"""
    if update.message.from_user.username == "AlexAnarcho":
        callback_reset_votes(context)


def callback_reset_votes(context):
    """Reset the votes for all group members"""
    with session_scope() as session:
        html_string = reset_votes(session)
    context.bot.send_message(chat_id=CHATID, parse_mode="HTML", text=html_string)


def callback_reset_weekly(context):
    """TG function to give winner of last week and reset score"""
    if datetime.datetime.now().isoweekday() == 7:
        # get the highest score from weekly, this will be the winner
        with session_scope() as session:
            html_string = reset_weekly(session)
        context.bot.send_message(
            chat_id=CHATID,
            parse_mode="HTML",
            text=html_string,
        )


def display_menu(update, context):
    """Display a button menu with all available commands"""
    keyboard = [
        [InlineKeyboardButton("MyRep", callback_data="myrep")],
        [
            InlineKeyboardButton("Top10", callback_data="top"),
            InlineKeyboardButton("Weekly", callback_data="weekly"),
        ],
        [InlineKeyboardButton("Help Message", callback_data="help")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_html("<b><i>Rep Bot Menu</i></b>", reply_markup=reply_markup)


def menu_buttons(update, context):
    """Handle the callback from the menu"""
    query = update.callback_query
    userid = update.callback_query.from_user.id
    username = update.callback_query.from_user.username

    with session_scope() as session:
        if query.data == "myrep":
            html_string = reputation_stats(session, userid, username)
        elif query.data == "top":
            html_string = top_leaderboard(session)
        elif query.data == "weekly":
            html_string = weekly_leaderboard(session)

    # return the matching html string
    query.edit_message_text(text=html_string, parse_mode="HTML")


def start(update, context):
    """Create the databases with the start message as input"""
    userid = update.message.from_user.id
    username = update.message.from_user.username

    with session_scope() as session:
        create_new_user(session, userid, username)
    html_string = "Hello there"

    update.message.reply_html(html_string)


def help(update, context):
    """Display a help message"""
    html_string = """
<b>THE REPUTATION BOT</b>

Within a 24h window you have only a limited amount of votes to cast, be wise.
Every week the most upvoted user will become champion!

<b>Commands:</b>
<code>/toprep</code> to view the Top 10 all time reputation
<code>/myrep</code> to show your repuationstats
<code>/weekly</code> for the leaderboard of the current week

<b>Mechanics</b>
Vote by replying with <code>+</code> or <code>-</code>
The level mechanism works like so:
<code>lvln ** 2 = xp_for_levelup</code>
(1 xp for lvl1, 4xp for lvl2, 9xp for lvl3...)

An upvote costs you 1 vote.
A downvote costs you 3 votes."""
    update.message.reply_html(html_string)


def error(update, context):
    """Log warnings"""
    logging.warning(f"Update {update} caused error {context.error}")


# ======================= RUNNING THE BOT =======================
def main():
    """Run the telegram bot with the commands"""
    updater = Updater(token=TOKEN, use_context=True)
    j = updater.job_queue

    dp = updater.dispatcher

    # Commands
    dp.add_handler(MessageHandler(Filters.text, vote), group=1)
    dp.add_handler(CommandHandler("start", start), group=2)
    dp.add_handler(CommandHandler("help", help), group=2)
    dp.add_handler(CommandHandler("toprep", toprep), group=2)
    dp.add_handler(CommandHandler("weekly", weekly), group=2)
    dp.add_handler(CommandHandler("myrep", myrep), group=2)
    dp.add_handler(CommandHandler("rep", display_menu), group=2)
    dp.add_handler(CommandHandler("reset", manual_reset), group=2)
    dp.add_handler(CallbackQueryHandler(menu_buttons), group=2)

    # Error
    dp.add_error_handler(error)

    # Start Bot and run
    updater.start_polling()

    # j.run_repeating(callback_reset_weekly, interval=1200, first=30)
    # j.run_repeating(callback_reset_votes, interval=600, first=0)
    j.run_daily(callback_reset_weekly, time=datetime.time(12, 0, 0))
    j.run_daily(callback_reset_votes, time=datetime.time(5, 0, 0))

    updater.idle()


if __name__ == "__main__":
    main()


# TODO Save some variables in config file (admin user, )
