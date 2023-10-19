#!/bin/bash
mkdir -p ./reports/sorareports
mkdir -p ./reports/etheriumreports

pip install -r requirements.txt

sed -i -e 's/001/'"$networkname"'/g' template_config_ci.json
sed -i -e 's/002/'"${address//\//\\\/}"'/g' template_config_ci.json
sed -i -e 's/003/'"$fromblock"'/g' template_config_ci.json
sed -i -e 's/004/'"$toblock"'/g' template_config_ci.json

python main.py ./template_config.json

directory="./reports"

files=$(find / -name "SORA*.csv")

if [ -n "$files" ]; then
  for file in $files; do
    telegram_bot_token=${TELEGRAM_BOT_TOKEN}
    telegram_group_chat_id=${TELEGRAM_CHAT_ID}
    curl -F document=@"$file" "https://api.telegram.org/bot$telegram_bot_token/sendDocument" \
    -F chat_id="$telegram_group_chat_id" \
    -F caption="Report: $file"
  done
else
    printf "❌ No reports found! \n"
fi