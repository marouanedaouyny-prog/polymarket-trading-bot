@echo Off
:: Add Polymarket & NVIDIA to hosts file (run as Administrator)
echo Adding API hosts...

echo. >> C:\Windows\System32\drivers\etc\hosts
echo # Polymarket API >> C:\Windows\System32\drivers\etc\hosts
echo 104.18.34.205 gamma-api.polymarket.com >> C:\Windows\System32\drivers\etc\hosts
echo 172.64.153.51 api.polymarket.com >> C:\Windows\System32\drivers\etc\hosts

echo. >> C:\Windows\System32\drivers\etc\hosts
echo # NVIDIA API >> C:\Windows\System32\drivers\etc\hosts
echo 99.83.136.103 integrate.api.nvidia.com >> C:\Windows\System32\drivers\etc\hosts
echo 75.2.113.119 api.nvidia.com >> C:\Windows\System32\drivers\etc\hosts

echo Done! Run as Administrator to apply changes.
echo Then restart your terminal and test the bot.
pause