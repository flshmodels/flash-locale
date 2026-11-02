# References and scope

Roblox's [manual translations](https://create.roblox.com/docs/production/localization/manual-translations) and [dynamic content](https://create.roblox.com/docs/production/localization/translate-dynamic-content) docs describe source/context fields and parameter formats. Flash Locale checks a deliberately small CSV subset and uses stricter duplicate/count policies; passing this checker does not guarantee cloud import success.

[Roblox Slang](https://github.com/bookek/roblox-slang) is a larger localization/code-generation project with different formats and features. Flash Locale is a read-only CSV lint command. It does not copy its implementation, generate translations or sync cloud state.
