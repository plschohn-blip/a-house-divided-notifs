"""
Poller: runs every minute, checks the AHD API for new events,
and DMs matching subscribers.
"""

import logging
from datetime import datetime, timezone

import discord

from ahd_api import AhdApi
from db import Database

log = logging.getLogger("ahd-poller")


def _make_embed(title: str, description: str, color: int, fields: list = None, url: str = None) -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.now(timezone.utc),
    )
    if fields:
        for f in fields:
            embed.add_field(name=f["name"], value=f["value"], inline=f.get("inline", True))
    if url:
        embed.url = url
    embed.set_footer(text="A House Divided Alert Bot • /myalerts to manage subscriptions")
    return embed


async def _dm(bot: discord.Client, user_id: int, embed: discord.Embed):
    """Send a DM to a user by ID, silently skip if DMs are closed."""
    try:
        user = await bot.fetch_user(user_id)
        await user.send(embed=embed)
    except discord.Forbidden:
        log.info(f"Cannot DM user {user_id} (DMs disabled)")
    except Exception as e:
        log.warning(f"Failed to DM {user_id}: {e}")


class Poller:
    def __init__(self, db: Database, bot: discord.Client):
        self.db = db
        self.bot = bot
        self.api = AhdApi()

    def _matches_election(self, sub: dict, election: dict, country: str) -> bool:
        if sub["country"] and sub["country"] != country:
            return False
        if sub["status"] and sub["status"] != election.get("status", ""):
            return False
        if sub["keyword"]:
            keyword = sub["keyword"]
            title = (election.get("electionType", "") + " " + election.get("state", "") + " " + country).lower()
            candidates = " ".join(c.get("characterName", "") for c in election.get("candidates", []))
            if keyword not in title and keyword not in candidates.lower():
                return False
        return True

    def _matches_legislation(self, sub: dict, bill: dict, country: str) -> bool:
        if sub["country"] and sub["country"] != country:
            return False
        if sub["keyword"] and sub["keyword"] not in bill.get("title", "").lower():
            return False
        return True

    def _matches_market(self, sub: dict, corp: dict, change: float) -> bool:
        if sub["keyword"] and sub["keyword"] not in corp.get("name", "").lower():
            return False
        threshold = sub.get("threshold", 0)
        minimum = threshold if threshold > 0 else 0.05
        if abs(change) < minimum:
            return False
        return True

    def _matches_news(self, sub: dict, post: dict) -> bool:
        country = post.get("countryId") or ""
        if sub["country"] and sub["country"] != country:
            return False
        if sub["keyword"]:
            text = (post.get("title", "") + " " + post.get("content", "")).lower()
            if sub["keyword"] not in text:
                return False
        return True

    def _matches_character(self, sub: dict, char_name: str, fav_change: float, pi_change: float) -> bool:
        if sub["keyword"] and sub["keyword"] not in char_name.lower():
            return False
        threshold = sub.get("threshold", 0)
        if threshold and max(abs(fav_change), abs(pi_change)) < threshold:
            return False
        return True

    async def run(self):
        await self._check_elections()
        await self._check_legislation()
        await self._check_market()
        await self._check_news()
        await self._check_characters()
        await self.api.close()

    # ── Elections ─────────────────────────────────────────────────────────────

    async def _check_elections(self):
        subs = self.db.get_subscribers_for("elections")
        if not subs:
            return

        # Collect unique countries subscribers care about
        countries = set(s["country"] for s in subs if s["country"])
        if not countries:
            countries = {"US", "GB", "DE", "JP", "FR", "CA", "AU"}  # sensible default set

        seen: dict = self.db.get_state("elections_seen", {})

        for country in countries:
            data = await self.api.get("elections", {"country": country})
            if not data or not data.get("found"):
                continue

            for election in data.get("elections", []):
                eid = election["id"]
                status = election.get("status", "")
                key = f"{eid}:{status}"
                if key in seen:
                    continue
                seen[key] = True

                etype = election.get("electionType", "Election")
                estate = election.get("state", country)
                candidates = election.get("candidates", [])
                cand_str = ", ".join(
                    f"{c['characterName']} ({c['party']})" for c in candidates[:5]
                ) or "None yet"

                color = {"open": 0x57F287, "upcoming": 0xFEE75C, "closed": 0xED4245}.get(status, 0x5865F2)
                icon = {"open": "🟢", "upcoming": "🟡", "closed": "🔴"}.get(status, "🗳️")
                embed = _make_embed(
                    title=f"{icon} Election {status.upper()} — {estate}, {country}",
                    description=f"**{etype}** is now **{status}**.",
                    color=color,
                    fields=[{"name": "Candidates", "value": cand_str, "inline": False}],
                    url=f"https://www.ahousedividedgame.com/elections/{eid}",
                )

                # DM matching subscribers
                for sub in subs:
                    if self._matches_election(sub, election, country):
                        await _dm(self.bot, sub["user_id"], embed)

        self.db.set_state("elections_seen", seen)

    # ── Legislation ───────────────────────────────────────────────────────────

    async def _check_legislation(self):
        subs = self.db.get_subscribers_for("legislation")
        if not subs:
            return

        countries = set(s["country"] for s in subs if s["country"])
        if not countries:
            countries = {"US"}

        seen: dict = self.db.get_state("legislation_seen", {})

        for country in countries:
            for status in ("passed", "failed"):
                data = await self.api.get("legislation", {"country": country, "status": status, "limit": 20})
                if not data or not data.get("found"):
                    continue

                for bill in data.get("bills", []):
                    bid = bill["id"]
                    key = f"{bid}:{status}"
                    if key in seen:
                        continue
                    seen[key] = True

                    title = bill.get("title", "Untitled Bill")
                    sponsor = bill.get("sponsor") or "Unknown"
                    vote = bill.get("vote", {})
                    vote_str = f"✅ {vote.get('yes', 0)} / ❌ {vote.get('no', 0)}" if vote else "—"

                    color = 0x57F287 if status == "passed" else 0xED4245
                    icon = "✅" if status == "passed" else "❌"
                    embed = _make_embed(
                        title=f"{icon} Bill {status.upper()} — {country}",
                        description=f"**{title}**",
                        color=color,
                        fields=[
                            {"name": "Sponsor", "value": sponsor, "inline": True},
                            {"name": "Vote", "value": vote_str, "inline": True},
                        ],
                    )

                    for sub in subs:
                        if self._matches_legislation(sub, bill, country):
                            await _dm(self.bot, sub["user_id"], embed)

        self.db.set_state("legislation_seen", seen)

    # ── Market ────────────────────────────────────────────────────────────────

    async def _check_market(self):
        subs = self.db.get_subscribers_for("market")
        if not subs:
            return

        # Market subs use keyword field to store corporation name/ticker
        corp_keywords = set(s["keyword"] for s in subs if s["keyword"])
        prev_prices: dict = self.db.get_state("market_prices", {})

        # Fetch top corporations
        data = await self.api.get("corporations", {"limit": 50})
        if not data or not data.get("found"):
            return

        for corp in data.get("corporations", []):
            corp_id = str(corp["id"])
            name = corp.get("name", "Unknown")
            price = corp.get("sharePrice")
            if price is None:
                continue

            prev = prev_prices.get(corp_id)
            prev_prices[corp_id] = price

            if prev is None:
                continue

            change = (price - prev) / prev if prev else 0

            matching_subs = [sub for sub in subs if self._matches_market(sub, corp, change)]
            if not matching_subs:
                continue

            direction = "📈" if change > 0 else "📉"
            color = 0x57F287 if change > 0 else 0xED4245
            embed = _make_embed(
                title=f"{direction} Stock Move — {name}",
                description=f"Share price moved **{change * 100:+.1f}%** ({prev:,.0f} → {price:,.0f})",
                color=color,
                fields=[
                    {"name": "Corporation", "value": name, "inline": True},
                    {"name": "New Price", "value": f"{price:,.0f}", "inline": True},
                ],
            )

            for sub in matching_subs:
                await _dm(self.bot, sub["user_id"], embed)

        self.db.set_state("market_prices", prev_prices)

    # ── News ──────────────────────────────────────────────────────────────────

    async def _check_news(self):
        subs = self.db.get_subscribers_for("news")
        if not subs:
            return

        seen: set = set(self.db.get_state("news_seen", []))

        data = await self.api.get("news", {"limit": 30})
        if not data or not data.get("found"):
            return

        for post in data.get("posts", []):
            pid = post["id"]
            if pid in seen:
                continue
            seen.add(pid)

            title = post.get("title") or "Untitled"
            content = post.get("content") or ""
            country = post.get("countryId") or ""
            category = post.get("category") or "general"
            author = post.get("authorName") or ("System" if post.get("isSystem") else "Unknown")
            snippet = content[:300] + ("…" if len(content) > 300 else "")

            embed = _make_embed(
                title=f"📰 {title}",
                description=snippet or "*No content*",
                color=0xEB459E,
                fields=[
                    {"name": "Author", "value": author, "inline": True},
                    {"name": "Country", "value": country or "Global", "inline": True},
                    {"name": "Category", "value": category, "inline": True},
                ],
            )

            for sub in subs:
                if self._matches_news(sub, post):
                    await _dm(self.bot, sub["user_id"], embed)

        self.db.set_state("news_seen", list(seen))

    # ── Characters ────────────────────────────────────────────────────────────

    async def _check_characters(self):
        subs = self.db.get_subscribers_for("characters")
        if not subs:
            return

        # Keyword field = character name (partial match)
        prev_stats: dict = self.db.get_state("char_stats", {})

        # Collect unique character names to look up
        names = set(s["keyword"] for s in subs if s["keyword"])
        if not names:
            return

        for name in names:
            data = await self.api.get("character", {"name": name})
            if not data or not data.get("found"):
                continue

            char = data.get("character", {})
            char_id = str(char.get("_id", name))
            char_name = char.get("name", name)
            fav = char.get("favorability", 0)
            pi = char.get("politicalInfluence", 0)

            prev = prev_stats.get(char_id, {})
            prev_fav = prev.get("fav")
            prev_pi = prev.get("pi")
            prev_stats[char_id] = {"fav": fav, "pi": pi}

            if prev_fav is None:
                continue

            fav_change = fav - prev_fav
            pi_change = pi - prev_pi
            matching_subs = [sub for sub in subs if self._matches_character(sub, char_name, fav_change, pi_change)]
            if not matching_subs:
                continue

            fields = []
            if fav_change != 0:
                arrow = "⬆️" if fav_change > 0 else "⬇️"
                fields.append({"name": f"{arrow} Favorability", "value": f"{prev_fav:.1f} → {fav:.1f} ({fav_change:+.1f})", "inline": True})
            if pi_change != 0:
                arrow = "⬆️" if pi_change > 0 else "⬇️"
                fields.append({"name": f"{arrow} Political Influence", "value": f"{prev_pi:.0f} → {pi:.0f} ({pi_change:+.0f})", "inline": True})

            if not fields:
                continue

            embed = _make_embed(
                title=f"👤 Character Update — {char_name}",
                description=f"**{char_name}** stats have changed.",
                color=0x5865F2,
                fields=fields,
                url=f"https://www.ahousedividedgame.com{char.get('profileUrl', '')}",
            )

            for sub in matching_subs:
                await _dm(self.bot, sub["user_id"], embed)

        self.db.set_state("char_stats", prev_stats)
