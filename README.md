# AHD Alert Bot — Discord App

A Discord bot that allows **A House Divided** players to subscribe to in-game alerts and receive Discord DMs when important events occur.

---

## Getting Started

1. Invite the bot to your Discord server.
2. Use `/subscribe` to create alerts for events you want to follow.
3. Wait for matching events to occur and receive a private Discord DM.

You can create as many alerts as you would like and customize them using countries and keywords.

---

## Commands

| Command        | Description                                              |
| -------------- | -------------------------------------------------------- |
| `/subscribe`   | Create a new alert subscription                          |
| `/unsubscribe` | Remove an alert subscription                             |
| `/myalerts`    | View all of your active subscriptions                    |
| `/ahd`         | Display information about the bot and available commands |

---

## Alert Types

### Elections (`elections`)

Receive notifications when elections become upcoming, open, or close.

**Available filters:**

* `country` — Only receive alerts for a specific country.

**Example:**

```
/subscribe alert_type:elections country:US
```

---

### Legislation (`legislation`)

Receive notifications when bills pass or fail.

**Available filters:**

* `country` — Filter by the country the legislation belongs to.
* `keyword` — Match words or phrases in the bill title.

**Example:**

```
/subscribe alert_type:legislation country:GB keyword:healthcare
```

---

### Market (`market`)

Receive notifications when a corporation's stock price changes by 5% or more.

**Available filters:**

* `keyword` — Match a corporation name.

**Example:**

```
/subscribe alert_type:market keyword:Acme Corp
```

---

### News (`news`)

Receive notifications when new news articles are posted.

**Available filters:**

* `country` — Only receive news from a specific country.
* `keyword` — Match words or phrases in the news title.

**Example:**

```
/subscribe alert_type:news country:US keyword:election
```

---

### Characters (`characters`)

Receive notifications when a character's favorability or political influence changes.

**Available filters:**

* `keyword` — Match a character's name.

**Example:**

```
/subscribe alert_type:characters keyword:John Smith
```

---

## Managing Your Alerts

Use `/myalerts` at any time to see your current subscriptions.

To remove an alert, use `/unsubscribe` with the same alert type you used when creating it.

Example:

```
/unsubscribe alert_type:elections
```

---

## Disclaimer

This is an independent community project and is not affiliated with or endorsed by the developers of **A House Divided**.
