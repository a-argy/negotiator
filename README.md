# CS 153 - Infrastruture at Scale AI Agent Starter Code

Note that for Discord the terms Bot and App are interchangable. We will use App in this manual.

## Discord App Framework Code

This is the base framework for students to complete the CS 152 final project. Please follow the instructions to fork this repository into your own repository and make all of your additions there. 

## Discord App Setup Instructions

Your group will be making your very own AI agent and import it into our CS153 server as a Discord App. This starter code provides the framework for a Discord App implemented in Python. Follow the instructions below. 

### Join the Discord Server

First, every member of the team should join the Discord server using the invite link on Ed.

### Get your Role within the Server

Role Options:

`Student`: For enrolled students in the course.

`Online-Student`:  For students taking this course online.

`Auditor`: For those auditing the course.

`Collaborator`: For external collaborators or guests.

How to Join Your Role:

1. Send a Direct Message (DM) to the Admin Bot.
2. Use the following command format: `.join <Role Name>`
3. Replace `<Role Name>` with one of the options above (e.g., `.join Student`).

How to Leave Your Role:

1. Send a Direct Message (DM) to the Admin Bot.
2. Use the following command format: `.leave <Role Name>`
3. Replace `<Role Name>` with one of the options above (e.g., `.leave Student`).

### Creating/Joining Your Group Channel

How to create or join your group channel:

1. Send a Direct Message (DM) to the Admin Bot.
2. Pick a unique group name (**IMPORTANT** )
2. Use the following command format:`.channel <Group Name>`
3. Replace `<Group Name>` with the name of your project group (e.g., `.channel Group 1`).

**What Happens When You Use the Command:**

If the Channel Already Exists:

- Check if you already have the role for this group. If you don’t have the role, it will assign you the role corresponding to `<Group Name>` granting you access to the channel.

If the Channel Does Not Exist:

- Create a new text channel named `<Group-Name>` in the Project Channels category.
- Create a role named `<group name>` (the system will intentionally lower the case) and assign it to you.

- Set permissions so that:
     - Only members with the `<group name>` role can access the channel. 
     - The app and server admins have full access. All other server members are denied access.
     - Once completed, you'll be able to access your group's private channel in the Project Channels category.

## [One student per group] Setting up your bot

##### Note: only ONE student per group should follow the rest of these steps.

### Download files

1. Fork and clone this GitHub repository. 
2. Share the repo with your teammates. 
3. Create a file called `.env` the same directory/folder as `bot.py `. The `.env` file should look like this, replacing the “your key here” with your key. In the below sections, we explain how to obtain Discord keys and Mistral API keys.

```
DISCORD_TOKEN=“your key here” 
MISTRAL_API_KEY=“your key here” 
```

#### Making the bot

1. Go to https://discord.com/developers and click “New Application” in the top right corner.
2. Name your application `Group Name`. Replacing `Group Name` with exactly the name of your groups role on Discord.

##### It is very important that you name your app exactly following this scheme; some parts of the bot’s code rely on this format.

1. Next, you’ll want to click on the tab labeled “Bot” under “Settings.”
2. Click “Copy” to copy the bot’s token. If you don’t see “Copy”, hit “Reset Token” and copy the token that appears (make sure you’re the first team member to go through these steps!)
3. Open `.env` and paste the token between the quotes on the line labeled `DISCORD_TOKEN`.
4. Scroll down to a region called “Privileged Gateway Intents”
5. Tick the options for “Presence Intent”, “Server Members Intent”, and “Message Content Intent”, and save your changes.
6. Click on the tab labeled “OAuth2” under “Settings”
7. Click the tab labeled “URL Generator” under “OAuth2”.
8. Check the box labeled “bot”. Once you do that, another area with a bunch of options should appear lower down on the page.
9. Check the following permissions, then copy the link that’s generated. <em>Note that these permissions are just a starting point for your bot. We think they’ll cover most cases, but you may run into cases where you want to be able to do more. If you do, you’re welcome to send updated links to the teaching team to re-invite your bot with new permissions.</em>
<img width="700" alt="Screenshot 2024-04-22 at 4 31 31 PM" src="https://github.com/stanfordio/cs152bots/assets/96695971/520c040e-f494-4b7e-bb45-01dd59772462">

10. Copy paste this link into the #app-invite-link channel on the CS 153 Discord server. Someone in the teaching team will invite your bot.

#### Setting up the starter code

First things first, the starter code is written in Python. You’ll want to make sure that you have Python 3 installed on your machine; if you don’t, follow [these instructions to install PyCharm](https://web.stanford.edu/class/cs106a/handouts/installingpycharm.html), the Stanford-recommended Python editor. Alternatively, you can use a text editor of your choice.

Once you’ve done that, open a terminal in the same folder as your `bot.py ` file. (If you haven’t used your terminal before, check out [this guide](https://www.macworld.com/article/2042378/master-the-command-line-navigating-files-and-folders.html)!)

You’ll need to install some libraries if you don’t have them already, namely:

	# python3 -m pip install requests
	# python3 -m pip install discord.py

## Guide To The Starter Code

Next up, let’s take a look at what `bot.py` already does. To do this, run `python3 bot.py` and leave it running in your terminal. Next, go into your team’s channel `Group-Name` and try typing any message. You should see the bot respond in the same channel. 

The default behavior of the bot is, that any time it sees a message (from a user), it sends that message to Mistral's API and sends back the response. 

## Troubleshooting

### `Exception: .env not found`!

If you’re seeing this error, it probably means that your terminal is not open in the right folder. Make sure that it is open inside the folder that contains `bot.py`  and `.env`
