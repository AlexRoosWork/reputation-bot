# Have the database models for sqlalchemy

from sqlalchemy import Column, String, Integer
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base_User = declarative_base()


class User(Base_User):
    """Class for the users"""

    __tablename__ = "users"

    userid = Column("userid", Integer, primary_key=True)
    username = Column("username", String, nullable=False)
    reputation_score = Column("reputation_score", Integer, default=0)
    votes = Column("votes", Integer, default=1)
    weekly_champ = Column("weekly_champ", Integer, default=0)
    weekly_score = Column("weekly_score", Integer, default=0)
    level = Column("level", Integer, default=0)
    xp = Column("xp", Integer, default=0)


# ======================= DATABASE OPERATIONS =======================
# Creation
def create_new_user(session, userid, username):
    """Add a new user into the db"""
    if session.query(User).get(userid):
        pass
    else:
        user = User(userid=userid, username=username)
        session.add(user)
        session.commit()


# Updates
def update_reputation(session, to_userid, from_userid, up):
    """Update the reputation of a given user. If up is TRUE,
    the reputation is incremented by one, otherwise, reduced by one"""
    from_user = session.query(User).get(from_userid)
    to_user = session.query(User).get(to_userid)
    html_string = ""  # empty string, give feedback if not enough votes left
    if up:
        if from_user.votes > 0:
            from_user.votes -= 1
            to_user.reputation_score += 1
            to_user.weekly_score += 1
            to_user.xp += 1
        else:
            html_string = "Sorry, not enough voting power."
    else:
        if from_user.votes >= 3:
            from_user.votes -= 3
            to_user.reputation_score -= 1
            to_user.weekly_score -= 1
        else:
            html_string = "Sorry, not enough voting power."

    session.add(from_user)
    session.add(to_user)
    session.commit()
    return html_string


def update_username(session, userid, username):
    """In case the user has changed his name, update the table to reflect it"""
    user = session.query(User).get(userid)
    user.username = username
    session.add(user)
    session.commit()


def update_level(session, userid):
    """
    Level for reputation. 1 rep for lvl 1, 4 rep for lvl 2, 9 rep for lvl 3...
    Returns true if new level was reached."""
    user = session.query(User).get(userid)
    next_level = user.level + 1
    xp_required = next_level ** 2
    if user.xp == xp_required:
        user.level += 1
        user.xp = 0
        session.add(user)
        session.commit()

        return True


def maintain_user(session, userid, username):
    """Check if user is in database, update the username if changed"""
    user = session.query(User).get(userid)
    if user is None:
        create_new_user(session, userid, username)
    if username != user.username:
        update_username(session, userid, username)
    return user


def voting(session, to_user, from_user, up):
    """Go through the logic of an upvote"""
    # check if the voter has the necessary resources to cast vote
    html_string = update_reputation(session, to_user.userid, from_user.userid, up)
    # Check for levelup
    if update_level(session, to_user.userid):
        html_string = (
            f"<b>{to_user.username}</b> has reached <b>level {to_user.level}!</b>"
        )
    return html_string


# Resets
def reset_votes(session):
    """
    Replenish all votes for users.
    Default is 1 vote. +1 for each level and weekly championship"""
    users = session.query(User).all()
    for user in users:
        bonus = user.weekly_champ + user.level
        user.votes = 1 + bonus
        session.add(user)
        session.commit()
    html_string = weekly_leaderboard(session)
    html_string += "\n\n<b>VOTES REPLENISHED</b>"
    return html_string


def reset_weekly(session):
    """Reset the score of everybody in the weekly Leaderboard"""
    winner = session.query(User).order_by(User.weekly_score.desc()).first()
    score = winner.weekly_score
    # update the champion count
    winner.weekly_champ += 1
    session.add(winner)

    html_string = f"""
🏆<b>{winner.username}</b> won the week with a score of {score}🏆

<b>Congratulations, {winner.username}!</b>
The new week begins now."""
    users = session.query(User).all()
    for user in users:
        user.weekly_score = 0
        session.add(user)

    return html_string


# Get Stats
def weekly_leaderboard(session):
    """Return the top 10 for the week"""
    users = session.query(User).order_by(User.weekly_score.desc()).all()

    html_string = """
    🏆 <b>WEEKLY LEADERBOARD</b> 🏆
  (Week ends on Sun, 12pm UTC)
  +++++++++++++++++++++++++

"""
    for user in users[:10]:
        if user.weekly_score >= 1:
            html_string += f"<code>{user.weekly_score}</code> <b>{user.username}</b>\n"
    return html_string


def top_leaderboard(session):
    """Return top 10 of all time"""
    users = session.query(User).order_by(User.reputation_score.desc()).all()

    html_string = "<b>TOP 10:</b>\n\n"
    for i, user in enumerate(users[:10]):
        if user.reputation_score > 0:
            if i == 0:
                html_string += "🥇"
            elif i == 1:
                html_string += "🥈"
            elif i == 2:
                html_string += "🥉"
            html_string += (
                f"<code>{user.reputation_score}</code> <b>{user.username}</b>\n"
            )
    return html_string


def reputation_stats(session, userid, username):
    """Show the reputation stats of a user"""
    user = session.query(User).get(userid)
    # create an entry in the database, if user does not exist
    if user is None:
        create_new_user(session, userid=userid, username=username)
        user = session.query(User).get(userid)
    # see if the user is in the top 3 of overall reputation
    users = session.query(User).order_by(User.reputation_score.desc()).all()

    trophy = ""
    for i, account in enumerate(users[:3]):
        if userid == account.userid and i == 0:
            trophy = "🥇"
        elif userid == account.userid and i == 1:
            trophy = "🥈"
        elif userid == account.userid and i == 2:
            trophy = "🥉"

    # display number of awards by the times of weekly wins

    weekly_champ = user.weekly_champ
    emoji_string = ""
    for i in range(weekly_champ):
        if weekly_champ >= 1:
            sign = "🏆"
            emoji_string += sign
            weekly_champ - 1
            continue

    html_string = f"""
<b>{"+" * 8} {user.username.upper()} {"+" * 8}</b>

<b>Reputation:</b> <code>{user.reputation_score}</code>
<b>Level:</b> <code>{user.level}</code>
<b>Upvotes till lvlup:</b> <code>{((user.level + 1) ** 2) - user.xp}</code>
<b>Trophies:</b> {trophy} {emoji_string}

<b>Votes:</b> <code>{user.votes}</code>"""
    return html_string
